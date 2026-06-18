"""Gerçek zamanlı veri dinleyicisi (v2 — performans optimize).

Mimari notu:
    PyQt'nin event loop'u ile asyncio'yu birleştirmek pratikte sorunlu
    olabildiği için bu masaüstü uygulamada **polling (sorgu döngüsü)**
    yaklaşımı kullanıyoruz.

    Performans stratejisi (v2):
        * Varsayılan polling aralığı: 10 saniye (UI yanıt süresi hâlâ iyi)
        * incoming_calls: hafif sorgu (sadece id,created_at,phone,device_id)
          → yeni satır tespitinde detaylar (customer JOIN) ayrıca çekilir
        * orders/customers: ``SELECT updated_at LIMIT 1`` — tek satır
        * Hata durumunda exponential backoff: 10s → 20s → 40s → max 60s
        * Başarılı sorgu sonrası backoff sıfırlanır

    Gerçek websocket subscription istenirse ileride bu sınıf
    AsyncRealtimeListener ile değiştirilebilir.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from .supabase_client import get_client

log = logging.getLogger(__name__)

# incoming_calls polling için sadece bu kolonlar çekilir (JOIN yok)
_CALLS_LIGHT_COLS = "id,created_at,phone_number,device_id,customer_id"


class RealtimeListener(QThread):
    """Arka planda Supabase'i sorgulayan dinleyici."""

    # Yeni gelen bir telefon araması (incoming_calls tablosu)
    incoming_call_received = pyqtSignal(dict)

    # Sipariş listesinde değişiklik olduğunda (yeni/güncellenmiş)
    orders_changed = pyqtSignal()

    # Müşteri listesinde değişiklik olduğunda
    customers_changed = pyqtSignal()

    # Bağlantı durumu mesajları (UI'da gösterilebilir)
    status_message = pyqtSignal(str)

    def __init__(self, poll_interval_seconds: float = 10.0, parent=None):
        super().__init__(parent)
        self._base_interval_ms = int(poll_interval_seconds * 1000)
        self._poll_interval_ms = self._base_interval_ms
        self._running = True

        # Yeni arama tespiti: "gördüğüm id'ler" ile çalışıyoruz.
        self._seen_call_ids: set[str] = set()
        self._first_call_poll: bool = True

        self._last_orders_updated_at: datetime | None = None
        self._last_customers_updated_at: datetime | None = None

        # Hata backoff
        self._consecutive_errors = 0

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------
    def run(self) -> None:  # noqa: D401 - Qt API
        self.status_message.emit("Dinleyici başlatıldı")
        while self._running:
            try:
                self._poll_incoming_calls()
                self._poll_orders()
                self._poll_customers()
                # Başarılı → backoff sıfırla
                if self._consecutive_errors > 0:
                    self._consecutive_errors = 0
                    self._poll_interval_ms = self._base_interval_ms
            except Exception as exc:  # noqa: BLE001
                self._consecutive_errors += 1
                # Exponential backoff: 10s → 20s → 40s → max 60s
                backoff = min(
                    self._base_interval_ms * (2 ** self._consecutive_errors),
                    60_000,
                )
                self._poll_interval_ms = backoff
                log.warning(
                    "Polling hatası (#%d, sonraki bekleme %ds): %s",
                    self._consecutive_errors, backoff // 1000, exc,
                )
                self.status_message.emit(f"Polling hatası: {exc}")
            self.msleep(self._poll_interval_ms)
        self.status_message.emit("Dinleyici durduruldu")

    # ------------------------------------------------------------------
    def _poll_incoming_calls(self) -> None:
        """incoming_calls tablosundan yeni satırları çeker.

        Strateji: Hafif kolonlarla son 20 kaydı çek; id'si daha önce
        görülmediyse 'yeni' kabul et. Yeni satır varsa detayları (customer
        JOIN dahil) sadece o satırlar için ayrıca çek.
        """
        client = get_client()
        res = (
            client.table("incoming_calls")
            .select(_CALLS_LIGHT_COLS)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        rows: list[dict[str, Any]] = res.data or []

        if self._first_call_poll:
            # İlk taramada sadece görüldü olarak işaretle, popup açma
            for r in rows:
                rid = r.get("id")
                if rid:
                    self._seen_call_ids.add(rid)
            self._first_call_poll = False
            return

        # Yeni id'leri bul
        new_ids: list[str] = []
        for r in rows:
            rid = r.get("id")
            if rid and rid not in self._seen_call_ids:
                new_ids.append(rid)

        # Yeni satır varsa detaylarını çek (customer JOIN dahil)
        if new_ids:
            detail_res = (
                client.table("incoming_calls")
                .select("*,customers(id,name,phone)")
                .in_("id", new_ids)
                .order("created_at", desc=False)
                .execute()
            )
            new_rows: list[dict[str, Any]] = detail_res.data or []

            # DB trigger'ı eşleştiremediyse Python tarafında eşleştir
            try:
                from . import incoming_calls_db

                incoming_calls_db.enrich_calls_with_customer(
                    new_rows, persist=True
                )
            except Exception as exc:  # noqa: BLE001
                self.status_message.emit(f"Eşleştirme hatası: {exc}")

            for r in new_rows:
                self.incoming_call_received.emit(r)

        # Tüm dönen id'leri 'görüldü' kabul et
        for r in rows:
            rid = r.get("id")
            if rid:
                self._seen_call_ids.add(rid)

        # Set'in sonsuz büyümesini engelle (son ~200 id'yi tut)
        if len(self._seen_call_ids) > 500:
            keep = {r.get("id") for r in rows if r.get("id")}
            self._seen_call_ids = keep

    def _poll_orders(self) -> None:
        """orders tablosunda updated_at değişen var mı bak."""
        client = get_client()
        res = (
            client.table("orders")
            .select("updated_at")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return
        latest = self._parse_ts(rows[0]["updated_at"])
        if (
            self._last_orders_updated_at is None
            or latest > self._last_orders_updated_at
        ):
            self._last_orders_updated_at = latest
            self.orders_changed.emit()

    def _poll_customers(self) -> None:
        """customers tablosunda updated_at değişen var mı bak."""
        client = get_client()
        res = (
            client.table("customers")
            .select("updated_at")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return
        latest = self._parse_ts(rows[0]["updated_at"])
        if (
            self._last_customers_updated_at is None
            or latest > self._last_customers_updated_at
        ):
            self._last_customers_updated_at = latest
            self.customers_changed.emit()

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_ts(value: str) -> datetime:
        """ISO 8601 string'i timezone-aware datetime'a çevirir."""
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        return datetime.fromisoformat(value)
