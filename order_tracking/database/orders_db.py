"""Sipariş (orders) ve sipariş kalemi (order_items) CRUD işlemleri."""

from __future__ import annotations

from datetime import date
from typing import Any

from .supabase_client import get_client


# Sipariş durumları için sabitler
STATUS_NEW = "new"
STATUS_PREPARING = "preparing"
STATUS_ON_WAY = "on_way"
STATUS_DELIVERED = "delivered"
STATUS_CANCELLED = "cancelled"

ORDER_STATUSES = [
    STATUS_NEW,
    STATUS_PREPARING,
    STATUS_ON_WAY,
    STATUS_DELIVERED,
    STATUS_CANCELLED,
]

STATUS_LABELS = {
    STATUS_NEW: "Yeni",
    STATUS_PREPARING: "Hazırlanıyor",
    STATUS_ON_WAY: "Yolda",
    STATUS_DELIVERED: "Teslim Edildi",
    STATUS_CANCELLED: "İptal",
}


# ---------------- Sipariş ----------------
def list_orders(
    target_date: date | None = None,
    status: str | None = None,
    courier_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    customer_search: str | None = None,
) -> list[dict[str, Any]]:
    """Siparişleri filtreleyerek döndürür.

    target_date: Tek bir gün (start/end yerine kullanılır)
    start_date / end_date: Tarih aralığı (her ikisi de gerekli)
    status: Sipariş durumu
    courier_id: Kurye filtresi
    customer_search: Müşteri ismi/telefonuna göre filtre
    """
    query = (
        get_client()
        .table("orders")
        .select(
            "*,"
            "customers(name,phone),"
            "customer_addresses(title,address_text),"
            "couriers(name,phone)"
        )
        .order("created_at", desc=True)
    )
    if target_date is not None:
        query = query.eq("order_date", target_date.isoformat())
    elif start_date is not None and end_date is not None:
        query = query.gte("order_date", start_date.isoformat())
        query = query.lte("order_date", end_date.isoformat())
    if status:
        query = query.eq("status", status)
    if courier_id:
        query = query.eq("courier_id", courier_id)
    rows = query.execute().data or []

    if customer_search:
        s = customer_search.strip().lower()
        rows = [
            r
            for r in rows
            if s in (r.get("customers") or {}).get("name", "").lower()
            or s in (r.get("customers") or {}).get("phone", "")
        ]
    return rows


def order_items_summary(order_id: str) -> dict[str, float]:
    """Bir siparişin kalemlerinden toplam adet ve tutar hesaplar."""
    res = (
        get_client()
        .table("order_items")
        .select("quantity,total_price")
        .eq("order_id", order_id)
        .execute()
    )
    rows = res.data or []
    total_qty = sum(float(r.get("quantity") or 0) for r in rows)
    total_amt = sum(float(r.get("total_price") or 0) for r in rows)
    return {"quantity": total_qty, "total": total_amt}


def mark_delivered(order_id: str) -> dict[str, Any]:
    """Siparişi 'teslim edildi' olarak işaretler."""
    return update_order_status(order_id, STATUS_DELIVERED)


