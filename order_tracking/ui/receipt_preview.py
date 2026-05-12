"""Adisyon önizleme penceresi."""

from __future__ import annotations

from typing import Any

import config
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.helpers import fit_to_screen
from utils.printer_handler import build_receipt_text, print_receipt


class ReceiptPreviewDialog(QDialog):
    def __init__(
        self,
        order: dict[str, Any],
        items: list[dict[str, Any]],
        settings: dict[str, str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle(f"Adisyon Önizleme - #{order.get('order_number', '')}")
        fit_to_screen(self, 500, 800, min_w_ratio=0.25, min_h_ratio=0.5)

        self.order = order
        self.items = items
        self.settings = settings

        text = build_receipt_text(order, items, settings, width=32)

        self.preview = QPlainTextEdit()
        self.preview.setPlainText(text)
        self.preview.setReadOnly(True)
        font = QFont("Courier New")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self.preview.setFont(font)
        self.preview.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Yazıcı seçimi
        self.printer_combo = QComboBox()
        self.printer_combo.addItems(["Dummy (Önizleme)", "USB", "Ağ (IP)", "Seri"])
        # Varsayılan seçimi config'ten belirle
        default_type = (config.PRINTER_TYPE or "dummy").lower()
        idx_map = {"dummy": 0, "usb": 1, "network": 2, "serial": 3}
        self.printer_combo.setCurrentIndex(idx_map.get(default_type, 0))
        self.printer_combo.currentIndexChanged.connect(self._on_printer_changed)

        # Parametre alanları
        self.param_vendor = self._param_input(config.PRINTER_USB_VENDOR_ID or "")
        self.param_product = self._param_input(config.PRINTER_USB_PRODUCT_ID or "")
        self.param_host = self._param_input(config.PRINTER_NETWORK_HOST or "")
        self.param_port = self._param_input(str(config.PRINTER_NETWORK_PORT or "9100"))

        self.usb_form = self._build_form(
            [("Vendor ID:", self.param_vendor), ("Product ID:", self.param_product)]
        )
        self.net_form = self._build_form(
            [("IP Adresi:", self.param_host), ("Port:", self.param_port)]
        )

        printer_layout = QVBoxLayout()
        printer_layout.addWidget(QLabel("Yazıcı:"))
        printer_layout.addWidget(self.printer_combo)
        printer_layout.addWidget(self.usb_form)
        printer_layout.addWidget(self.net_form)

        print_btn = QPushButton("Yazdır")
        print_btn.setObjectName("SuccessButton")
        print_btn.clicked.connect(self._print)

        close_btn = QPushButton("Kapat")
        close_btn.setObjectName("SecondaryButton")
        close_btn.clicked.connect(self.accept)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(close_btn)
        button_row.addWidget(print_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview)
        layout.addLayout(printer_layout)
        layout.addLayout(button_row)

        self._on_printer_changed()

    # ------------------------------------------------------------------
    # Yardımcı widget oluşturucular
    # ------------------------------------------------------------------
    @staticmethod
    def _param_input(text: str = ""):
        from PyQt6.QtWidgets import QLineEdit

        le = QLineEdit(text)
        le.setMaximumWidth(160)
        return le

    @staticmethod
    def _build_form(fields: list[tuple[str, QWidget]]) -> QWidget:
        from PyQt6.QtWidgets import QFormLayout

        w = QWidget()
        fl = QFormLayout(w)
        fl.setContentsMargins(0, 4, 0, 4)
        for label, widget in fields:
            fl.addRow(label, widget)
        return w

    def _on_printer_changed(self) -> None:
        idx = self.printer_combo.currentIndex()
        self.usb_form.setVisible(idx == 1)
        self.net_form.setVisible(idx == 2)

    def _print(self) -> None:
        idx = self.printer_combo.currentIndex()
        type_map = {0: "dummy", 1: "usb", 2: "network", 3: "serial"}
        ptype = type_map.get(idx, "dummy")

        opts: dict[str, Any] = {}
        if ptype == "usb":
            opts["vendor_id"] = self.param_vendor.text().strip()
            opts["product_id"] = self.param_product.text().strip()
        elif ptype == "network":
            opts["host"] = self.param_host.text().strip()
            try:
                opts["port"] = int(self.param_port.text().strip())
            except ValueError:
                opts["port"] = 9100

        ok, msg = print_receipt(
            self.order, self.items, self.settings,
            printer_type=ptype, printer_options=opts,
        )
        if ok:
            QMessageBox.information(self, "Yazıcı", msg)
        else:
            QMessageBox.warning(self, "Yazıcı", msg)
