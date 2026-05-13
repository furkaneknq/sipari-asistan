"""Gerçek zamanlı veri dinleyicisi.

Mimari notu:
    Supabase realtime websocket üzerinden çalışır ve asyncio gerektirir.
    PyQt'nin event loop'u ile asyncio'yu birleştirmek pratikte sorunlu
    olabildiği için bu masaüstü uygulamada **polling (sorgu döngüsü)**
    yaklaşımı kullanıyoruz. Belirli aralıklarla (varsayılan 2 saniye)
    veritabanını sorgular ve değişiklikleri Qt sinyalleri olarak yayınlar.

    Avantajları:
        * Bağlantı kopukluklarına dayanıklı (her döngüde yeniden dener)
        * Qt thread modeline uyumlu, race-condition yok
        * 2 saniyelik gecikme tipik kullanım için kabul edilebilir

    Gerçek websocket subscription istenirse ileride bu sınıf
    AsyncRealtimeListener ile değiştirilebilir.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from .supabase_client import get_client


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

    def __init__(self, poll_interval_seconds: float = 5.0, parent=None):
        super().__init__(parent)
        self._poll_interval_ms = int(poll_interval_seconds * 1000)
        self._running = True

        # Yeni arama tespiti: timestamp karşılaştırması yerine "gördüğüm id'ler"
        # ile çalışıyoruz. Bu, server/client saat farkı veya URL-encoding gibi
        # platform sorunlarından (özellikle Windows) etkilenmez.
        self._seen_call_ids: set[str] = set()
        self._first_call_poll: bool = True

        self._last_orders_updated_at: datetime | None = None
        self._last_customers_updated_at: datetime | None = None

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
            except Exception as exc:  # noqa: BLE001
                self.status_message.emit(f"Polling hatası: {exc}")
            self.msleep(self._poll_interval_ms)
        self.status_message.emit("Dinleyici durduruldu")

    # ------------------------------------------------------------------
    def _poll_incoming_calls(self) -> None:
        """incoming_calls tablosundan yeni satırları çeker.

        Strateji: Son 20 kaydı her seferinde çek; id'si daha önce
        görülmediyse 'yeni' kabul edip emit et. İlk poll'da hiçbir şey
        emit edilmez (uygulama başlangıcı eski aramalarla bombardımanı
        önlemek için), sadece mevcut id'ler 'görüldü' olarak işaretlenir.
        """
        client = get_client()
        res = (
            client.table("incoming_calls")
            .select("*,customers(id,name,phone)")
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

        # Yeni id'leri bul (en eskiden yeniye sırayla emit etmek için ters)
        new_rows: list[dict[str, Any]] = []
        for r in rows:
            rid = r.get("id")
            if rid and rid not in self._seen_call_ids:
                new_rows.append(r)

        # DB trigger'ı eşleştiremediyse popup'tan ÖNCE Python tarafında
        # eşleştir; aynı zamanda DB'deki customer_id'yi de doldur.
        if new_rows:
            try:
                from . import incoming_calls_db

                incoming_calls_db.enrich_calls_with_customer(
                    new_rows, persist=True
                )
            except Exception as exc:  # noqa: BLE001
                self.status_message.emit(f"Eşleştirme hatası: {exc}")

        for r in reversed(new_rows):
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
