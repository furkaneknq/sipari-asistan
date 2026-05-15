"""Sipariş Takip Sistemi - Ana giriş noktası.

Çalıştırma:
    python main.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox

import config
from database.supabase_client import reset_client, test_connection
from ui import themes
from ui.main_window import MainWindow


def _env_file_path() -> Path:
    """Kullanıcının düzenlemesi gereken .env dosyasının yolu."""
    return Path(config.APP_DIR) / ".env"


def _open_env_in_editor() -> None:
    """Platform-uygun şekilde .env dosyasını editör ile açar."""
    env_path = _env_file_path()
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(env_path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(env_path)])
        else:
            subprocess.Popen(["xdg-open", str(env_path)])
    except Exception:  # noqa: BLE001
        pass


def _show_connection_error(message: str) -> str:
    """Bağlantı hatası dialog'u — 3 buton: Tekrar Dene / Ayarları Aç / Çıkış.

    Döndürür: 'retry' | 'edit' | 'quit'
    """
    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle("Bağlantı Hatası")
    box.setText(message)
    retry_btn = box.addButton("Tekrar Dene", QMessageBox.ButtonRole.AcceptRole)
    edit_btn = box.addButton("Ayarları Aç (.env)", QMessageBox.ButtonRole.ActionRole)
    quit_btn = box.addButton("Çıkış", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(retry_btn)
    box.exec()
    clicked = box.clickedButton()
    if clicked is retry_btn:
        return "retry"
    if clicked is edit_btn:
        return "edit"
    return "quit"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)

    # Debug: .env ve yazıcı ayarlarını göster
    print(f"[CONFIG] .env yolu: {config.ENV_PATH}")
    print(f"[CONFIG] PRINTER_TYPE={config.PRINTER_TYPE}")
    print(f"[CONFIG] PRINTER_WIN_NAME={config.PRINTER_WIN_NAME}")

    # Varsayılan tema (DB'den okumadan önce)
    themes.apply_theme(app, "light")

    # Konfigürasyon kontrolü
    if not config.is_configured():
        QMessageBox.critical(
            None,
            "Yapılandırma Eksik",
            config.missing_config_message(),
        )
        # Ayarları açmayı dene
        _open_env_in_editor()
        return 1

    # Veritabanı bağlantı kontrolü — retry döngüsü
    while True:
        ok, msg = test_connection()
        if ok:
            break
        action = _show_connection_error(msg)
        if action == "quit":
            return 1
        if action == "edit":
            _open_env_in_editor()
        # 'retry' veya 'edit' sonrası: .env tekrar oku ve client'ı sıfırla
        try:
            from dotenv import load_dotenv

            load_dotenv(_env_file_path(), override=True)
            # config modülünü yeniden yükle ki güncel SUPABASE_URL/KEY okusun
            import importlib

            importlib.reload(config)
        except Exception:  # noqa: BLE001
            pass
        reset_client()

    try:
        window = MainWindow()
        window.show()
    except Exception:  # noqa: BLE001
        QMessageBox.critical(
            None,
            "Başlatma Hatası",
            f"Uygulama başlatılırken hata oluştu:\n\n{traceback.format_exc()}",
        )
        return 1

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
