import os
import json
import shutil
import threading
from typing import Any, Dict

from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
OUTPUT_EXCEL = os.path.join(BASE_DIR, "output.xlsx")
TESCILSIZ_EXCEL = os.path.join(BASE_DIR, "Tescilsiz.xlsx")
ELENMIS_EXCEL = os.path.join(BASE_DIR, "elenmis.xlsx")
TESCILSIZ_MAKER_LOG = os.path.join(LOGS_DIR, "tescilsiz_maker.log")


DEFAULT_CONFIG: Dict[str, Any] = {
    "category_start": 1,
    "category_end": 100000,
    "genders": [str(i) for i in range(1, 13)],
    "num_workers": 10,
    "update_interval": 200,
}


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_PATH):
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return DEFAULT_CONFIG.copy()

    cfg = DEFAULT_CONFIG.copy()
    cfg.update(data)
    cfg["genders"] = [str(g) for g in cfg.get("genders", DEFAULT_CONFIG["genders"])]
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def read_log_tail(path: str, max_lines: int = 50) -> list[str]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    return [line.rstrip("\n") for line in lines[-max_lines:]]


USERNAME = "admin"
PASSWORD = "markaprog.1"

app = Flask(__name__)
app.secret_key = "mk-panel-s3cr3t-2024"


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        if request.form.get("username") == USERNAME and request.form.get("password") == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Kullanıcı adı veya şifre hatalı."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


category_thread: threading.Thread | None = None
patent_thread: threading.Thread | None = None
eleyici_thread: threading.Thread | None = None
tescilsiz_thread: threading.Thread | None = None
category_running = False
patent_running = False
eleyici_running = False
tescilsiz_running = False
category_last_error: str | None = None
patent_last_error: str | None = None
eleyici_last_error: str | None = None
tescilsiz_last_error: str | None = None


def run_category_finder():
    global category_running, category_last_error
    category_last_error = None
    cfg = load_config()
    try:
        import category_finder as cf

        cf.GENDER_LIST = [str(g) for g in cfg.get("genders", DEFAULT_CONFIG["genders"])]
        start = int(cfg.get("category_start", DEFAULT_CONFIG["category_start"]))
        end = int(cfg.get("category_end", DEFAULT_CONFIG["category_end"]))
        cf.main(start=start, end=end)
    except OSError as e:
        if e.errno == 5:  # EIO - Input/output error
            category_last_error = (
                "Dosya okuma/yazma hatası. Proje klasörü iCloud veya Dropbox içindeyse taşı: "
                "Projeyi Masaüstü (~/Desktop) veya yerel bir klasöre kopyala, oradan çalıştır."
            )
        else:
            category_last_error = str(e)
    except Exception as e:
        category_last_error = str(e)
    finally:
        category_running = False


def run_patent_worker():
    global patent_running, patent_last_error
    patent_last_error = None
    cfg = load_config()
    try:
        import patent_worker as pw

        pw.NUM_WORKERS = int(cfg.get("num_workers", DEFAULT_CONFIG["num_workers"]))
        pw.UPDATE_INTERVAL = int(cfg.get("update_interval", DEFAULT_CONFIG["update_interval"]))
        pw.main()
    except OSError as e:
        if e.errno == 5:  # EIO - Input/output error
            patent_last_error = (
                "Dosya okuma/yazma hatası. Proje klasörü iCloud veya Dropbox içindeyse taşı: "
                "Projeyi Masaüstü (~/Desktop) veya yerel bir klasöre kopyala, oradan çalıştır."
            )
        else:
            patent_last_error = str(e)
    except Exception as e:
        patent_last_error = str(e)
    finally:
        patent_running = False


def run_tescilsiz_maker():
    global tescilsiz_running, tescilsiz_last_error
    tescilsiz_last_error = None
    try:
        import tescilsiz_maker as tm

        tm.STOP_REQUESTED = False
        tm.main()
    except OSError as e:
        if e.errno == 5:
            tescilsiz_last_error = (
                "Dosya okuma/yazma hatası. Proje klasörü iCloud veya Dropbox içindeyse taşı."
            )
        else:
            tescilsiz_last_error = str(e)
    except Exception as e:
        tescilsiz_last_error = str(e)
    finally:
        tescilsiz_running = False


