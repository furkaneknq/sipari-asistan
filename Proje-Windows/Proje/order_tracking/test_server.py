"""TestSprite için geçici REST API sunucusu.

Desktop uygulamasının Supabase veritabanı işlemlerini
HTTP endpoint'leri üzerinden test edilebilir hale getirir.
Port 5000'de çalışır.
"""

from __future__ import annotations

import json
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

# Proje modüllerini import et
from database import customers_db, orders_db, products_db, couriers_db


def _json_serial(obj: Any) -> str:
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class APIHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, default=_json_serial, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _get_params(self) -> dict[str, str]:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        return {k: v[0] for k, v in qs.items()}

    def _parse_postgrest_id(self, params: dict[str, str], field: str = "id") -> str | None:
        """PostgREST formatındaki filtre parametrelerini ayrıştır.
        Örn: id=eq.abc-123 → abc-123
        """
        val = params.get(field, "")
        if val.startswith("eq."):
            return val[3:]
        return val or None

    def _parse_postgrest_search(self, params: dict[str, str]) -> str:
        """PostgREST ilike filtresinden arama terimini çıkar.
        Örn: phone=ilike.*534* → 534
        """
        for key, val in params.items():
            if val.startswith("ilike."):
                term = val[6:].strip("*")
                return term
        return ""

    def _route(self) -> str:
        path = urlparse(self.path).path.rstrip("/")
        # /rest/v1/xxx → /api/xxx dönüşümü
        if path.startswith("/rest/v1/"):
            table = path[len("/rest/v1/"):]
            result = f"/api/{table}"
            print(f"[ROUTE] {self.command} {self.path} → {result}")
            return result
        print(f"[ROUTE] {self.command} {self.path} → {path}")
        return path

    # ---- GET ----
    def do_GET(self) -> None:  # noqa: N802
        route = self._route()
        params = self._get_params()

        try:
            if route == "/":
                self._send_json({"status": "ok", "service": "order_tracking_test_api"})

            elif route == "/api/customers":
                # PostgREST-uyumlu: ?id=eq.xxx veya ?search=xxx veya ?phone=ilike.*xxx*
                cid = self._parse_postgrest_id(params)
                if cid:
                    data = customers_db.get_customer(cid)
                    self._send_json([data] if data else [], 200)
                else:
                    search = params.get("search", "") or self._parse_postgrest_search(params)
                    limit = int(params.get("limit", "50"))
                    data = customers_db.list_customers(search=search, limit=limit)
                    self._send_json(data)

            elif route == "/api/customers/by-id":
                cid = params.get("id", "")
                data = customers_db.get_customer(cid)
                self._send_json(data or {}, 200 if data else 404)

            elif route == "/api/customers/by-phone":
                phone = params.get("phone", "")
                data = customers_db.get_customer_by_phone(phone)
                self._send_json(data or {}, 200 if data else 404)

            elif route in ("/api/addresses", "/api/customer_addresses"):
                cid = self._parse_postgrest_id(params, "customer_id") or params.get("customer_id", "")
                data = customers_db.list_addresses(cid)
                self._send_json(data)

            elif route == "/api/orders":
                oid = self._parse_postgrest_id(params)
                if oid:
                    data = orders_db.get_order(oid)
                    self._send_json([data] if data else [], 200)
                else:
                    status = params.get("status")
                    courier_id = params.get("courier_id")
                    data = orders_db.list_orders(
                        target_date=date.today(),
                        status=status,
                        courier_id=courier_id,
                    )
                    self._send_json(data)

            elif route == "/api/orders/items" or route == "/api/order_items":
                oid = self._parse_postgrest_id(params, "order_id") or params.get("order_id", "")
                data = orders_db.list_order_items(oid)
                self._send_json(data)

            elif route == "/api/products":
                cat_id = params.get("category_id")
                data = products_db.list_products(category_id=cat_id)
                self._send_json(data)

            elif route == "/api/categories":
                data = products_db.list_categories()
                self._send_json(data)

            elif route == "/api/couriers":
                cid = self._parse_postgrest_id(params)
                if cid:
                    data = couriers_db.get_courier(cid)
                    self._send_json([data] if data else [], 200)
                else:
                    data = couriers_db.list_couriers()
                    self._send_json(data)

            else:
                self._send_json({"error": "Not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ---- POST ----
    def do_POST(self) -> None:  # noqa: N802
        route = self._route()
        body = self._read_body()

        try:
            if route == "/api/customers":
                try:
                    data = customers_db.create_customer(
                        name=body.get("name", ""),
                        phone=body.get("phone", ""),
                        email=body.get("email"),
                        notes=body.get("notes"),
                        is_guest=body.get("is_guest", False),
                    )
                    self._send_json(data, 201)
                except Exception as e:
                    if "duplicate" in str(e).lower() or "unique" in str(e).lower() or "409" in str(e):
                        self._send_json({"error": "Duplicate phone number"}, 409)
                    else:
                        raise

            elif route in ("/api/addresses", "/api/customer_addresses"):
                data = customers_db.create_address(
                    customer_id=body["customer_id"],
                    address_text=body.get("address_text", ""),
                    title=body.get("title", "Ev"),
                    latitude=body.get("latitude"),
                    longitude=body.get("longitude"),
                    is_default=body.get("is_default", False),
                )
                self._send_json(data, 201)

            elif route == "/api/orders":
                data = orders_db.create_order(
                    customer_id=body["customer_id"],
                    address_id=body.get("address_id"),
                    items=body.get("items", []),
                    payment_method=body.get("payment_method", "cash"),
                    notes=body.get("notes"),
                    courier_id=body.get("courier_id"),
                    status=body.get("status", "new"),
                )
                self._send_json(data, 201)

            elif route == "/api/products":
                data = products_db.create_product(
                    name=body.get("name", ""),
                    price=body.get("price", 0),
                    unit=body.get("unit", "adet"),
                    category_id=body.get("category_id"),
                )
                self._send_json(data, 201)

            elif route == "/api/categories":
                data = products_db.create_category(
                    name=body.get("name", ""),
                    color=body.get("color"),
                    sort_order=body.get("sort_order", 0),
                )
                self._send_json(data, 201)

            elif route == "/api/couriers":
                data = couriers_db.create_courier(
                    name=body.get("name", ""),
                    phone=body.get("phone", ""),
                    password=body.get("password"),
                    is_active=body.get("is_active", True),
                )
                self._send_json(data, 201)

            else:
                self._send_json({"error": "Not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ---- PATCH ----
    def do_PATCH(self) -> None:  # noqa: N802
        route = self._route()
        body = self._read_body()
        params = self._get_params()

        try:
            if route == "/api/customers":
                cid = self._parse_postgrest_id(params) or body.get("id", "")
                data = customers_db.update_customer(cid, body)
                self._send_json(data)

            elif route in ("/api/addresses", "/api/customer_addresses"):
                aid = self._parse_postgrest_id(params) or body.get("id", "")
                data = customers_db.update_address(aid, body)
                self._send_json(data)

            elif route == "/api/orders/status":
                oid = self._parse_postgrest_id(params) or body.get("id", "")
                data = orders_db.update_order_status(oid, body.get("status", ""))
                self._send_json(data)

            elif route == "/api/orders/payment":
                oid = self._parse_postgrest_id(params) or body.get("id", "")
                data = orders_db.update_order_payment(
                    oid,
                    payment_method=body.get("payment_method"),
                    payment_status=body.get("payment_status"),
                    total_amount=body.get("total_amount"),
                    paid_amount=body.get("paid_amount"),
                )
                self._send_json(data)

            elif route == "/api/orders/courier":
                oid = self._parse_postgrest_id(params) or body.get("id", "")
                data = orders_db.assign_courier(oid, body.get("courier_id"))
                self._send_json(data)

            elif route == "/api/orders":
                oid = self._parse_postgrest_id(params) or body.get("id", "")
                data = orders_db.update_order_status(oid, body.get("status", ""))
                self._send_json(data)

            elif route == "/api/products":
                pid = self._parse_postgrest_id(params) or body.get("id", "")
                data = products_db.update_product(pid, body)
                self._send_json(data)

            elif route == "/api/categories":
                cid = self._parse_postgrest_id(params) or body.get("id", "")
                data = products_db.update_category(cid, body)
                self._send_json(data)

            elif route == "/api/couriers":
                cid = self._parse_postgrest_id(params) or body.get("id", "")
                data = couriers_db.update_courier(cid, body)
                self._send_json(data)

            else:
                self._send_json({"error": "Not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    # ---- DELETE ----
    def do_DELETE(self) -> None:  # noqa: N802
        route = self._route()
        params = self._get_params()

        try:
            rid = self._parse_postgrest_id(params)
            if not rid:
                self._send_json({"error": "Missing id parameter"}, 400)
                return

            if route == "/api/customers":
                customers_db.delete_customer(rid)
                self._send_json({"deleted": True})

            elif route in ("/api/addresses", "/api/customer_addresses"):
                customers_db.delete_address(rid)
                self._send_json({"deleted": True})

            elif route == "/api/orders":
                orders_db.delete_order(rid)
                self._send_json({"deleted": True})

            elif route == "/api/products":
                products_db.delete_product(rid)
                self._send_json({"deleted": True})

            elif route == "/api/categories":
                products_db.delete_category(rid)
                self._send_json({"deleted": True})

            elif route == "/api/couriers":
                couriers_db.delete_courier(rid)
                self._send_json({"deleted": True})

            else:
                self._send_json({"error": "Not found"}, 404)

        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[API] {args[0]} {args[1]} {args[2]}")


def main() -> None:
    port = 5000
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    print(f"Test API sunucusu http://localhost:{port} adresinde çalışıyor")
    print("Durdurmak için Ctrl+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu kapatılıyor...")
        server.server_close()


if __name__ == "__main__":
    main()
