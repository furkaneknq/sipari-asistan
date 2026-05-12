#!/usr/bin/env bash
# =============================================================
# Sipariş Takip Sistemi - Linux başlatma scripti
# İlk çalıştırmada: sanal ortam kurar, paketleri indirir, başlatır.
# Sonraki çalıştırmalarda: doğrudan başlatır.
#
# Kullanım:
#   ./run.sh
# =============================================================

set -e

cd "$(dirname "$0")"

VENV=".venv"
PY="python3"

# 1) Sanal ortam yoksa oluştur
if [ ! -d "$VENV" ]; then
    echo "[1/3] Sanal ortam oluşturuluyor..."
    "$PY" -m venv "$VENV"
fi

# 2) Sanal ortamı etkinleştir
# shellcheck source=/dev/null
source "$VENV/bin/activate"

# 3) Paketleri yükle (sadece eksikse)
if [ ! -f "$VENV/.installed" ] || [ "requirements.txt" -nt "$VENV/.installed" ]; then
    echo "[2/3] Paketler yükleniyor..."
    pip install --upgrade pip wheel >/dev/null
    pip install -r requirements.txt
    touch "$VENV/.installed"
fi

# 4) .env kontrolü
if [ ! -f ".env" ]; then
    echo "HATA: .env dosyası yok. .env.example'ı kopyalayıp doldurun."
    exit 1
fi

# 5) Çalıştır
echo "[3/3] Uygulama başlatılıyor..."
exec python main.py
