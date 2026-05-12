"""Kategori (categories) ve ürün (products) CRUD işlemleri."""

from __future__ import annotations

from typing import Any

from .supabase_client import get_client


# ---------------- Kategori ----------------
def list_categories(only_active: bool = True) -> list[dict[str, Any]]:
    query = (
        get_client()
        .table("categories")
        .select("*")
        .order("sort_order", desc=False)
        .order("name", desc=False)
    )
    if only_active:
        query = query.eq("is_active", True)
    return query.execute().data or []


def create_category(
    name: str,
    color: str | None = None,
    sort_order: int = 0,
) -> dict[str, Any]:
    payload = {"name": name, "color": color, "sort_order": sort_order}
    res = get_client().table("categories").insert(payload).execute()
    return (res.data or [{}])[0]


def update_category(category_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    res = (
        get_client()
        .table("categories")
        .update(updates)
        .eq("id", category_id)
        .execute()
    )
    return (res.data or [{}])[0]


def delete_category(category_id: str) -> bool:
    get_client().table("categories").delete().eq("id", category_id).execute()
    return True


# ---------------- Ürün ----------------
def list_products(
    category_id: str | None = None, only_active: bool = True
) -> list[dict[str, Any]]:
    query = (
        get_client()
        .table("products")
        .select("*,categories(name,color)")
        .order("sort_order", desc=False)
        .order("name", desc=False)
    )
    if only_active:
        query = query.eq("is_active", True)
    if category_id:
        query = query.eq("category_id", category_id)
    return query.execute().data or []


def create_product(
    name: str,
    price: float,
    unit: str = "adet",
    category_id: str | None = None,
    sort_order: int = 0,
) -> dict[str, Any]:
    payload = {
        "name": name,
        "price": price,
        "unit": unit,
        "category_id": category_id,
        "sort_order": sort_order,
    }
    res = get_client().table("products").insert(payload).execute()
    return (res.data or [{}])[0]


def update_product(product_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    res = (
        get_client()
        .table("products")
        .update(updates)
        .eq("id", product_id)
        .execute()
    )
    return (res.data or [{}])[0]


def delete_product(product_id: str) -> bool:
    get_client().table("products").delete().eq("id", product_id).execute()
    return True
