"""Müşteri sipariş geçmişi dialog'u — yeniden kullanılabilir."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from database import orders_db
from database.orders_db import STATUS_LABELS

COL_NO, COL_DATE, COL_TIME, COL_ADDR, COL_AMT, COL_STATUS = range(6)


class OrderHistoryDialog(QDialog):
    """Bir müşterinin son siparişlerini listeleyen, düzenle/sil butonlu dialog."""

    def __init__(
        self,
        customer_id: str,
        parent=None,
        *,
        main_window=None,
        stay_on_top: bool = False,
    ) -> None:
        super().__init__(parent)
        self._customer_id = customer_id
        self._main_window = main_window
        self.setWindowTitle("📋 Sipariş Geçmişi")
        self.setMinimumSize(660, 400)
        if stay_on_top:
            self.setWindowFlags(
                self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
            )

        self._build_ui()
        self._load_orders()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["S.No", "Tarih", "Saat", "Adres", "Tutar", "Durum"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(lambda _: self._on_edit())

        edit_btn = QPushButton("✏️ Düzenle")
        edit_btn.setToolTip("Seçili siparişi düzenle")
        delete_btn = QPushButton("🗑 Sil")
        delete_btn.setToolTip("Seçili siparişi sil")
        delete_btn.setStyleSheet("color: #D32F2F;")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(delete_btn)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: gray; font-size: 11px;")

        layout = QVBoxLayout(self)
        layout.addWidget(self.table, 1)
        layout.addLayout(btn_row)
        layout.addWidget(self.info_label)

        edit_btn.clicked.connect(self._on_edit)
        delete_btn.clicked.connect(self._on_delete)

    # ------------------------------------------------------------------
    def _load_orders(self) -> None:
        try:
            self._orders = orders_db.list_orders_by_customer(
                self._customer_id, limit=50
            )
        except Exception:  # noqa: BLE001
            self._orders = []

        self.table.setRowCount(0)
        for row_idx, o in enumerate(self._orders):
            self.table.insertRow(row_idx)

            # S.No
            num_item = QTableWidgetItem(str(o.get("order_number") or "-"))
            num_item.setData(Qt.ItemDataRole.UserRole, o.get("id"))
            self.table.setItem(row_idx, COL_NO, num_item)

            # Tarih
            od = o.get("order_date") or ""
            if od:
                try:
                    from datetime import datetime as _dt
                    d = _dt.strptime(od, "%Y-%m-%d")
                    od = d.strftime("%d.%m.%Y")
                except Exception:  # noqa: BLE001
                    pass
            self.table.setItem(row_idx, COL_DATE, QTableWidgetItem(od))

            # Saat
            dt = o.get("delivery_time") or ""
            self.table.setItem(
                row_idx, COL_TIME, QTableWidgetItem(dt[:5] if dt else "-")
            )

            # Adres
            addr = (o.get("customer_addresses") or {}).get("address_text") or "-"
            addr_item = QTableWidgetItem(addr[:50])
            addr_item.setToolTip(addr)
            self.table.setItem(row_idx, COL_ADDR, addr_item)

            # Tutar
            amt = float(o.get("total_amount") or 0)
            self.table.setItem(
                row_idx, COL_AMT, QTableWidgetItem(f"₺{amt:,.2f}")
            )

            # Durum
            status = STATUS_LABELS.get(o.get("status", ""), o.get("status", "-"))
            self.table.setItem(row_idx, COL_STATUS, QTableWidgetItem(status))

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            COL_ADDR, QHeaderView.ResizeMode.Stretch
        )
        self.info_label.setText(f"Son {len(self._orders)} sipariş gösteriliyor")

    # ------------------------------------------------------------------
    def _get_selected_order_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, COL_NO)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_edit(self) -> None:
        oid = self._get_selected_order_id()
        if not oid:
            return
        mw = self._main_window
        if mw and hasattr(mw, "_open_order"):
            self.close()
            mw._open_order(oid)

    def _on_delete(self) -> None:
        oid = self._get_selected_order_id()
        if not oid:
            return
        ans = QMessageBox.question(
            self,
            "Sipariş Sil",
            "Bu siparişi silmek istediğinize emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            orders_db.delete_order(oid)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Hata", str(exc))
            return
        self._load_orders()
