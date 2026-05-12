"""Ana pencere: header, sekmeler, realtime listener, gelen arama popup'ları."""

from __future__ import annotations

import sys
from typing import Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import config
from database import customers_db, orders_db
from database.realtime_listener import RealtimeListener
from database.supabase_client import get_client
from ui import themes
from ui.couriers_panel import CouriersPanel
from ui.customer_detail_dialog import CustomerDetailDialog
from ui.customers_panel import CustomersPanel
from ui.incoming_call_popup import IncomingCallPopup
from ui.incoming_calls_panel import IncomingCallsPanel
from ui.new_customer_dialog import NewCustomerDialog
from ui.order_detail_dialog import OrderDetailDialog
from ui.orders_panel import OrdersPanel
from ui.products_panel import ProductsPanel
from ui.receipt_preview import ReceiptPreviewDialog
from ui.settings_panel import SettingsPanel
from utils.helpers import fit_to_screen, format_phone


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")
        fit_to_screen(self, 1400, 900, min_w_ratio=0.5, min_h_ratio=0.5)

        self._popups: list[IncomingCallPopup] = []

        self._build_ui()
        self._start_listener()
        self._load_active_theme()
        self._refresh_last_customer()

    # ==================================================================
    # UI
    # ==================================================================
    def _build_ui(self) -> None:
        # Header
        self.header_title = QLabel(f"📦 {config.APP_NAME}")
        self.header_title.setObjectName("HeaderTitle")

        self.last_customer_label = QLabel("Son Kayıt: -")
        self.last_customer_label.setObjectName("HeaderInfo")
        self.last_customer_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()
        header_layout.addWidget(self.last_customer_label)

        header = QWidget()
        header.setObjectName("HeaderBar")
        # QWidget'lara QSS ile background uygulanması için gerekli
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.setLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.orders_panel = OrdersPanel()
        self.customers_panel = CustomersPanel()
        self.calls_panel = IncomingCallsPanel()
        self.products_panel = ProductsPanel()
        self.couriers_panel = CouriersPanel()
        self.settings_panel = SettingsPanel()

        self.tabs.addTab(self.orders_panel, "📋 Siparişler")
        self.tabs.addTab(self.calls_panel, "📞 Arama Geçmişi")
        self.tabs.addTab(self.customers_panel, "👥 Müşteriler")
        self.tabs.addTab(self.products_panel, "📦 Ürünler")
        self.tabs.addTab(self.couriers_panel, "🏍️ Kuryeler")
        self.tabs.addTab(self.settings_panel, "⚙️ Ayarlar")

        # Olay bağlantıları
        self.orders_panel.create_order_requested.connect(self._open_new_order)
        self.orders_panel.open_order_requested.connect(self._open_order)
        self.orders_panel.print_order_requested.connect(self._print_order)
        self.orders_panel.open_customer_requested.connect(self._open_customer_detail)

        self.calls_panel.create_order_requested.connect(self._open_new_order_for_customer)
        self.calls_panel.create_customer_requested.connect(
            self._open_new_customer_with_phone
        )
        self.calls_panel.create_guest_order_requested.connect(
            self._open_guest_order_for_phone
        )
        self.calls_panel.open_customer_requested.connect(self._open_customer_detail)

        self.customers_panel.open_customer_requested.connect(self._open_customer_detail)
        self.customers_panel.new_customer_requested.connect(self._open_new_customer)

        self.couriers_panel.open_order_requested.connect(self._open_order)

        self.settings_panel.theme_changed.connect(self._on_theme_changed)

        # Layout
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(header)
        central_layout.addWidget(self.tabs, 1)

        central = QWidget()
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Hazır")

    # ==================================================================
    # Realtime listener
    # ==================================================================
    def _start_listener(self) -> None:
        self.listener = RealtimeListener(poll_interval_seconds=2.0)
        self.listener.incoming_call_received.connect(self._on_incoming_call)
        self.listener.orders_changed.connect(self._on_orders_changed)
        self.listener.customers_changed.connect(self._on_customers_changed)
        self.listener.status_message.connect(self._on_listener_status)
        self.listener.start()

    def _stop_listener(self) -> None:
        if hasattr(self, "listener") and self.listener.isRunning():
            self.listener.stop()
            self.listener.wait(3000)

    def _on_listener_status(self, msg: str) -> None:
        self.status_bar.showMessage(msg, 5000)

    # ==================================================================
    # Olay yöneticileri
    # ==================================================================
    def _play_call_notification_sound(self) -> None:
        """Yeni gelen arama için kısa bildirim sesi çalar (cross-platform)."""
        try:
            if sys.platform.startswith("win"):
                import winsound

                # MB_ICONASTERISK = kısa, hoş 'ding' sistem sesi
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                return
        except Exception:  # noqa: BLE001
            pass
        # Linux/Mac veya winsound başarısız → Qt'nin terminal bell'i
        try:
            QApplication.beep()
        except Exception:  # noqa: BLE001
            pass

    def _on_incoming_call(self, call: dict[str, Any]) -> None:
        """Yeni gelen arama → popup göster + Arama Geçmişi panelini yenile."""
        # Bildirim sesi çal
        self._play_call_notification_sound()
        # Popup top-level olarak oluşturuluyor; referansı listeyle koruyoruz.
        popup = IncomingCallPopup(call, parent=self)
        popup.setStyleSheet(self.styleSheet())  # Tema uygula (top-level olduğu için inherit etmez)
        popup.create_order_requested.connect(self._open_new_order_for_customer)
        popup.create_customer_requested.connect(self._open_new_customer_with_phone)
        popup.create_guest_order_requested.connect(self._open_guest_order_for_phone)
        popup.closed.connect(self._on_popup_closed)

        self._popups.append(popup)
        # Windows'ta cascade pozisyonu önlemek için show()'dan ÖNCE konumlandır.
        # Popup constructor'da resize(360, 220) çağrıldığı için geometri belli.
        self._reposition_popups()
        popup.show()
        popup.raise_()
        popup.activateWindow()
        # Windows'ta bazen show() sonrası WM final geometriyi commit ettikten sonra
        # tekrar konum ayarı gerekebilir (event loop bir kez dönsün).
        QTimer.singleShot(0, self._reposition_popups)

        # Arama geçmişi panelini yenile (eğer açıksa)
        try:
            self.calls_panel.refresh()
        except Exception:  # noqa: BLE001
            pass

    def _on_popup_closed(self, popup: IncomingCallPopup) -> None:
        if popup in self._popups:
            self._popups.remove(popup)
        self._reposition_popups()

    def _screen_for_main_window(self):
        """Multi-monitor'da MainWindow'un bulunduğu ekranı döndür.

        Fallback: primary screen. (Windows'ta sadece primaryScreen()
        kullanmak popup'ı yanlış ekrana atabilir.)
        """
        try:
            handle = self.windowHandle()
            if handle is not None:
                scr = handle.screen()
                if scr is not None:
                    return scr
        except Exception:  # noqa: BLE001
            pass
        return QGuiApplication.primaryScreen()

    def _reposition_popups(self) -> None:
        """Popup'ları cascade (çapraz) istifle.

        Mantık:
          • İlk popup: ekranın tam ortasında başlar.
          • Her sonraki popup: öncekinden +cascade_offset sağa ve aşağıya kayar.
          • Açık popup hiç kalmazsa fonksiyon erken döner; bir sonraki gelen
            popup yine i=0 olarak başladığı için **otomatik olarak ortada
            açılır** (ekstra state tutmaya gerek yok).
          • Ekran kenarını taşırsa clamp edilir.
        """
        screen = self._screen_for_main_window()
        if not screen or not self._popups:
            return
        geom = screen.availableGeometry()
        cascade_offset = 30  # piksel, hem x hem y için

        # İlk popup'ın boyutuna göre merkez başlangıç noktasını hesapla.
        first = self._popups[0]
        first_w = first.width() if first.width() > 0 else max(
            first.sizeHint().width(), first.minimumSizeHint().width(), 360
        )
        first_h = first.height() if first.height() > 0 else max(
            first.sizeHint().height(), first.minimumSizeHint().height(), 220
        )
        base_x = geom.left() + (geom.width() - first_w) // 2
        base_y = geom.top() + (geom.height() - first_h) // 2

        for i, p in enumerate(self._popups):
            w = p.width() if p.width() > 0 else max(
                p.sizeHint().width(), p.minimumSizeHint().width(), 360
            )
            h = p.height() if p.height() > 0 else max(
                p.sizeHint().height(), p.minimumSizeHint().height(), 220
            )
            x = base_x + i * cascade_offset
            y = base_y + i * cascade_offset
            # Ekran dışına taşıyorsa clamp et (kullanıcı popup'a ulaşabilsin)
            x = max(geom.left() + 8, min(x, geom.right() - w - 8))
            y = max(geom.top() + 8, min(y, geom.bottom() - h - 8))
            p.position_at(x, y)

    # ------------------------------------------------------------------
    def _on_orders_changed(self) -> None:
        # Sipariş paneli açıksa ve otomatik güncelleme aktifse yenile
        if (
            self.tabs.currentWidget() is self.orders_panel
            and self.orders_panel.auto_refresh_enabled
        ):
            self.orders_panel.refresh()
        # Kurye panelinin aktif sipariş sayıları için her zaman yenile
        self.couriers_panel.refresh()

    def _on_customers_changed(self) -> None:
        self._refresh_last_customer()
        if self.tabs.currentWidget() is self.customers_panel:
            self.customers_panel.refresh()

    # ------------------------------------------------------------------
    def _refresh_last_customer(self) -> None:
        try:
            cust = customers_db.latest_customer()
        except Exception:  # noqa: BLE001
            cust = None
        if cust:
            self.last_customer_label.setText(
                f"Son Kayıt: {cust.get('name', '-')}  ({format_phone(cust.get('phone', ''))})"
            )
        else:
            self.last_customer_label.setText("Son Kayıt: -")

    # ==================================================================
    # Diyalog açıcılar
    # ==================================================================
    def _open_new_order(self, customer_id: object = None) -> None:
        cust_id = customer_id if isinstance(customer_id, str) else None
        dlg = OrderDetailDialog(self, prefill_customer_id=cust_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.orders_panel.refresh()
            if dlg.print_after_save and dlg.saved_order_id:
                self._print_order(dlg.saved_order_id)

    def _open_new_order_for_customer(self, customer_id: str) -> None:
        self._open_new_order(customer_id)

    def _open_guest_order_for_phone(self, phone: str) -> None:
        """Misafir modunda OrderDetailDialog aç, telefonu prefill yap."""
        dlg = OrderDetailDialog(self, guest_mode=True, prefill_phone=phone)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.orders_panel.refresh()
            if dlg.print_after_save and dlg.saved_order_id:
                self._print_order(dlg.saved_order_id)

    def _open_order(self, order_id: str) -> None:
        dlg = OrderDetailDialog(self, order_id=order_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.orders_panel.refresh()
            self.couriers_panel.refresh()
            if dlg.print_after_save and dlg.saved_order_id:
                self._print_order(dlg.saved_order_id)

    def _open_customer_detail(self, customer_id: str) -> None:
        dlg = CustomerDetailDialog(customer_id, self)
        dlg.exec()
        self.customers_panel.refresh()
        self._refresh_last_customer()

    def _open_new_customer(self) -> None:
        dlg = NewCustomerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.customers_panel.refresh()
            self._refresh_last_customer()

    def _open_new_customer_with_phone(self, phone: str) -> None:
        dlg = NewCustomerDialog(self, prefill_phone=phone)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.customers_panel.refresh()
            self._refresh_last_customer()
            cust = dlg.created_customer
            if cust and cust.get("id"):
                # Yeni müşteri oluşturuldu → hemen sipariş aç
                self._open_new_order(cust["id"])

    def _print_order(self, order_id: str) -> None:
        try:
            order = orders_db.get_order(order_id)
            items = orders_db.list_order_items(order_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
            return
        if not order:
            return

        # Settings tablosundan işletme bilgilerini çek
        try:
            res = get_client().table("settings").select("*").execute()
            rows = res.data or []
        except Exception:  # noqa: BLE001
            rows = []
        settings = {r["key"]: r.get("value") or "" for r in rows}

        dlg = ReceiptPreviewDialog(order, items, settings, self)
        dlg.exec()

    # ==================================================================
    # Tema
    # ==================================================================
    def _load_active_theme(self) -> None:
        active = "light"
        try:
            res = (
                get_client()
                .table("settings")
                .select("value")
                .eq("key", "active_theme")
                .limit(1)
                .execute()
            )
            if res.data:
                active = res.data[0].get("value") or "light"
        except Exception:  # noqa: BLE001
            pass
        self._on_theme_changed(active)

    def _on_theme_changed(self, theme_name: str) -> None:
        app = QApplication.instance()
        if app is not None:
            themes.apply_theme(app, theme_name)

    # ==================================================================
    # Kapanış
    # ==================================================================
    def closeEvent(self, event):  # noqa: N802 - Qt API
        # Realtime listener'ı temiz bir şekilde durdur
        self._stop_listener()
        # Tüm popup'ları kapat
        for p in list(self._popups):
            p.close()
        super().closeEvent(event)
