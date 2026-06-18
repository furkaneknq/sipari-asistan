"""Veritabanı yedekleme yöneticisi.

Supabase'deki tüm tabloları JSON olarak lokal dosyaya yedekler.
Günlük otomatik yedekleme + elle yedek alma/geri yükleme destekler.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .supabase_client import get_client

log = logging.getLogger(__name__)

# Yedeklenecek tablolar (sıralama: bağımlılıklara göre)
BACKUP_TABLES = [
    "categories",
    "products",
    "customers",
    "customer_addresses",
    "couriers",
    "orders",
    "order_items",
    "phones",
    "incoming_calls",
    "settings",
    "themes",
]

# Varsayılan yedek dizini
_DEFAULT_BACKUP_DIR = Path.home() / "siparis_yedekleri"

# Maksimum tutulacak yedek sayısı
MAX_BACKUPS = 30


def get_backup_dir() -> Path:
    """Yedek dosyalarının saklandığı dizini döner, yoksa oluşturur."""
    backup_dir = _DEFAULT_BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(backup_dir: Path | None = None) -> tuple[bool, str]:
    """Tüm tabloları JSON olarak yedekler.

    Returns:
        (başarılı, mesaj) — mesaj: dosya yolu veya hata açıklaması.
    """
    if backup_dir is None:
        backup_dir = get_backup_dir()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{timestamp}"
    backup_path = backup_dir / backup_name
    backup_path.mkdir(parents=True, exist_ok=True)

    try:
        client = get_client()
        metadata: dict[str, Any] = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "tables": {},
        }

        for table_name in BACKUP_TABLES:
            try:
                all_rows = _fetch_all_rows(client, table_name)
                table_file = backup_path / f"{table_name}.json"
                table_file.write_text(
                    json.dumps(all_rows, ensure_ascii=False, default=str, indent=2),
                    encoding="utf-8",
                )
                metadata["tables"][table_name] = len(all_rows)
                log.info("Yedeklendi: %s (%d satır)", table_name, len(all_rows))
            except Exception as exc:  # noqa: BLE001
                log.warning("Tablo yedeklenemedi: %s — %s", table_name, exc)
                metadata["tables"][table_name] = f"HATA: {exc}"

        # Metadata dosyası
        meta_file = backup_path / "_metadata.json"
        meta_file.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # Eski yedekleri temizle
        _cleanup_old_backups(backup_dir)

        total_rows = sum(
            v for v in metadata["tables"].values() if isinstance(v, int)
        )
        return True, f"Yedek alındı: {backup_path.name} ({total_rows} satır)"

    except Exception as exc:  # noqa: BLE001
        # Hatalı dizini temizle
        if backup_path.exists():
            shutil.rmtree(backup_path, ignore_errors=True)
        log.error("Yedekleme başarısız: %s", exc)
        return False, f"Yedekleme başarısız: {exc}"


def restore_backup(backup_path: Path) -> tuple[bool, str]:
    """Yedek dizinindeki JSON dosyalarından veritabanını geri yükler.

    DİKKAT: Mevcut verilerin üzerine yazar (upsert).

    Returns:
        (başarılı, mesaj)
    """
    if not backup_path.is_dir():
        return False, "Geçersiz yedek dizini"

    meta_file = backup_path / "_metadata.json"
    if not meta_file.exists():
        return False, "Geçersiz yedek: _metadata.json bulunamadı"

    try:
        client = get_client()
        restored_count = 0

        for table_name in BACKUP_TABLES:
            table_file = backup_path / f"{table_name}.json"
            if not table_file.exists():
                continue

            rows = json.loads(table_file.read_text(encoding="utf-8"))
            if not rows:
                continue

            # Batch upsert (500'er kayıt)
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                client.table(table_name).upsert(batch).execute()

            restored_count += len(rows)
            log.info("Geri yüklendi: %s (%d satır)", table_name, len(rows))

        return True, f"Geri yükleme tamamlandı ({restored_count} satır)"

    except Exception as exc:  # noqa: BLE001
        log.error("Geri yükleme başarısız: %s", exc)
        return False, f"Geri yükleme başarısız: {exc}"


def list_backups(backup_dir: Path | None = None) -> list[dict[str, Any]]:
    """Mevcut yedeklerin listesini döner (yeniden eskiye)."""
    if backup_dir is None:
        backup_dir = get_backup_dir()

    backups: list[dict[str, Any]] = []
    if not backup_dir.exists():
        return backups

    for item in sorted(backup_dir.iterdir(), reverse=True):
        if not item.is_dir() or not item.name.startswith("backup_"):
            continue
        meta_file = item / "_metadata.json"
        meta: dict[str, Any] = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                pass

        total_rows = sum(
            v for v in meta.get("tables", {}).values() if isinstance(v, int)
        )
        size_mb = sum(f.stat().st_size for f in item.iterdir() if f.is_file()) / (1024 * 1024)

        backups.append({
            "name": item.name,
            "path": str(item),
            "created_at": meta.get("created_at", ""),
            "total_rows": total_rows,
            "size_mb": round(size_mb, 2),
        })

    return backups


def should_backup_today(backup_dir: Path | None = None) -> bool:
    """Bugün yedek alınmış mı kontrol eder."""
    if backup_dir is None:
        backup_dir = get_backup_dir()

    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    if not backup_dir.exists():
        return True

    for item in backup_dir.iterdir():
        if item.is_dir() and item.name.startswith(f"backup_{today}"):
            return False

    return True


# ─── Dahili yardımcılar ────────────────────────────────────────────────


def _fetch_all_rows(client: Any, table_name: str) -> list[dict[str, Any]]:
    """Bir tablodan tüm satırları pagination ile çeker."""
    PAGE_SIZE = 1000
    all_rows: list[dict[str, Any]] = []
    offset = 0

    while True:
        res = (
            client.table(table_name)
            .select("*")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        page = res.data or []
        all_rows.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return all_rows


def _cleanup_old_backups(backup_dir: Path) -> None:
    """MAX_BACKUPS'tan fazla yedek varsa eskileri siler."""
    backups = sorted(
        [d for d in backup_dir.iterdir() if d.is_dir() and d.name.startswith("backup_")],
        reverse=True,
    )
    for old_backup in backups[MAX_BACKUPS:]:
        try:
            shutil.rmtree(old_backup)
            log.info("Eski yedek silindi: %s", old_backup.name)
        except Exception as exc:  # noqa: BLE001
            log.warning("Eski yedek silinemedi: %s — %s", old_backup.name, exc)
