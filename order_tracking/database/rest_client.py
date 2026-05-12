"""Hafif PostgREST istemcisi — httpx ile doğrudan REST çağrısı.

supabase-py kütüphanesi sb_secret_ formatındaki anahtarları
desteklemediğinden, bu modül aynı .table().select().eq().execute()
arayüzünü sağlayarak drop-in yedek olarak çalışır.

Kullanım:
    client = RestClient("https://xxx.supabase.co", "sb_secret_xxx")
    res = client.table("customers").select("*").eq("id", "abc").execute()
    print(res.data)
"""

from __future__ import annotations

from typing import Any

import httpx


# ─── Yanıt nesnesi ───────────────────────────────────────────────────

class RestResponse:
    """supabase-py'nin execute() dönüşüyle uyumlu basit yanıt."""

    def __init__(self, data: list[dict[str, Any]], count: int | None = None):
        self.data: list[dict[str, Any]] = data
        self.count: int | None = count


# ─── Sorgu oluşturucu ────────────────────────────────────────────────

# Bu anahtarlar query string'de tek değer alır (yeni gelen eskiyi geçersiz kılar).
_UNIQUE_KEYS = {"select", "order", "limit", "offset", "on_conflict"}


class TableQueryBuilder:
    """Tek bir tablo üzerinde zincirleme sorgu oluşturur.

    _params, list[tuple[str, str]] olarak tutulur; böylece PostgREST'in
    aynı kolona birden çok filtre (örn. gte + lte) verilmesini destekler:
        ?order_date=gte.2026-05-11&order_date=lte.2026-05-11
    httpx, params'a list of tuples verilirse tekrarlayan key'leri korur.
    """

    def __init__(self, http: httpx.Client, table: str):
        self._http = http
        self._table = table
        self._params: list[tuple[str, str]] = []
        self._or_filters: list[str] = []
        self._payload: Any = None
        self._method = "GET"
        self._prefer: list[str] = []

    # ── Yardımcılar ───────────────────────────────────────────────────

    def _add_filter(self, column: str, value: str) -> None:
        """Aynı kolona ek filtre ekler (gte+lte gibi kombinasyonlar için)."""
        self._params.append((column, value))

    def _set_unique(self, key: str, value: str) -> None:
        """select/order/limit gibi tek değerli parametreyi günceller."""
        self._params = [(k, v) for k, v in self._params if k != key]
        self._params.append((key, value))

    def _get_unique(self, key: str) -> str | None:
        for k, v in self._params:
            if k == key:
                return v
        return None

    # ── Okuma ─────────────────────────────────────────────────────────

    def select(self, columns: str = "*", *, count: str | None = None):
        self._set_unique("select", columns)
        if count:
            self._prefer.append(f"count={count}")
        return self

    # ── Yazma ─────────────────────────────────────────────────────────

    def insert(self, payload: dict | list):
        self._method = "POST"
        self._payload = payload
        self._prefer.append("return=representation")
        return self

    def update(self, payload: dict):
        self._method = "PATCH"
        self._payload = payload
        self._prefer.append("return=representation")
        return self

    def upsert(self, payload: dict | list):
        self._method = "POST"
        self._payload = payload
        self._prefer.append("return=representation")
        self._prefer.append("resolution=merge-duplicates")
        return self

    def delete(self):
        self._method = "DELETE"
        return self

    # ── Filtreler ─────────────────────────────────────────────────────

    def eq(self, column: str, value: Any):
        self._add_filter(column, f"eq.{value}")
        return self

    def neq(self, column: str, value: Any):
        self._add_filter(column, f"neq.{value}")
        return self

    def gt(self, column: str, value: Any):
        self._add_filter(column, f"gt.{value}")
        return self

    def gte(self, column: str, value: Any):
        self._add_filter(column, f"gte.{value}")
        return self

    def lt(self, column: str, value: Any):
        self._add_filter(column, f"lt.{value}")
        return self

    def lte(self, column: str, value: Any):
        self._add_filter(column, f"lte.{value}")
        return self

    def like(self, column: str, pattern: str):
        self._add_filter(column, f"like.{pattern}")
        return self

    def ilike(self, column: str, pattern: str):
        self._add_filter(column, f"ilike.{pattern}")
        return self

    def is_(self, column: str, value: Any):
        self._add_filter(column, f"is.{value}")
        return self

    def in_(self, column: str, values: list):
        vals = ",".join(str(v) for v in values)
        self._add_filter(column, f"in.({vals})")
        return self

    def or_(self, expr: str):
        self._or_filters.append(f"({expr})")
        return self

    # ── Sıralama / Limit ─────────────────────────────────────────────

    def order(self, column: str, *, desc: bool = False):
        direction = "desc" if desc else "asc"
        new_part = f"{column}.{direction}"
        existing = self._get_unique("order") or ""
        merged = f"{existing},{new_part}".lstrip(",")
        self._set_unique("order", merged)
        return self

    def limit(self, count: int):
        self._set_unique("limit", str(count))
        return self

    def range(self, start: int, end: int):
        self._set_unique("offset", str(start))
        self._set_unique("limit", str(end - start + 1))
        return self

    # ── Çalıştır ──────────────────────────────────────────────────────

    def execute(self) -> RestResponse:
        url = f"/{self._table}"
        headers: dict[str, str] = {}
        if self._prefer:
            headers["Prefer"] = ", ".join(self._prefer)

        # Params'ı list olarak ilet (tekrarlayan key'ler korunur)
        params: list[tuple[str, str]] = list(self._params)
        if self._or_filters:
            params.append(("or", self._or_filters[-1]))

        if self._method == "GET":
            resp = self._http.get(url, params=params, headers=headers)

        elif self._method == "POST":
            # POST'ta yalnızca select/on_conflict query string'e gider
            q = [(k, v) for k, v in params if k in ("select", "on_conflict")]
            resp = self._http.post(url, json=self._payload,
                                   params=q, headers=headers)

        elif self._method == "PATCH":
            # PATCH'te tüm filtreler query string'e gider
            q = list(params)
            resp = self._http.patch(url, json=self._payload,
                                    params=q, headers=headers)

        elif self._method == "DELETE":
            resp = self._http.delete(url, params=params, headers=headers)

        else:
            raise ValueError(f"Bilinmeyen metod: {self._method}")

        resp.raise_for_status()

        data = resp.json() if resp.content else []
        if isinstance(data, dict):
            data = [data]

        # count header'dan al
        count = None
        content_range = resp.headers.get("content-range", "")
        if "/" in content_range:
            count_str = content_range.split("/")[-1]
            if count_str != "*":
                try:
                    count = int(count_str)
                except ValueError:
                    pass

        return RestResponse(data=data, count=count)


# ─── Ana istemci ──────────────────────────────────────────────────────

class RestClient:
    """supabase-py Client ile aynı .table() arayüzünü sağlar."""

    def __init__(self, url: str, key: str):
        self.supabase_url = url.rstrip("/")
        self.supabase_key = key
        self._http = httpx.Client(
            base_url=f"{self.supabase_url}/rest/v1",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=15.0,
        )

    def table(self, name: str) -> TableQueryBuilder:
        return TableQueryBuilder(self._http, name)

    def rpc(self, fn: str, params: dict | None = None) -> RestResponse:
        """PostgREST RPC çağrısı: POST /rest/v1/rpc/<fn>"""
        resp = self._http.post(
            f"/rpc/{fn}",
            json=params or {},
        )
        resp.raise_for_status()
        data = resp.json() if resp.content else []
        if isinstance(data, dict):
            data = [data]
        return RestResponse(data=data)
