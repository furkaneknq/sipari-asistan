"""Gelen arama bildirim popup'ı.

Birden fazla popup eş zamanlı açılabilir; sağ üst köşeden aşağıya doğru
istiflenir. Her popup eşleşen müşteri varsa "Sipariş Oluştur" butonu,
yoksa "Yeni Müşteri" butonu gösterir.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.helpers import format_phone


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
        self.setObjectName("IncomingCallPopup")
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
        # Sabit yerine minimum: 'Misafir Sipariş' butonu sığsın
        self.setMinimumSize(360, 220)
        # show() öncesi gerçek boyut belli olsun — Windows'ta cascade pozisyonu
        # önlemek için move() çağrılırken width/height bilinmek zorunda.
        self.resize(360, 220)

        phone = call_data.get("phone_number") or ""
        customer = call_data.get("customers") or {}

        self.title_label = QLabel("📞 Gelen Arama")
        self.title_label.setObjectName("CallTitle")

        self.phone_label = QLabel(format_phone(phone) or phone)
        self.phone_label.setObjectName("CallNumber")

        button_row = QHBoxLayout()

        if customer.get("id"):
            self.match_label = QLabel(
                f"✓ {customer.get('name', '')}  (Kayıtlı)"
            )
            self.match_label.setObjectName("CallMatchYes")
            primary_btn = QPushButton("Sipariş Oluştur")
            primary_btn.setObjectName("SuccessButton")
            primary_btn.clicked.connect(
                lambda: self._on_primary_click(customer.get("id"))
            )
            button_row.addWidget(primary_btn)
        else:
            self.match_label = QLabel("✗ Kayıtsız Numara")
            self.match_label.setObjectName("CallMatchNo")

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
        layout.addStretch()
        layout.addLayout(button_row)

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
        self.closed.emit(self, unanswered)
        self.close()

    # ------------------------------------------------------------------
    def position_at(self, x: int, y: int) -> None:
        self.move(x, y)
