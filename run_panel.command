#!/bin/bash

# Bu dosyaya çift tıkladığında panel otomatik açılır.

cd "$(dirname "$0")" || exit 1

# Önce venv'deki Python'u kullan (daha güvenilir); yoksa sistem python3
if [ -x ".venv/bin/python3" ]; then
  PYTHON_CMD=".venv/bin/python3"
elif [ -x ".venv/bin/python" ]; then
  PYTHON_CMD=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "Python bulunamadı. Önce: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  read -r
  exit 1
fi

# Bağımlılık kontrolü
if ! "$PYTHON_CMD" -c "import flask" 2>/dev/null; then
  echo "Flask kurulu değil. Kuruluyor..."
  "$PYTHON_CMD" -m pip install -r requirements.txt
fi

# Arka planda Flask panelini başlat
"$PYTHON_CMD" panel.py &

# Sunucunun ayağa kalkması için birkaç saniye bekle
sleep 3

# Varsayılan tarayıcıda paneli aç
open "http://127.0.0.1:5000"

# Terminal penceresinin hemen kapanmaması için (isteğe bağlı)
echo ""
echo "Panel tarayıcıda açıldı. Kapatmak için Ctrl+C, ardından pencereyi kapatabilirsin."
read -r

