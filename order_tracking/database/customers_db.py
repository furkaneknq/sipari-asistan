"""Müşteri (customers) ve adres (customer_addresses) CRUD işlemleri."""

from __future__ import annotations

from typing import Any

from .supabase_client import get_client


# ----------------------- MÜŞTERİ -----------------------
def list_customers(
    search: str = "",
    include_guests: bool = False,
    limit: int = 0,
) -> list[dict[str, Any]]:
    """Müşterileri (opsiyonel arama metniyle) listeler.

    include_guests=False (varsayılan): is_guest=true olan kayıtlar
    UI listelerinde görünmesin diye filtrelenir.
    limit=0: tüm kayıtlar (pagination ile).
    """
    client = get_client()

    if search:
        # Arama varsa tek sayfa yeterli (genelde az sonuç)
        query = client.table("customers").select("*").order("name", desc=False)
        if not include_guests:
            query = query.eq("is_guest", False)
        query = query.or_(f"name.ilike.%{search}%,phone.ilike.%{search}%")
        if limit > 0:
            query = query.limit(limit)
        else:
            query = query.limit(100)  # Arama sonuçlarını sınırla
        return query.execute().data or []

    # Arama yoksa tüm müşterileri pagination ile çek
    PAGE_SIZE = 1000
    all_data: list[dict[str, Any]] = []
    offset = 0
    max_records = limit if limit > 0 else 999999

    while len(all_data) < max_records:
        query = client.table("customers").select("*").order("name", desc=False)
        if not include_guests:
            query = query.eq("is_guest", False)
        query = query.range(offset, offset + PAGE_SIZE - 1)
        page = query.execute().data or []
        all_data.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return all_data[:max_records] if limit > 0 else all_data


def get_customer(customer_id: str) -> dict[str, Any] | None:
    res = (
        get_client()
        .table("customers")
        .select("*")
        .eq("id", customer_id)
        .limit(1)
        .execute()
    )
    return (res.data or [None])[0]


def get_customer_by_phone(phone: str) -> dict[str, Any] | None:
    """Telefon numarasından müşteri bulur.

    Numarayı son 10 haneye normalize eder ve en yaygın formatlarda
    ('5321234567', '05321234567', '+905321234567', '905321234567')
    DB'yi tarar. Bir de boşluk / tire içeren eski kayıtlar için
    son 4 haneyle 'ilike' fallback yapar, sonra Python tarafında
    normalize karşılaştırması ile doğrular.

    Aynı numarayla hem gerçek hem misafir kayıt varsa gerçek müşteri
    (is_guest=false) öncelikli döndürülür.
    """
    if not phone:
        return None

    from utils.helpers import normalize_phone

    norm = normalize_phone(phone)
    client = get_client()

    if not norm or len(norm) < 10:
        # Son çare: tam eşleşme (kısa veya boş numaralar için)
        res = (
            client.table("customers")
            .select("*")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        return (res.data or [None])[0]

    candidates = list(dict.fromkeys([
        norm,
        f"0{norm}",
        f"+90{norm}",
        f"90{norm}",
        phone,
    ]))

    # 1) Yaygın formatlarda tam eşleşme — misafir olmayan tercihli
    res = (
        client.table("customers")
        .select("*")
        .in_("phone", candidates)
        .order("is_guest", desc=False)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if rows:
        return rows[0]

    # 2) Boşluk/tire içeren eski kayıtlar için ilike fallback
    res = (
        client.table("customers")
        .select("*")
        .ilike("phone", f"%{norm[-4:]}%")
        .order("is_guest", desc=False)
        .limit(20)
        .execute()
    )
    for row in (res.data or []):
        if normalize_phone(row.get("phone", "")) == norm:
            return row
    return None


def create_customer(
    name: str,
    phone: str,
    email: str | None = None,
    notes: str | None = None,
    is_guest: bool = False,
) -> dict[str, Any]:
    payload = {
        "name": name,
        "phone": phone,
        "email": email,
        "notes": notes,
        "is_guest": is_guest,
    }
    res = get_client().table("customers").insert(payload).execute()
    return (res.data or [{}])[0]


def update_customer(customer_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    res = (
        get_client()
        .table("customers")
        .update(updates)
        .eq("id", customer_id)
        .execute()
    )
    return (res.data or [{}])[0]


def delete_customer(customer_id: str) -> bool:
    get_client().table("customers").delete().eq("id", customer_id).execute()
    return True


def latest_customer() -> dict[str, Any] | None:
    """Sona en son kaydolan (gerçek) müşteri — tek seferlikler hariç."""
    res = (
        get_client()
        .table("customers")
        .select("name,phone,created_at")
        .eq("is_guest", False)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return (res.data or [None])[0]


def count_customer_orders(customer_id: str) -> int:
    """Müşterinin toplam sipariş sayısı."""
    res = (
        get_client()
        .table("orders")
        .select("id", count="exact")
        .eq("customer_id", customer_id)
        .execute()
    )
    return res.count or 0


# ----------------------- ADRES -----------------------
def list_addresses(customer_id: str) -> list[dict[str, Any]]:
    res = (
        get_client()
        .table("customer_addresses")
        .select("*")
        .eq("customer_id", customer_id)
        .order("is_default", desc=True)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


def create_address(
    customer_id: str,
    address_text: str,
    title: str = "Ev",
    latitude: float | None = None,
    longitude: float | None = None,
    is_default: bool = False,
) -> dict[str, Any]:
    if is_default:
        # Önceki default'ları kaldır
        get_client().table("customer_addresses").update({"is_default": False}).eq(
            "customer_id", customer_id
        ).execute()
    payload = {
        "customer_id": customer_id,
        "title": title,
        "address_text": address_text,
        "latitude": latitude,
        "longitude": longitude,
        "is_default": is_default,
    }
    res = get_client().table("customer_addresses").insert(payload).execute()
    return (res.data or [{}])[0]


def update_address(address_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    res = (
        get_client()
        .table("customer_addresses")
        .update(updates)
        .eq("id", address_id)
        .execute()
    )
    return (res.data or [{}])[0]


def delete_address(address_id: str) -> bool:
    get_client().table("customer_addresses").delete().eq("id", address_id).execute()
    return True
