import os
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://apigw.trendyol.com"
OUT_FILE = "cache/categories_with_products.txt"
GENDER_LIST = [str(i) for i in range(1, 13)]

# Durdurma isteği; panel "Durdur" tıklanınca True yapar
STOP_REQUESTED = False

# Basit progress ve log bilgisi; panel.py buradan okuyabilir
PROGRESS = {
    "start": None,
    "end": None,
    "current": None,
    "completed": 0,
    "found_count": 0,
}


def _ensure_cache_dir() -> None:
    cache_dir = os.path.dirname(OUT_FILE)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)


def log(message: str) -> None:
    """Hem konsola hem de log dosyasına yaz."""
    ts = time.strftime("%H:%M:%S")
    text = f"[{ts}] {message}"
    print(text)

    log_dir = os.path.join(os.path.dirname(OUT_FILE), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "category_finder.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except OSError:
        # Log yazılamasa da ana akışı bozma
        pass


session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
session.mount("https://", HTTPAdapter(max_retries=retries))


def get_products_from_top_ranking(params):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
    }
    url = "/discovery-web-websfxcategorytopranking-santral/topRankingContents"
    r = session.get(f"{BASE_URL}{url}", headers=headers, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("result", {})


def append_id(path, category_id, gender):
    _ensure_cache_dir()
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{category_id},{gender}\n")


def _load_seen_pairs():
    seen = set()
    if not os.path.exists(OUT_FILE):
        return seen

    with open(OUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            if "," in s:
                cid_str, gender_str = [p.strip() for p in s.split(",", 1)]
                if cid_str.isdigit() and gender_str.isdigit():
                    seen.add((int(cid_str), gender_str))
            elif s.isdigit():
                seen.add((int(s), "1"))
    return seen


def main(start=1, end=100000):
    global STOP_REQUESTED
    STOP_REQUESTED = False

    PROGRESS["start"] = int(start)
    PROGRESS["end"] = int(end)
    PROGRESS["current"] = None
    PROGRESS["completed"] = 0
    PROGRESS["found_count"] = 0

    seen = _load_seen_pairs()
    total = max(0, PROGRESS["end"] - PROGRESS["start"])

    log(f"Kategori taraması başladı: [{PROGRESS['start']}, {PROGRESS['end']}) - daha önce bulunan çift sayısı: {len(seen)}")

    for idx, categoryId in enumerate(range(PROGRESS["start"], PROGRESS["end"]), start=1):
        if STOP_REQUESTED:
            log("Durdurma isteği alındı, tarama durduruluyor.")
            break

        PROGRESS["current"] = categoryId
        has_any_product = False

        for gender in GENDER_LIST:
            pair = (categoryId, gender)
            if pair in seen:
                has_any_product = True
                continue

            params = {
                "categoryId": categoryId,
                "rankingType": "bestSeller",
                "gender": gender,
                "page": "1",
                "channelId": "1",
            }
            try:
                res = get_products_from_top_ranking(params)
            except Exception as e:
                log(f"API hatası (category={categoryId}, gender={gender}): {e}")
                continue

            ok = bool(res and "contents" in res and len(res["contents"]) > 0)

            if ok:
                append_id(OUT_FILE, categoryId, gender)
                seen.add(pair)
                has_any_product = True
                PROGRESS["found_count"] += 1
                log(f"[OK] {categoryId},{gender}")
            else:
                log(f"[NO] {categoryId},{gender}")

        PROGRESS["completed"] = idx
        if not has_any_product:
            log(f"[NO] {categoryId} (hiçbir gender'da ürün yok)")

        # Çok sık log basmamak için her 100 kategoride bir özet geç
        if total and idx % 100 == 0:
            pct = (idx / total) * 100
            log(f"İlerleme: {idx}/{total} kategori (~%{pct:.1f})")

    log("Kategori taraması tamamlandı.")


if __name__ == "__main__":
    main()