def list_customer_orders(customer_id: str) -> list[dict[str, Any]]:
    res = (
        get_client()
        .table("orders")
        .select("*")
        .eq("customer_id", customer_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def get_order(order_id: str) -> dict[str, Any] | None:
    res = (
        get_client()
        .table("orders")
        .select(
            "*,"
            "customers(name,phone,email),"
            "customer_addresses(title,address_text,latitude,longitude),"
            "couriers(name,phone)"
        )
        .eq("id", order_id)
        .limit(1)
        .execute()
    )
    return (res.data or [None])[0]


def create_order(
    customer_id: str,
    address_id: str | None,
    items: list[dict[str, Any]],
    payment_method: str = "cash",
    payment_status: str = "pending",
    notes: str | None = None,
    courier_id: str | None = None,
    order_date: date | None = None,
    delivery_time: str | None = None,
    delivery_date: date | None = None,
    status: str = STATUS_NEW,
    total_override: float | None = None,
    address_text: str | None = None,
) -> dict[str, Any]:
    """Yeni sipariş ve ilgili sipariş kalemlerini ekler.

    items: [{product_id, name (yedek), quantity, unit, unit_price, notes}]
    address_text: Sipariş anındaki adres metni (snapshot).
    """
    client = get_client()
    payload = {
        "customer_id": customer_id,
        "address_id": address_id,
        "courier_id": courier_id,
        "status": status,
        "order_date": (order_date or date.today()).isoformat(),
        "delivery_date": delivery_date.isoformat() if delivery_date else None,
        "delivery_time": delivery_time,
        "payment_method": payment_method,
        "payment_status": payment_status,
        "notes": notes,
        "address_text": address_text,
    }
    order = (client.table("orders").insert(payload).execute().data or [{}])[0]
    order_id = order.get("id")
    if not order_id:
        return order

    # Sipariş kalemleri
    item_rows = []
    for item in items:
        item_rows.append(
            {
                "order_id": order_id,
                "product_id": item.get("product_id"),
                "quantity": item.get("quantity", 1),
                "unit": item.get("unit", "adet"),
                "unit_price": item.get("unit_price", 0),
                "notes": item.get("notes"),
            }
        )
    if item_rows:
        client.table("order_items").insert(item_rows).execute()

    # Toplam tutarı override etmek istiyorsak (DB trigger zaten hesaplar
    # ama kullanıcı manuel girmiş olabilir)
    if total_override is not None:
        client.table("orders").update({"total_amount": total_override}).eq(
            "id", order_id
        ).execute()

    return get_order(order_id) or order


def update_order_status(order_id: str, status: str) -> dict[str, Any]:
    res = (
        get_client()
        .table("orders")
        .update({"status": status})
        .eq("id", order_id)
        .execute()
    )
    return (res.data or [{}])[0]


def update_order_payment(
    order_id: str,
    payment_method: str | None = None,
    payment_status: str | None = None,
    total_amount: float | None = None,
    paid_amount: float | None = None,
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    if payment_method is not None:
        updates["payment_method"] = payment_method
    if payment_status is not None:
        updates["payment_status"] = payment_status
    if total_amount is not None:
        updates["total_amount"] = total_amount
    if paid_amount is not None:
        updates["paid_amount"] = paid_amount
    if not updates:
        return {}
    res = (
        get_client()
        .table("orders")
        .update(updates)
        .eq("id", order_id)
        .execute()
    )
    return (res.data or [{}])[0]


def set_paid_amount(
    order_id: str,
    paid_amount: float,
    order_total: float | None = None,
) -> dict[str, Any]:
    """Ödenen tutarı yazar ve payment_status'ı otomatik türetir.

    paid <= 0          → 'pending'
    0 < paid < total   → 'partial'
    paid >= total      → 'paid'

    order_total verilmezse DB'den okunur.
    """
    client = get_client()

    # Sipariş toplamı verilmediyse çek
    if order_total is None:
        res = (
            client.table("orders")
            .select("total_amount")
            .eq("id", order_id)
            .limit(1)
            .execute()
        )
        rows = res.data or [{}]
        order_total = float(rows[0].get("total_amount") or 0)

    paid_amount = max(0.0, float(paid_amount))
    if paid_amount <= 0:
        status = "pending"
    elif paid_amount >= float(order_total) - 0.005:  # küçük yuvarlama toleransı
        status = "paid"
    else:
        status = "partial"

    res = (
        client.table("orders")
        .update({"paid_amount": paid_amount, "payment_status": status})
        .eq("id", order_id)
        .execute()
    )
    return (res.data or [{}])[0]


def assign_courier(order_id: str, courier_id: str | None) -> dict[str, Any]:
    res = (
        get_client()
        .table("orders")
        .update({"courier_id": courier_id})
        .eq("id", order_id)
        .execute()
    )
    return (res.data or [{}])[0]


def delete_order(order_id: str) -> bool:
    get_client().table("orders").delete().eq("id", order_id).execute()
    return True


# ---------------- Sipariş Kalemleri ----------------
def list_order_items(order_id: str) -> list[dict[str, Any]]:
    res = (
        get_client()
        .table("order_items")
        .select("*,products(name,unit)")
        .eq("order_id", order_id)
        .execute()
    )
    return res.data or []


def replace_order_items(
    order_id: str, items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Bir siparişin tüm kalemlerini siler ve yenilerini ekler."""
    client = get_client()
    client.table("order_items").delete().eq("order_id", order_id).execute()

    if not items:
        return []

    rows = []
    for item in items:
        rows.append(
            {
                "order_id": order_id,
                "product_id": item.get("product_id"),
                "quantity": item.get("quantity", 1),
                "unit": item.get("unit", "adet"),
                "unit_price": item.get("unit_price", 0),
                "notes": item.get("notes"),
            }
        )
    res = client.table("order_items").insert(rows).execute()
    return res.data or []
