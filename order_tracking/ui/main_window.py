"""Ana pencere: header, sekmeler, realtime listener, gelen arama popup'ları."""

from __future__ import annotations

import sys
from typing import Any

from PyQt6.QtCore import QSettings, Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QKeySequence, QShortcut
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
from utils.helpers import fit_to_screen, format_phone, keep_widget_on_screen


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} v{config.APP_VERSION}")

        self._popups: list[IncomingCallPopup] = []
        self._last_call_data: dict[str, Any] | None = None

        self._build_ui()
        self._restore_window_placement()
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

        # Global klavye kısayolları (sekme değiştirme + yardım)
        self._setup_global_shortcuts()

        # Olay bağlantıları
        self.orders_panel.create_order_requested.connect(self._open_new_order)
        self.orders_panel.open_order_requested.connect(self._open_order)
        self.orders_panel.print_order_requested.connect(self._print_order)
        self.orders_panel.print_bulk_customer_requested.connect(self._print_bulk_customer)
        self.orders_panel.print_preparation_requested.connect(self._print_preparation)
        self.orders_panel.open_customer_requested.connect(self._open_customer_detail)
        self.orders_panel.show_last_call_popup_requested.connect(self._show_last_call_popup)

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
        self.listener = RealtimeListener(poll_interval_seconds=15.0)
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

    # ------------------------------------------------------------------
    def _setup_global_shortcuts(self) -> None:
        """Global klavye kısayolları."""
        # Ctrl+1 .. Ctrl+6 → ilgili sekmeyi aç
        for i in range(self.tabs.count()):
            sc = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
            sc.activated.connect(lambda idx=i: self.tabs.setCurrentIndex(idx))
        # F1 → kısayol yardımı
        help_sc = QShortcut(QKeySequence("F1"), self)
        help_sc.activated.connect(self._show_shortcuts_help)

        reset_window_sc = QShortcut(QKeySequence("Ctrl+0"), self)
        reset_window_sc.activated.connect(self._reset_window_placement)

        fullscreen_sc = QShortcut(QKeySequence("F11"), self)
        fullscreen_sc.activated.connect(self._toggle_fullscreen)

    def _show_shortcuts_help(self) -> None:
        """Tüm klavye kısayollarını gösteren yardım dialog'u."""
        html = """
        <h3>⌨ Klavye Kısayolları</h3>
        <table cellspacing="6" cellpadding="2">
          <tr><th align="left">Tuş</th><th align="left">İşlem</th></tr>
          <tr><td><b>Ctrl+1..6</b></td><td>Sekmeler arası geçiş</td></tr>
          <tr><td><b>Ctrl+0</b></td><td>Pencere boyutunu ve konumunu sıfırla</td></tr>
          <tr><td><b>F11</b></td><td>Tam ekran aç/kapat</td></tr>
          <tr><td><b>F1</b></td><td>Bu yardım penceresi</td></tr>
          <tr><td><b>F5</b></td><td>Listeyi yenile</td></tr>
          <tr><td colspan="2"><i>—— Siparişler sekmesi ——</i></td></tr>
          <tr><td><b>F2</b></td><td>Yeni sipariş</td></tr>
          <tr><td><b>F3</b></td><td>Seçili siparişi düzenle</td></tr>
          <tr><td><b>Del</b></td><td>Seçili siparişi sil</td></tr>
          <tr><td><b>Ctrl+P</b></td><td>Adisyon yazdır</td></tr>
          <tr><td><b>Ctrl+D</b></td><td>Teslim edildi olarak işaretle</td></tr>
          <tr><td colspan="2"><i>—— Müşteriler sekmesi ——</i></td></tr>
          <tr><td><b>F2</b></td><td>Yeni müşteri</td></tr>
          <tr><td><b>F3</b></td><td>Müşteriyi düzenle</td></tr>
          <tr><td><b>Del</b></td><td>Müşteriyi sil</td></tr>
          <tr><td><b>Ctrl+F</b></td><td>Arama kutusuna odaklan</td></tr>
          <tr><td colspan="2"><i>—— Ürünler / Kuryeler ——</i></td></tr>
          <tr><td><b>F2</b></td><td>Yeni ürün / yeni kurye</td></tr>
        </table>
        """
        QMessageBox.information(self, "Klavye Kısayolları", html)

    def _window_settings(self) -> QSettings:
        return QSettings("SiparisAsistani", config.APP_NAME)

    def _restore_window_placement(self) -> None:
        settings = self._window_settings()
        geometry = settings.value("main_window/geometry")
        state = settings.value("main_window/state")
        maximized = settings.value("main_window/maximized", False, type=bool)
        restored = False
        if geometry is not None:
            restored = self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state)
        if not restored:
            fit_to_screen(self, 1400, 900)
        keep_widget_on_screen(self)
        if maximized:
            self.showMaximized()

    def _save_window_placement(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        settings = self._window_settings()
        settings.setValue("main_window/geometry", self.saveGeometry())
        settings.setValue("main_window/state", self.saveState())
        settings.setValue("main_window/maximized", self.isMaximized())

    def _reset_window_placement(self) -> None:
        settings = self._window_settings()
        settings.remove("main_window/geometry")
        settings.remove("main_window/state")
        settings.remove("main_window/maximized")
        self.showNormal()
        fit_to_screen(self, 1400, 900)
        self.status_bar.showMessage("Pencere boyutu ve konumu sıfırlandı", 4000)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            keep_widget_on_screen(self)
        else:
            self.showFullScreen()

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

    # Aynı anda ekranda bulunabilecek maksimum popup sayısı
    _MAX_POPUPS = 3

    def _on_incoming_call(self, call: dict[str, Any]) -> None:
        """Yeni gelen arama → popup göster + Arama Geçmişi panelini yenile."""
        self._last_call_data = call

        # Aynı numaradan zaten açık popup varsa tekrar açma
        phone = call.get("phone_number") or call.get("phone") or ""
        if phone:
            for p in self._popups:
                existing_phone = (
                    p.call_data.get("phone_number")
                    or p.call_data.get("phone")
                    or ""
                )
                if existing_phone == phone:
                    # Mevcut popup'ı öne getir, yeni popup açma
                    p.raise_()
                    return

        # Bildirim sesi çal
        self._play_call_notification_sound()

        # Popup limiti: en fazla _MAX_POPUPS açık olabilir, fazlaysa en eskiyi kapat
        while len(self._popups) >= self._MAX_POPUPS:
            oldest = self._popups[0]
            oldest._close(unanswered=True)

        # Popup top-level olarak oluşturuluyor; referansı listeyle koruyoruz.
        popup = IncomingCallPopup(call, parent=self)
        popup.setStyleSheet(self.styleSheet())  # Tema uygula (top-level olduğu için inherit etmez)
        popup.create_order_requested.connect(self._open_new_order_for_customer)
        popup.create_customer_requested.connect(self._open_new_customer_with_phone)
        popup.create_guest_order_requested.connect(self._open_guest_order_for_phone)
        popup.closed.connect(self._on_popup_closed)

        self._popups.append(popup)
        # Windows'ta cascade pozisyonu önlemek için show()'dan ÖNCE konumlandır.
        self._reposition_popups()
        popup.show()
        popup.raise_()
        # Modal dialog (sipariş oluşturma vb.) açıkken focus çalma → donma riski
        if not QApplication.activeModalWidget():
            popup.activateWindow()
        # Windows'ta bazen show() sonrası WM final geometriyi commit ettikten sonra
        # tekrar konum ayarı gerekebilir (event loop bir kez dönsün).
        QTimer.singleShot(0, self._reposition_popups)

        # Arama geçmişi panelini yenile (eğer açıksa)
        if self.tabs.currentWidget() is self.calls_panel:
            try:
                self.calls_panel.refresh()
            except Exception:  # noqa: BLE001
                pass

    def _on_popup_closed(self, popup: IncomingCallPopup, was_unanswered: bool = False) -> None:
        if popup in self._popups:
            self._popups.remove(popup)
        self._reposition_popups()
        if was_unanswered:
            call_id = popup.call_data.get("id")
            if call_id:
                try:
                    from database import incoming_calls_db
                    incoming_calls_db.mark_unanswered(call_id)
                    self.calls_panel.refresh()
                except Exception as exc:  # noqa: BLE001
                    print(f"Cevapsız işaretleme hatası: {exc}")

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
        # Debounce: 2 sn bekle, süre dolunca refresh yap
        if not hasattr(self, "_orders_debounce"):
            self._orders_debounce = QTimer(self)
            self._orders_debounce.setSingleShot(True)
            self._orders_debounce.setInterval(2000)
            self._orders_debounce.timeout.connect(self._do_orders_refresh)
        # Zaten aktifse yeniden başlatma (debounce)
        if self._orders_debounce.isActive():
            return
        self._orders_debounce.start()

    def _do_orders_refresh(self) -> None:
        current = self.tabs.currentWidget()
        if current is self.orders_panel and self.orders_panel.auto_refresh_enabled:
            self.orders_panel.refresh()
        elif current is self.couriers_panel:
            self.couriers_panel.refresh()

    def _on_customers_changed(self) -> None:
        # Debounce: 2 sn bekle, süre dolunca refresh yap
        if not hasattr(self, "_customers_debounce"):
            self._customers_debounce = QTimer(self)
            self._customers_debounce.setSingleShot(True)
            self._customers_debounce.setInterval(2000)
            self._customers_debounce.timeout.connect(self._do_customers_refresh)
        if self._customers_debounce.isActive():
            return
        self._customers_debounce.start()

    def _do_customers_refresh(self) -> None:
        self._refresh_last_customer()
        self.customers_panel.invalidate_cache()
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
            self.orders_panel.refresh(clear_cache=True)
            if dlg.print_after_save and dlg.saved_order_id:
                self._print_order(dlg.saved_order_id)

    def _show_last_call_popup(self) -> None:
        """Son gelen arama popup'ını tekrar göster (ses çalmadan)."""
        if not self._last_call_data:
            QMessageBox.information(self, "Bilgi", "Henüz gelen arama yok.")
            return
        call = self._last_call_data
        popup = IncomingCallPopup(call, parent=self)
        popup.setStyleSheet(self.styleSheet())
        popup.create_order_requested.connect(self._open_new_order_for_customer)
        popup.create_customer_requested.connect(self._open_new_customer_with_phone)
        popup.create_guest_order_requested.connect(self._open_guest_order_for_phone)
        popup.closed.connect(self._on_popup_closed)
        self._popups.append(popup)
        popup.show()

    def _open_new_order_for_customer(self, customer_id: str) -> None:
        dlg = OrderDetailDialog(self, prefill_customer_id=customer_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.orders_panel.refresh(clear_cache=True)
            if dlg.print_after_save and dlg.saved_order_id:
                self._print_order(dlg.saved_order_id)

    def _open_guest_order_for_phone(self, phone: str) -> None:
        dlg = OrderDetailDialog(self, guest_mode=True, prefill_phone=phone)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.orders_panel.refresh(clear_cache=True)
            if dlg.print_after_save and dlg.saved_order_id:
                self._print_order(dlg.saved_order_id)

    def _open_order(self, order_id: str) -> None:
        dlg = OrderDetailDialog(self, order_id=order_id)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.orders_panel.refresh(clear_cache=True)
            self.couriers_panel.refresh()
            if dlg.print_after_save and dlg.saved_order_id:
                self._print_order(dlg.saved_order_id)

    def _open_customer_detail(self, customer_id: str) -> None:
        dlg = CustomerDetailDialog(customer_id, self)
        dlg.exec()
        self.customers_panel.invalidate_cache()
        self.customers_panel.refresh()
        self._refresh_last_customer()

    def _open_new_customer(self) -> None:
        dlg = NewCustomerDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.customers_panel.invalidate_cache()
            self.customers_panel.refresh()
            self._refresh_last_customer()

    def _open_new_customer_with_phone(self, phone: str) -> None:
        dlg = NewCustomerDialog(self, prefill_phone=phone)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.customers_panel.invalidate_cache()
            self.customers_panel.refresh()
            self._refresh_last_customer()
            cust = dlg.created_customer
            if cust and cust.get("id"):
                # Yeni müşteri oluşturuldu → hemen sipariş aç
                self._open_new_order(cust["id"])

    def _get_settings(self) -> dict[str, str]:
        """Settings tablosundan işletme bilgilerini çeker."""
        try:
            res = get_client().table("settings").select("*").execute()
            rows = res.data or []
        except Exception:  # noqa: BLE001
            rows = []
        return {r["key"]: r.get("value") or "" for r in rows}

    def _print_order(self, order_id: str) -> None:
        try:
            order = orders_db.get_order(order_id)
            items = orders_db.list_order_items(order_id)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
            return
        if not order:
            return

        settings = self._get_settings()
        dlg = ReceiptPreviewDialog(order, items, settings, self)
        dlg.exec()

    def _print_bulk_customer(self, order_ids: list[str]) -> None:
        """Seçili siparişlerin müşteri fişlerini önizle ve yazdır (her biri arasında kesim)."""
        from utils.printer_handler import (
            build_customer_receipt_text,
            show_receipt_preview,
            _get_printer,
        )

        settings = self._get_settings()
        all_data: list[dict] = []
        preview_parts: list[str] = []

        for oid in order_ids:
            try:
                order = orders_db.get_order(oid)
                items = orders_db.list_order_items(oid)
            except Exception:  # noqa: BLE001
                continue
            if not order:
                continue

            from datetime import datetime
            customer = order.get("customers") or {}
            address = order.get("customer_addresses") or {}
            courier = order.get("couriers") or {}
            created_at = order.get("created_at") or datetime.now().isoformat()
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                date_str = dt.strftime("%d/%m/%Y")
                time_str = dt.strftime("%H:%M")
            except Exception:  # noqa: BLE001
                date_str = str(created_at)
                time_str = ""

            data = {
                "business_name": settings.get("company_name", "İşletme"),
                "business_address": settings.get("company_address", ""),
                "business_phone": settings.get("company_phone", ""),
                "order_number": order.get("order_number", ""),
                "date": date_str,
                "time": time_str,
                "customer_name": customer.get("name", ""),
                "customer_phone": customer.get("phone", ""),
                "customer_address": (
                    address.get("address_text") or order.get("address_text", "")
                ),
                "items": [
                    {
                        "name": (i.get("products") or {}).get("name") or i.get("name", ""),
                        "qty": i.get("quantity", 0),
                        "unit": i.get("unit") or (i.get("products") or {}).get("unit", "adet"),
                        "total": i.get("total_price", 0),
                    }
                    for i in items
                ],
                "total": order.get("total_amount", 0),
                "payment_method": {
                    "cash": "Nakit", "credit_card": "Kredi Kartı", "iban": "IBAN"
                }.get(order.get("payment_method") or "", "-"),
                "payment_amount": order.get("total_amount", 0),
                "courier_name": courier.get("name", ""),
                "note": order.get("notes", ""),
            }
            all_data.append(data)
            preview_parts.append(build_customer_receipt_text(data))

        if not all_data:
            QMessageBox.warning(self, "Uyarı", "Yazdırılacak sipariş bulunamadı.")
            return

        combined = ("\n\n--- KESİM ---\n\n").join(preview_parts)
        if not show_receipt_preview(self, combined, f"Müşteri Fişi ({len(all_data)} adet)"):
            return

        printer = _get_printer()
        if printer is None:
            QMessageBox.information(self, "Yazıcı", "Yazıcı yapılandırılmadı (dummy mod).")
            return

        try:
            for i, data in enumerate(all_data):
                text = build_customer_receipt_text(data)
                printer.set(align="left", font="a", bold=False, width=1, height=1)
                for line in text.split("\n"):
                    if line.startswith("TOPLAM:"):
                        printer.set(bold=True, width=2, height=2)
                        printer.text(line + "\n")
                        printer.set(bold=False, width=1, height=1)
                    else:
                        printer.text(line + "\n")
                printer.cut()
            printer.close()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Yazıcı Hatası", str(exc))

    def _print_preparation(self, order_ids: list[str]) -> None:
        """Seçili siparişlerin hazırlama fişini önizle ve yazdır."""
        from utils.printer_handler import (
            build_preparation_receipt_text,
            print_preparation_receipt,
            show_receipt_preview,
        )

        selected_orders: list[dict] = []
        for oid in order_ids:
            try:
                order = orders_db.get_order(oid)
                items = orders_db.list_order_items(oid)
            except Exception:  # noqa: BLE001
                continue
            if not order:
                continue
            selected_orders.append({
                "order_number": order.get("order_number", "?"),
                "items": [
                    {
                        "name": (i.get("products") or {}).get("name") or i.get("name", ""),
                        "quantity": i.get("quantity", 0),
                        "unit": i.get("unit") or (i.get("products") or {}).get("unit", "adet"),
                    }
                    for i in items
                ],
            })

        if not selected_orders:
            QMessageBox.warning(self, "Uyarı", "Yazdırılacak sipariş bulunamadı.")
            return

        text = build_preparation_receipt_text(selected_orders)
        if not show_receipt_preview(self, text, f"Hazırlama Fişi ({len(selected_orders)} sipariş)"):
            return

        ok, msg = print_preparation_receipt(selected_orders)
        if not ok:
            QMessageBox.warning(self, "Yazıcı", msg)

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
        self._save_window_placement()
        # Realtime listener'ı temiz bir şekilde durdur
        self._stop_listener()
        # Tüm popup'ları kapat
        for p in list(self._popups):
            p.close()
        super().closeEvent(event)
