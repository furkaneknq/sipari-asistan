"""Tema yönetimi: QSS dosyalarını yükler ve uygulamaya uygular."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QApplication

import config


THEMES = {
    "light": "light.qss",
    "dark": "dark.qss",
}


def list_theme_names() -> list[str]:
    return list(THEMES.keys())


def load_qss(theme_name: str) -> str:
    """QSS dosyasının içeriğini döner."""
    file_name = THEMES.get(theme_name, THEMES["light"])
    path = Path(config.STYLES_DIR) / file_name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def apply_theme(app: QApplication, theme_name: str) -> None:
    """Belirtilen temayı tüm uygulamaya uygular."""
    qss = load_qss(theme_name)
    app.setStyleSheet(qss)