def run_eleyici():
    global eleyici_running, eleyici_last_error
    eleyici_last_error = None
    try:
        import eleyici as el

        el.STOP_REQUESTED = False
        el.main()
    except OSError as e:
        if e.errno == 5:
            eleyici_last_error = (
                "Dosya okuma/yazma hatası. Proje klasörü iCloud veya Dropbox içindeyse taşı: "
                "Projeyi Masaüstü (~/Desktop) veya yerel bir klasöre kopyala, oradan çalıştır."
            )
        else:
            eleyici_last_error = str(e)
    except Exception as e:
        eleyici_last_error = str(e)
    finally:
        eleyici_running = False


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    global category_thread, patent_thread, eleyici_thread, tescilsiz_thread, category_running, patent_running, eleyici_running, tescilsiz_running
    cfg = load_config()

    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_config":
            try:
                category_start = int(request.form.get("category_start", cfg["category_start"]))
                category_end = int(request.form.get("category_end", cfg["category_end"]))
                num_workers = int(request.form.get("num_workers", cfg["num_workers"]))
                update_interval = int(request.form.get("update_interval", cfg["update_interval"]))
                genders_raw = request.form.get("genders", ",".join(cfg["genders"]))

                genders = [g.strip() for g in genders_raw.split(",") if g.strip()]

                cfg.update(
                    {
                        "category_start": category_start,
                        "category_end": category_end,
                        "num_workers": num_workers,
                        "update_interval": update_interval,
                        "genders": genders,
                    }
                )
                save_config(cfg)
                flash("Ayarlar kaydedildi.", "success")
            except ValueError:
                flash("Lütfen sayısal alanları doğru doldurun.", "error")

            return redirect(url_for("index"))

        if action == "run_category" and not category_running:
            category_running = True
            category_thread = threading.Thread(target=run_category_finder, daemon=True)
            category_thread.start()
            flash("category_finder çalıştırıldı.", "success")
            return redirect(url_for("index"))

        if action == "run_patent" and not patent_running:
            categories_file = os.path.join(BASE_DIR, "cache", "categories_with_products.txt")
            if not os.path.exists(categories_file) or os.path.getsize(categories_file) == 0:
                flash(
                    "patent_worker için önce category_finder'ı çalıştırıp kategori listesi oluşturmalısın.",
                    "error",
                )
                return redirect(url_for("index"))
            patent_running = True
            patent_thread = threading.Thread(target=run_patent_worker, daemon=True)
            patent_thread.start()
            flash("patent_worker çalıştırıldı.", "success")
            return redirect(url_for("index"))

        if action == "stop_category" and category_running:
            import category_finder as cf

            cf.STOP_REQUESTED = True
            flash("category_finder durduruluyor… (birkaç saniye sürebilir)", "success")
            return redirect(url_for("index"))

        if action == "stop_patent" and patent_running:
            import patent_worker as pw

            pw.STOP_REQUESTED = True
            flash("patent_worker durduruluyor… (birkaç saniye sürebilir)", "success")
            return redirect(url_for("index"))

        if action == "run_tescilsiz" and not tescilsiz_running:
            if not os.path.exists(OUTPUT_EXCEL):
                flash("Tescilsiz Maker için önce output.xlsx oluşturulmalı (patent_worker çalıştır).", "error")
                return redirect(url_for("index"))
            tescilsiz_running = True
            tescilsiz_thread = threading.Thread(target=run_tescilsiz_maker, daemon=True)
            tescilsiz_thread.start()
            flash("tescilsiz_maker çalıştırıldı.", "success")
            return redirect(url_for("index"))

        if action == "stop_tescilsiz" and tescilsiz_running:
            import tescilsiz_maker as tm

            tm.STOP_REQUESTED = True
            flash("tescilsiz_maker durduruluyor…", "success")
            return redirect(url_for("index"))

        if action == "run_eleyici" and not eleyici_running:
            if not os.path.exists(TESCILSIZ_EXCEL):
                flash("Eleyici için önce Tescilsiz.xlsx oluşturulmalı (patent_worker çalıştır).", "error")
                return redirect(url_for("index"))
            eleyici_running = True
            eleyici_thread = threading.Thread(target=run_eleyici, daemon=True)
            eleyici_thread.start()
            flash("eleyici çalıştırıldı.", "success")
            return redirect(url_for("index"))

        if action == "stop_eleyici" and eleyici_running:
            import eleyici as el

            el.STOP_REQUESTED = True
            flash("eleyici durduruluyor… (birkaç saniye sürebilir)", "success")
            return redirect(url_for("index"))

    # Basit health bilgileri
    gecko_ok = bool(shutil.which("geckodriver")) if hasattr(shutil, "which") else False
    has_excel = os.path.exists(OUTPUT_EXCEL)
    has_tescilsiz = os.path.exists(TESCILSIZ_EXCEL)
    has_elenmis = os.path.exists(ELENMIS_EXCEL)

    return render_template(
        "panel.html",
        config=cfg,
        category_running=category_running,
        patent_running=patent_running,
        eleyici_running=eleyici_running,
        tescilsiz_running=tescilsiz_running,
        tescilsiz_last_error=tescilsiz_last_error,
        gecko_ok=gecko_ok,
        has_excel=has_excel,
        has_tescilsiz=has_tescilsiz,
        has_elenmis=has_elenmis,
        category_last_error=category_last_error,
        patent_last_error=patent_last_error,
        eleyici_last_error=eleyici_last_error,
    )


