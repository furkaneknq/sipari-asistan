"""Adisyon önizleme penceresi."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
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
        # WindowModal: popup gibi bağımsız top-level pencereleri bloklamasın
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle(f"Adisyon Önizleme - #{order.get('order_number', '')}")
        fit_to_screen(self, 460, 720, min_w_ratio=0.25, min_h_ratio=0.5)

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
        layout.addLayout(button_row)

    def _print(self) -> None:
        ok, msg = print_receipt(self.order, self.items, self.settings)
        if ok:
            QMessageBox.information(self, "Yazıcı", msg)
        else:
            QMessageBox.warning(self, "Yazıcı", msg)
