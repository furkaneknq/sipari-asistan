"""Tema yönetimi: QSS dosyalarını yükler ve uygulamaya uygular."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QApplication

import config


THEMES = {
    "light": {"label": "Açık", "file": "light.qss"},
    "dark": {"label": "Koyu", "file": "dark.qss"},
    "forest": {"label": "Orman", "file": "forest.qss"},
    "graphite": {"label": "Grafit", "file": "graphite.qss"},
}


def list_theme_names() -> list[str]:
    return list(THEMES.keys())


def theme_label(theme_name: str) -> str:
    theme = THEMES.get(theme_name)
    if theme is None:
        return theme_name.title()
    return theme["label"]


def load_qss(theme_name: str) -> str:
    """QSS dosyasının içeriğini döner."""
    theme = THEMES.get(theme_name, THEMES["light"])
    file_name = theme["file"]
    path = Path(config.STYLES_DIR) / file_name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def apply_theme(app: QApplication, theme_name: str) -> None:
    """Belirtilen temayı tüm uygulamaya uygular."""
    qss = load_qss(theme_name)
    app.setStyleSheet(qss)
