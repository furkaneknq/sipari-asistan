"""Kurye (couriers) CRUD işlemleri."""

from __future__ import annotations

from typing import Any

from .supabase_client import get_client


def list_couriers(only_active: bool = False) -> list[dict[str, Any]]:
    query = get_client().table("couriers").select("*").order("name", desc=False)
    if only_active:
        query = query.eq("is_active", True)
    return query.execute().data or []


def get_courier(courier_id: str) -> dict[str, Any] | None:
    res = (
        get_client()
        .table("couriers")
        .select("*")
        .eq("id", courier_id)
        .limit(1)
        .execute()
    )
    return (res.data or [None])[0]


def create_courier(
    name: str,
    phone: str,
    password: str | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    payload = {
        "name": name,
        "phone": phone,
        "password": password,
        "is_active": is_active,
    }
    res = get_client().table("couriers").insert(payload).execute()
    return (res.data or [{}])[0]


def update_courier(courier_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    res = (
        get_client()
        .table("couriers")
        .update(updates)
        .eq("id", courier_id)
        .execute()
    )
    return (res.data or [{}])[0]


def delete_courier(courier_id: str) -> bool:
    get_client().table("couriers").delete().eq("id", courier_id).execute()
    return True


def count_active_orders(courier_id: str) -> int:
    """Kuryenin teslim edilmemiş ve iptal edilmemiş aktif sipariş sayısı."""
    res = (
        get_client()
        .table("orders")
        .select("id", count="exact")
        .eq("courier_id", courier_id)
        .in_("status", ["new", "preparing", "on_way"])
        .execute()
    )
    return res.count or 0


def list_courier_orders(courier_id: str) -> list[dict[str, Any]]:
    """Kuryeye atanmış güncel siparişler (en yeni üstte)."""
    res = (
        get_client()
        .table("orders")
        .select("*,customers(name,phone)")
        .eq("courier_id", courier_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []
