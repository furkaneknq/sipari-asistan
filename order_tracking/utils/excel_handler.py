"""Müşteri Excel import/export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from database import customers_db
from utils.helpers import format_phone, normalize_phone


COLUMNS = ["Ad Soyad", "Telefon", "Adres", "Not"]


def export_customers(file_path: str | Path) -> int:
    """Veritabanındaki tüm müşterileri Excel'e yazar. Yazılan satır sayısını döner."""
    file_path = Path(file_path)
    customers = customers_db.list_customers()

    wb = Workbook()
    ws = wb.active
    ws.title = "Müşteriler"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="1976D2", end_color="1976D2", fill_type="solid"
    )

    for col_idx, col_name in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    row_idx = 2
    for cust in customers:
        addresses = customers_db.list_addresses(cust["id"])
        addr_text = ""
        if addresses:
            default = next(
                (a for a in addresses if a.get("is_default")), addresses[0]
            )
            addr_text = default.get("address_text") or ""
        ws.cell(row=row_idx, column=1, value=cust.get("name", ""))
        ws.cell(row=row_idx, column=2, value=format_phone(cust.get("phone", "")))
        ws.cell(row=row_idx, column=3, value=addr_text)
        ws.cell(row=row_idx, column=4, value=cust.get("notes", ""))
        row_idx += 1

    for col_idx, col_name in enumerate(COLUMNS, start=1):
        max_len = max(
            len(col_name),
            *(
                len(str(ws.cell(row=r, column=col_idx).value or ""))
                for r in range(2, row_idx)
            ),
            10,
        )
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = (
            min(max_len + 2, 60)
        )

    wb.save(file_path)
    return row_idx - 2


def import_customers(file_path: str | Path) -> dict[str, int]:
    """Excel'den müşterileri içe aktarır.

    Sütunlar: Ad Soyad | Telefon | Adres | Not

    Aynı telefondaki müşteri varsa eklemez (skip).
    Adres alanı varsa müşterinin varsayılan adresi olarak eklenir.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    wb = load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active

    inserted = 0
    skipped = 0
    failed = 0

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"inserted": 0, "skipped": 0, "failed": 0, "total": 0}

    header = [str(c).strip() if c else "" for c in rows[0]]
    name_idx = _find_column(header, ["Ad Soyad", "Ad", "İsim", "Name"])
    phone_idx = _find_column(header, ["Telefon", "Phone", "Tel"])
    address_idx = _find_column(header, ["Adres", "Address"])
    notes_idx = _find_column(header, ["Not", "Notlar", "Notes"])

    if name_idx is None or phone_idx is None:
        raise ValueError(
            "Excel dosyasında en az 'Ad Soyad' ve 'Telefon' sütunları olmalı."
        )

    for row in rows[1:]:
        try:
            name = _cell_text(row, name_idx)
            phone_raw = _cell_text(row, phone_idx)
            address = _cell_text(row, address_idx) if address_idx is not None else ""
            notes = _cell_text(row, notes_idx) if notes_idx is not None else ""

            if not name or not phone_raw:
                failed += 1
                continue

            phone = normalize_phone(phone_raw)
            if not phone:
                failed += 1
                continue

            if customers_db.get_customer_by_phone(phone):
                skipped += 1
                continue

            cust = customers_db.create_customer(
                name=name, phone=phone, notes=notes or None
            )
            cust_id = cust.get("id")
            if cust_id and address:
                customers_db.create_address(
                    cust_id, address_text=address, title="Ev", is_default=True
                )
            inserted += 1
        except Exception:  # noqa: BLE001
            failed += 1

    return {
        "inserted": inserted,
        "skipped": skipped,
        "failed": failed,
        "total": len(rows) - 1,
    }


# ---------------- internal ----------------
def _find_column(header: list[str], aliases: list[str]) -> int | None:
    lowered = [h.strip().lower() for h in header]
    for alias in aliases:
        target = alias.strip().lower()
        if target in lowered:
            return lowered.index(target)
    return None


def _cell_text(row: tuple[Any, ...], idx: int | None) -> str:
    if idx is None or idx >= len(row):
        return ""
    val = row[idx]
    if val is None:
        return ""
    return str(val).strip()
