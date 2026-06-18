"""Gelen arama bildirim popup'ı.

Birden fazla popup eş zamanlı açılabilir; sağ üst köşeden aşağıya doğru
istiflenir. Her popup eşleşen müşteri varsa "Sipariş Oluştur" butonu,
yoksa "Yeni Müşteri" butonu gösterir.

Performans notu:
    * Her popup 30 sn sonra otomatik kapanır (cevapsız olarak).
    * Kullanıcı fare ile popup üzerindeyken timer durur.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.helpers import format_phone

# Otomatik kapanma süresi (ms)
_AUTO_CLOSE_MS = 30_000


class IncomingCallPopup(QWidget):
    """Frame'siz, üstte kalan, sağ üstte beliren küçük bildirim penceresi."""

    create_order_requested = pyqtSignal(str)  # customer_id
    create_customer_requested = pyqtSignal(str)  # phone
    create_guest_order_requested = pyqtSignal(str)  # phone
    closed = pyqtSignal(object, bool)  # self, was_unanswered

    def __init__(self, call_data: dict[str, Any], parent=None) -> None:
        # Parent verilse bile bağımsız bir top-level pencere olmalı.
        super().__init__(None)
        self._parent_ref = parent  # referansı garbage collection'a karşı koru
        self.call_data = call_data
        self._closed_internally = False
        self.setObjectName("IncomingCallPopup")
        self.setMouseTracking(True)

        # 30 sn sonra otomatik kapat (cevapsız)
        self._auto_close_timer = QTimer(self)
        self._auto_close_timer.setSingleShot(True)
        self._auto_close_timer.setInterval(_AUTO_CLOSE_MS)
        self._auto_close_timer.timeout.connect(lambda: self._close(unanswered=True))
        # Windows'ta WindowDoesNotAcceptFocus + WA_ShowWithoutActivating
        # kombinasyonu popup'ı bazen görünmez kılıyor.
        # Standart Window + StaysOnTop yeterli; başlık çubuğunu da koru
        # ki kullanıcı pencereyi taşıyıp/kapatabilsin (Frameless'i kaldırdık).
        self.setWindowTitle("📞 Gelen Arama")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        # Sabit yerine minimum: butonlar + uyarı sığsın
        self.setMinimumSize(360, 260)
        self.resize(360, 260)

        phone = call_data.get("phone_number") or ""
        customer = call_data.get("customers") or {}
        self._customer_id: str | None = customer.get("id")

        self.title_label = QLabel("📞 Gelen Arama")
        self.title_label.setObjectName("CallTitle")

        self.phone_label = QLabel(format_phone(phone) or phone)
        self.phone_label.setObjectName("CallNumber")

        button_row = QHBoxLayout()

        if self._customer_id:
            self.match_label = QLabel(
                f"✓ {customer.get('name', '')}  (Kayıtlı)"
            )
            self.match_label.setObjectName("CallMatchYes")

            # Bugünkü sipariş uyarısı
            self.today_label = QLabel("")
            self.today_label.setStyleSheet(
                "color: #E65100; font-weight: bold; font-size: 13px;"
            )
            self._check_today_orders(self._customer_id)

            primary_btn = QPushButton("Sipariş Oluştur")
            primary_btn.setObjectName("SuccessButton")
            primary_btn.clicked.connect(
                lambda: self._on_primary_click(customer.get("id"))
            )

            history_btn = QPushButton("📋 Geçmiş")
            history_btn.setToolTip("Son sipariş geçmişini göster")
            history_btn.clicked.connect(
                lambda: self._show_order_history(self._customer_id)
            )

            button_row.addWidget(primary_btn)
            button_row.addWidget(history_btn)
        else:
            self.match_label = QLabel("✗ Kayıtsız Numara")
            self.match_label.setObjectName("CallMatchNo")
            self.today_label = None

            guest_btn = QPushButton("📌 Misafir")
            guest_btn.setObjectName("SuccessButton")
            guest_btn.setToolTip("Müşteri kaydetmeden tek seferlik sipariş oluştur")
            guest_btn.clicked.connect(lambda: self._on_guest_order(phone))

            new_cust_btn = QPushButton("+ Müşteri")
            new_cust_btn.setToolTip("Müşteri kaydı oluştur")
            new_cust_btn.clicked.connect(lambda: self._on_new_customer(phone))

            button_row.addWidget(guest_btn)
            button_row.addWidget(new_cust_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("SecondaryButton")
        close_btn.setMaximumWidth(36)
        close_btn.setToolTip("Kapat")
        close_btn.clicked.connect(lambda: self._close(unanswered=True))
        button_row.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(self.title_label)
        layout.addWidget(self.phone_label)
        layout.addWidget(self.match_label)
        if self.today_label is not None:
            layout.addWidget(self.today_label)
        layout.addStretch()
        layout.addLayout(button_row)

    # ------------------------------------------------------------------
    # Sipariş geçmişi
    # ------------------------------------------------------------------
    def _check_today_orders(self, customer_id: str) -> None:
        """Bugün sipariş varsa uyarı etiketi göster."""
        try:
            from database import orders_db
            count = orders_db.count_today_orders(customer_id)
        except Exception:  # noqa: BLE001
            count = 0
        if count > 0:
            self.today_label.setText(f"⚠ Bugün {count} sipariş mevcut")
        else:
            self.today_label.setVisible(False)

    def _show_order_history(self, customer_id: str) -> None:
        """Sipariş geçmişi dialog'unu aç (ortak OrderHistoryDialog)."""
        from ui.order_history_dialog import OrderHistoryDialog
        dlg = OrderHistoryDialog(
            customer_id,
            parent=self,
            main_window=self._parent_ref,
            stay_on_top=True,
        )
        dlg.show()

    # ------------------------------------------------------------------
    # Bu üç callback'te önce _close() çağırıyoruz; çünkü signal'lerin slot'ları
    # modal dialog açıyor (sipariş/müşteri dialog'u). Modal dialog kapanana
    # kadar emit dönmediği için, emit'i önce yaparsak popup ekranda kalır.
    def _on_primary_click(self, customer_id: str | None) -> None:
        self._close()
        if customer_id:
            self.create_order_requested.emit(customer_id)

    def _on_new_customer(self, phone: str) -> None:
        self._close()
        self.create_customer_requested.emit(phone)

    def _on_guest_order(self, phone: str) -> None:
        self._close()
        self.create_guest_order_requested.emit(phone)

    def _close(self, unanswered: bool = False) -> None:
        self._auto_close_timer.stop()
        self._closed_internally = True
        self.closed.emit(self, unanswered)
        self.close()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._auto_close_timer.start()

    def enterEvent(self, event) -> None:  # noqa: N802
        # Fare popup üzerindeyken otomatik kapanmayı durdur
        self._auto_close_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        # Fare ayrılınca timer'ı yeniden başlat
        if not self._closed_internally:
            self._auto_close_timer.start()
        super().leaveEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._auto_close_timer.stop()
        # Pencere başlık çubuğundaki X tuşuyla kapatıldığında da
        # cevapsız arama olarak işaretle (iç ✕ butonu ile aynı davranış).
        if not self._closed_internally:
            self.closed.emit(self, True)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    def position_at(self, x: int, y: int) -> None:
        self.move(x, y)
