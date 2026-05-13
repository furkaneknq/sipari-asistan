"""Gelen aramalar (incoming_calls) için sorgu yardımcıları."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from .supabase_client import get_client


def list_calls(
    start_date: date | None = None,
    end_date: date | None = None,
    only_unprocessed: bool = False,
    search: str = "",
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Gelen aramaları (en yeni üstte) döndürür."""
    query = (
        get_client()
        .table("incoming_calls")
        .select("*,customers(id,name,phone)")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if start_date is not None:
        start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        query = query.gte("created_at", start_dt.isoformat())
    if end_date is not None:
        end_dt = datetime.combine(
            end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
        )
        query = query.lt("created_at", end_dt.isoformat())
    if only_unprocessed:
        query = query.eq("is_processed", False)

    rows = query.execute().data or []
    rows = enrich_calls_with_customer(rows)
    rows = _enrich_device_names(rows)

    if search:
        s = search.strip().lower()
        rows = [
            r
            for r in rows
            if s in (r.get("phone_number") or "").lower()
            or s in ((r.get("customers") or {}).get("name") or "").lower()
        ]
    return rows


def _enrich_device_names(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """device_id → phones.device_name basit eşleştirme."""
    if not rows:
        return rows
    device_ids = {r.get("device_id") for r in rows if r.get("device_id")}
    if not device_ids:
        return rows
    try:
        res = (
            get_client()
            .table("phones")
            .select("device_id,device_name")
            .in_("device_id", list(device_ids))
            .execute()
        )
        name_map = {
            p["device_id"]: p.get("device_name") or ""
            for p in (res.data or [])
            if p.get("device_id")
        }
    except Exception:  # noqa: BLE001
        name_map = {}
    for r in rows:
        did = r.get("device_id")
        if did and did in name_map:
            r["phones"] = {"device_name": name_map[did]}
    return rows


def enrich_calls_with_customer(
    rows: list[dict[str, Any]],
    *,
    persist: bool = False,
) -> list[dict[str, Any]]:
    """Customers join boş olan satırlar için Python tarafında eşleştirme yapar.

    DB trigger'ı eşleştiremediği veya PostgREST embed'i boş döndürdüğü
    durumlarda fallback olur. Telefon numarası son 10 haneye normalize
    edilip yaygın formatlarda (5xx..., 05xx..., +905xx..., 905xx...) tek
    bir 'in_' sorgusuyla aranır. Gerçek müşteri (is_guest=false) tercihli.

    persist=True verilirse, eşleşen satırların `customer_id`'si de
    sessizce DB'de güncellenir (idempotent).
    """
    if not rows:
        return rows

    from utils.helpers import normalize_phone

    needs: list[dict[str, Any]] = [
        r for r in rows if not (r.get("customers") or {}).get("id")
    ]
    if not needs:
        return rows

    # Eşsiz son-10-hane gruplandırması
    by_norm_calls: dict[str, list[dict[str, Any]]] = {}
    for r in needs:
        norm = normalize_phone(r.get("phone_number") or "")
        if norm and len(norm) >= 10:
            by_norm_calls.setdefault(norm, []).append(r)

    if not by_norm_calls:
        return rows

    # Tüm olası tam-eşleşme varyantları (tek sorgu için)
    candidates: set[str] = set()
    for norm in by_norm_calls:
        candidates.update([norm, f"0{norm}", f"+90{norm}", f"90{norm}"])

    client = get_client()
    try:
        cust_rows = (
            client.table("customers")
            .select("id,name,phone,is_guest")
            .in_("phone", list(candidates))
            .execute()
            .data
            or []
        )
    except Exception:  # noqa: BLE001
        cust_rows = []

    # norm → en uygun müşteri (yalnızca gerçek müşteriler)
    by_norm_cust: dict[str, dict[str, Any]] = {}
    for c in cust_rows:
        if c.get("is_guest"):
            continue  # misafir kayıtlarını atla
        cnorm = normalize_phone(c.get("phone") or "")
        if not cnorm:
            continue
        if cnorm not in by_norm_cust:
            by_norm_cust[cnorm] = c

    # Eşleşmeyenler için boşluk/tire içeren olası kayıtları ilike ile yokla.
    missing = [n for n in by_norm_calls if n not in by_norm_cust]
    if missing:
        try:
            for norm in missing:
                res = (
                    client.table("customers")
                    .select("id,name,phone,is_guest")
                    .ilike("phone", f"%{norm[-4:]}%")
                    .limit(10)
                    .execute()
                )
                for c in (res.data or []):
                    if c.get("is_guest"):
                        continue  # misafir kayıtlarını atla
                    if normalize_phone(c.get("phone") or "") == norm:
                        if norm not in by_norm_cust:
                            by_norm_cust[norm] = c
        except Exception:  # noqa: BLE001
            pass

    # Eşlemeleri uygula
    for norm, call_rows in by_norm_calls.items():
        cust = by_norm_cust.get(norm)
        if not cust:
            continue
        cust_view = {
            "id": cust["id"],
            "name": cust.get("name"),
            "phone": cust.get("phone"),
        }
        for r in call_rows:
            r["customers"] = cust_view
            if persist and not r.get("customer_id"):
                try:
                    client.table("incoming_calls").update(
                        {"customer_id": cust["id"]}
                    ).eq("id", r.get("id")).execute()
                    r["customer_id"] = cust["id"]
                except Exception:  # noqa: BLE001
                    pass
    return rows


def mark_processed(call_id: str) -> bool:
    get_client().table("incoming_calls").update({"is_processed": True}).eq(
        "id", call_id
    ).execute()
    return True


def mark_unanswered(call_id: str) -> bool:
    get_client().table("incoming_calls").update({"is_unanswered": True}).eq(
        "id", call_id
    ).execute()
    return True


def delete_call(call_id: str) -> bool:
    get_client().table("incoming_calls").delete().eq("id", call_id).execute()
    return True
