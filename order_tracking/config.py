"""Uygulama yapılandırması.

.env dosyasından Supabase ve yazıcı ayarlarını okur.
Tüm uygulama bu modülü import ederek değerleri kullanır.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def _app_dir() -> Path:
    """Geliştirmede dosyanın yanı; PyInstaller exe'sinde exe'nin yanı."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _resource_dir() -> Path:
    """Read-only kaynaklar (assets/) için.
    PyInstaller _MEIPASS'a açar, geliştirmede dosyanın yanı."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", _app_dir()))
    return Path(__file__).resolve().parent


def _find_env_file() -> Path | None:
    """
    Aşağıdaki sırayla .env arar; ilk bulunanı döner:
      1) Exe/script ile aynı klasör (taşınabilir kurulum)
      2) %APPDATA%\\SiparisAsistani\\.env  (Windows kullanıcı bazlı)
      3) ~/.config/siparis-asistani/.env   (Linux/Mac)
    """
    candidates: list[Path] = [_app_dir() / ".env"]
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "SiparisAsistani" / ".env")
    candidates.append(Path.home() / ".config" / "siparis-asistani" / ".env")
    for c in candidates:
        if c.exists():
            return c
    return None


BASE_DIR = _resource_dir()
APP_DIR = _app_dir()

ENV_PATH = _find_env_file()
if ENV_PATH is not None:
    load_dotenv(ENV_PATH)
else:
    # Sistem env değişkenlerine düş
    load_dotenv()

# ---------- Supabase ----------
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "").strip()
SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()

# Masaüstü için service_role tercih edilir (RLS bypass eder)
SUPABASE_KEY: str = SUPABASE_SECRET_KEY or SUPABASE_PUBLISHABLE_KEY

# ---------- Yazıcı ----------
PRINTER_TYPE: str = os.getenv("PRINTER_TYPE", "dummy").strip().lower()
PRINTER_USB_VENDOR_ID: str = os.getenv("PRINTER_USB_VENDOR_ID", "0x04b8")
PRINTER_USB_PRODUCT_ID: str = os.getenv("PRINTER_USB_PRODUCT_ID", "0x0202")
PRINTER_NETWORK_HOST: str = os.getenv("PRINTER_NETWORK_HOST", "")
PRINTER_NETWORK_PORT: int = int(os.getenv("PRINTER_NETWORK_PORT", "9100") or 9100)
PRINTER_PAPER_WIDTH: int = int(os.getenv("PRINTER_PAPER_WIDTH", "80") or 80)

# ---------- UI ----------
APP_NAME: str = "Sipariş Takip Sistemi"
APP_VERSION: str = "0.1.0"
ASSETS_DIR: Path = BASE_DIR / "assets"
STYLES_DIR: Path = ASSETS_DIR / "styles"
ICONS_DIR: Path = ASSETS_DIR / "icons"


def is_configured() -> bool:
    """Supabase bağlantı bilgileri tamam mı?"""
    return bool(SUPABASE_URL) and bool(SUPABASE_KEY)


def missing_config_message() -> str:
    """Konfig eksikse kullanıcıya gösterilecek mesaj."""
    eksikler = []
    if not SUPABASE_URL:
        eksikler.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        eksikler.append("SUPABASE_SECRET_KEY (veya SUPABASE_PUBLISHABLE_KEY)")
    return (
        "Eksik yapılandırma: " + ", ".join(eksikler) + "\n\n"
        "Lütfen .env.example dosyasını .env olarak kopyalayıp\n"
        "Supabase Dashboard'dan aldığınız değerleri girin."
    )
