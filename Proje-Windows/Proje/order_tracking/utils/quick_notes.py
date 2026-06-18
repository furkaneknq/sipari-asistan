"""Hızlı notlar — kullanıcı bazlı, JSON dosyasında saklanan kısa not şablonları.

Sipariş ekleme/düzenleme ekranında kullanıcı, sıkça yazdığı notları (örn.
'Acı az olsun', 'Soğansız', 'Kapıya bırak') buradan tek tıkla ekler.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


DEFAULT_NOTES: list[str] = [
    "Acı az olsun",
    "Soğansız",
    "Sosu ayrı",
    "Kapıya bırakın",
    "Zile basmayın",
    "Yağsız",
    "Az tuzlu",
]


def _config_dir() -> Path:
    """Kullanıcı verilerinin saklandığı dizin (cross-platform)."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "SiparisAsistani"
    return Path.home() / ".config" / "siparis-asistani"


def _notes_file() -> Path:
    return _config_dir() / "quick_notes.json"


def load_notes() -> list[str]:
    """Kayıtlı notları okur; dosya yoksa varsayılan listeyi döndürür."""
    path = _notes_file()
    if not path.exists():
        return list(DEFAULT_NOTES)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(x) for x in data if str(x).strip()]
    except (OSError, json.JSONDecodeError):
        pass
    return list(DEFAULT_NOTES)


def save_notes(notes: list[str]) -> None:
    """Notları diske yazar (varsa duplikatları temizler, sırayı korur)."""
    path = _notes_file()
    path.parent.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    cleaned: list[str] = []
    for n in notes:
        s = (n or "").strip()
        if s and s not in seen:
            seen.add(s)
            cleaned.append(s)

    path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_note(text: str) -> list[str]:
    """Yeni not ekler ve güncel listeyi döndürür."""
    text = (text or "").strip()
    if not text:
        return load_notes()
    notes = load_notes()
    if text not in notes:
        notes.append(text)
        save_notes(notes)
    return notes


def remove_note(text: str) -> list[str]:
    """Notu siler ve güncel listeyi döndürür."""
    notes = [n for n in load_notes() if n != text]
    save_notes(notes)
    return notes