@app.route("/status")
@login_required
def status():
    try:
        import category_finder as cf

        cat_progress = getattr(cf, "PROGRESS", None)
    except Exception:
        cat_progress = None

    try:
        import patent_worker as pw

        pat_progress = getattr(pw, "PROGRESS", None)
    except Exception:
        pat_progress = None

    try:
        import eleyici as el

        el_progress = getattr(el, "PROGRESS", None)
    except Exception:
        el_progress = None

    try:
        import tescilsiz_maker as tm

        tm_progress = getattr(tm, "PROGRESS", None)
    except Exception:
        tm_progress = None

    data: Dict[str, Any] = {
        "category": {
            "running": category_running,
            "progress": cat_progress,
            "last_error": category_last_error,
        },
        "patent": {
            "running": patent_running,
            "progress": pat_progress,
            "last_error": patent_last_error,
        },
        "eleyici": {
            "running": eleyici_running,
            "progress": el_progress,
            "last_error": eleyici_last_error,
        },
        "tescilsiz": {
            "running": tescilsiz_running,
            "progress": tm_progress,
            "last_error": tescilsiz_last_error,
        },
    }
    return jsonify(data)


@app.route("/logs")
@login_required
def logs():
    category_log = read_log_tail(os.path.join(LOGS_DIR, "category_finder.log"), max_lines=80)
    patent_log = read_log_tail(os.path.join(LOGS_DIR, "patent_worker.log"), max_lines=80)
    eleyici_log = read_log_tail(os.path.join(LOGS_DIR, "eleyici.log"), max_lines=80)
    tescilsiz_log = read_log_tail(os.path.join(LOGS_DIR, "tescilsiz_maker.log"), max_lines=80)
    return jsonify(
        {
            "category": category_log,
            "patent": patent_log,
            "eleyici": eleyici_log,
            "tescilsiz": tescilsiz_log,
        }
    )


@app.route("/download/output.xlsx")
@login_required
def download_output():
    if not os.path.exists(OUTPUT_EXCEL):
        flash("Henüz output.xlsx oluşturulmadı.", "error")
        return redirect(url_for("index"))
    return send_file(OUTPUT_EXCEL, as_attachment=True)


@app.route("/download/Tescilsiz.xlsx")
@login_required
def download_tescilsiz():
    if not os.path.exists(TESCILSIZ_EXCEL):
        flash("Henüz Tescilsiz.xlsx oluşturulmadı.", "error")
        return redirect(url_for("index"))
    return send_file(TESCILSIZ_EXCEL, as_attachment=True)


@app.route("/download/elenmis.xlsx")
@login_required
def download_elenmis():
    if not os.path.exists(ELENMIS_EXCEL):
        flash("Henüz elenmis.xlsx oluşturulmadı.", "error")
        return redirect(url_for("index"))
    return send_file(ELENMIS_EXCEL, as_attachment=True)


if __name__ == "__main__":
    # Varsayılan olarak localhost:5000'de çalıştır
    app.run(host="127.0.0.1", port=5000, debug=True)

