#!/usr/bin/env python3
"""
Sipariş Asistanı — Windows kurulum ZIP'i üreticisi.

Linux'ta calistir:
    python3 _build_windows_zip.py

Cikti:
    Proje-Windows.zip  (proje kokunde)

ZIP icindeki dosyalar binary kopyalanir; .bat / .iss dosyalarinin
CRLF satir sonlari ve UTF-8 BOM'lari korunur.
"""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
ZIP_NAME = "Proje-Windows.zip"
ZIP_PATH = ROOT / ZIP_NAME

# ZIP icindeki tum dosyalar bu klasor altinda olacak.
# Boylece kullanici ZIP'i ne kadar yanlis acsa da yapi bozulmaz.
ZIP_TOPLEVEL = "Proje"

# Dahil edilecek klasorler (paths relative to ROOT).
# Tek tek dosya da verilebilir.
INCLUDE_DIRS = [
    "installer/windows",
    "order_tracking",
    "database/sql",
]

# Tek dosyalar:
INCLUDE_FILES = [
    "KURULUM_OKU.txt",
    ".gitattributes",
]

# Bu pattern'lardan herhangi birini iceren yollar atlanir.
EXCLUDE_PATTERNS = (
    "/__pycache__/",
    "/.git/",
    "/.venv/",
    "/node_modules/",
    "/dist/",
    "/build/",
    "/Output/",
    "/.DS_Store",
)

# Bu uzantilar atlanir
EXCLUDE_SUFFIXES = (
    ".pyc",
    ".pyo",
)

# Bu tam yollar (rel) atlanir — gizli/private dosyalar
EXCLUDE_EXACT = {
    "order_tracking/.env",       # private! ZIP'e konmaz
    "order_tracking/run.sh",     # Linux helper, Windows'ta gerek yok
}


def _should_exclude(rel_path: str) -> bool:
    p = "/" + rel_path.replace(os.sep, "/")
    if any(pat in p for pat in EXCLUDE_PATTERNS):
        return True
    if rel_path in EXCLUDE_EXACT:
        return True
    if any(rel_path.endswith(suf) for suf in EXCLUDE_SUFFIXES):
        return True
    return False


def _collect_files() -> list[Path]:
    files: list[Path] = []
    for d in INCLUDE_DIRS:
        base = ROOT / d
        if not base.exists():
            print(f"  UYARI: bulunamadi {d}, atlandi")
            continue
        for fp in sorted(base.rglob("*")):
            if not fp.is_file():
                continue
            rel = fp.relative_to(ROOT).as_posix()
            if _should_exclude(rel):
                continue
            files.append(fp)

    for f in INCLUDE_FILES:
        fp = ROOT / f
        if fp.exists() and fp.is_file():
            files.append(fp)
        else:
            print(f"  UYARI: tek dosya yok: {f}")
    return files


def main() -> int:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()

    files = _collect_files()
    print(f"Paketlenecek dosya sayisi: {len(files)}")

    total_bytes = 0
    with zipfile.ZipFile(
        ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zf:
        for fp in files:
            rel = fp.relative_to(ROOT).as_posix()
            arcname = f"{ZIP_TOPLEVEL}/{rel}"
            zf.write(fp, arcname=arcname)
            total_bytes += fp.stat().st_size

    out_size = ZIP_PATH.stat().st_size
    print()
    print(f"Olusturuldu : {ZIP_PATH}")
    print(f"  Dosya     : {len(files)}")
    print(f"  Ham boyut : {total_bytes / 1024:.1f} KB")
    print(f"  ZIP boyut : {out_size / 1024:.1f} KB")

    print()
    print("Icerik onizleme (ilk 25):")
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for name in zf.namelist()[:25]:
            print(f"  {name}")
        if len(zf.namelist()) > 25:
            print(f"  ... ({len(zf.namelist()) - 25} daha)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
