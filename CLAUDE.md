# CLAUDE.md

Turkish-language web application ("Patent Paneli") for e-commerce data collection and trademark registration checking against the Turkish Patent Office.

## Setup & Run

```bash
# Install dependencies
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Run web UI (http://127.0.0.1:5000)
python3 panel.py

# Run CLI components individually
python3 category_finder.py
python3 patent_worker.py

# macOS double-click launcher
./run_panel.command
```

**System dependency:** Firefox + geckodriver required for Selenium.

## Architecture

**Data flow:** `config.json` → `category_finder.py` → `cache/categories_with_products.txt` → `patent_worker.py` → `output.xlsx`

| File | Role |
|------|------|
| `panel.py` | Flask app; spawns category_finder and patent_worker as daemon threads; exposes `/status`, `/logs`, `/download/output.xlsx` |
| `category_finder.py` | Queries Trendyol API; outputs `cache/categories_with_products.txt` |
| `patent_worker.py` | Reads cache; scrapes Turkish Patent Office via Selenium (ThreadPoolExecutor, up to 10 Firefox instances); writes `output.xlsx` |
| `templates/panel.html` | Dark-theme UI with AJAX polling every 4–5s |
| `config.json` | Runtime config: category range, genders, worker count, update interval |

## Notes

- No test suite configured.
- No linter configured.
