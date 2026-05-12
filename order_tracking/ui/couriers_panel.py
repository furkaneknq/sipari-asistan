"""Kurye paneli: liste + seçilen kuryenin aktif siparişleri."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database import couriers_db
from database.orders_db import STATUS_LABELS
from utils.helpers import format_currency, format_phone, normalize_phone


class CourierDialog(QDialog):
    def __init__(self, parent=None, courier: dict[str, Any] | None = None) -> None:
        super().__init__(parent)
        # WindowModal: popup gibi bağımsız top-level pencereleri bloklamasın
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.courier = courier
        self.setWindowTitle("Kurye Düzenle" if courier else "Yeni Kurye")
        self.setMinimumWidth(360)

        self.name_input = QLineEdit((courier or {}).get("name", ""))
        self.phone_input = QLineEdit(format_phone((courier or {}).get("phone", "")))
        self.password_input = QLineEdit((courier or {}).get("password", ""))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.active_check = QCheckBox("Aktif")
        self.active_check.setChecked((courier or {}).get("is_active", True))

        form = QFormLayout()
        form.addRow("Ad Soyad *", self.name_input)
        form.addRow("Telefon *", self.phone_input)
        form.addRow("Şifre", self.password_input)
        form.addRow("", self.active_check)

        save_btn = QPushButton("Kaydet")
        save_btn.setObjectName("SuccessButton")
        save_btn.clicked.connect(self.accept)

        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(cancel_btn)
        row.addWidget(save_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(row)

    def values(self) -> dict[str, Any]:
        return {
            "name": self.name_input.text().strip(),
            "phone": normalize_phone(self.phone_input.text()),
            "password": self.password_input.text() or None,
            "is_active": self.active_check.isChecked(),
        }


class CouriersPanel(QWidget):
    open_order_requested = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_courier_id: str | None = None
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        # Üst toolbar
        new_btn = QPushButton("+ Yeni Kurye")
        new_btn.setObjectName("SuccessButton")
        new_btn.clicked.connect(self._add_courier)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        toolbar.addWidget(new_btn)

        # Kurye tablosu
        self.courier_table = QTableWidget(0, 5)
        self.courier_table.setHorizontalHeaderLabels(
            ["Ad Soyad", "Telefon", "Aktif Sipariş", "Durum", ""]
        )
        self.courier_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.courier_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.courier_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.courier_table.cellDoubleClicked.connect(self._edit_courier)
        self.courier_table.itemSelectionChanged.connect(self._on_courier_selected)

        # Sipariş tablosu (alt)
        self.orders_label = QLabel("Seçilen kuryenin siparişleri:")
        self.orders_table = QTableWidget(0, 5)
        self.orders_table.setHorizontalHeaderLabels(
            ["Sipariş", "Müşteri", "Durum", "Tutar", "Ödeme"]
        )
        self.orders_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.orders_table.cellDoubleClicked.connect(self._on_order_double_click)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(QLabel("Kuryeler"))
        layout.addWidget(self.courier_table)
        layout.addWidget(self.orders_label)
        layout.addWidget(self.orders_table)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._reload_couriers()
        self._reload_orders()

    def _reload_couriers(self) -> None:
        try:
            couriers = couriers_db.list_couriers(only_active=False)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
            return
        self.courier_table.setRowCount(0)
        for cr in couriers:
            row = self.courier_table.rowCount()
            self.courier_table.insertRow(row)
            cr_id = cr.get("id")

            name_item = QTableWidgetItem(cr.get("name") or "")
            name_item.setData(Qt.ItemDataRole.UserRole, cr_id)
            self.courier_table.setItem(row, 0, name_item)
            self.courier_table.setItem(
                row, 1, QTableWidgetItem(format_phone(cr.get("phone") or ""))
            )

            try:
                count = couriers_db.count_active_orders(cr_id)
            except Exception:  # noqa: BLE001
                count = 0
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.courier_table.setItem(row, 2, count_item)

            status_text = "🟢 Aktif" if cr.get("is_active") else "🔴 Pasif"
            self.courier_table.setItem(row, 3, QTableWidgetItem(status_text))

            del_btn = QPushButton("🗑")
            del_btn.setObjectName("DangerButton")
            del_btn.setMaximumWidth(40)
            del_btn.clicked.connect(lambda _, x=cr_id: self._delete_courier(x))
            self.courier_table.setCellWidget(row, 4, del_btn)

    def _reload_orders(self) -> None:
        self.orders_table.setRowCount(0)
        if not self._current_courier_id:
            self.orders_label.setText("Seçilen kuryenin siparişleri: -")
            return
        try:
            orders = couriers_db.list_courier_orders(self._current_courier_id)
        except Exception:  # noqa: BLE001
            orders = []
        cr_name = ""
        for cr in couriers_db.list_couriers(only_active=False):
            if cr.get("id") == self._current_courier_id:
                cr_name = cr.get("name") or ""
                break
        self.orders_label.setText(f"{cr_name} - Siparişler ({len(orders)})")

        for o in orders:
            row = self.orders_table.rowCount()
            self.orders_table.insertRow(row)
            number_item = QTableWidgetItem(f"#{o.get('order_number')}")
            number_item.setData(Qt.ItemDataRole.UserRole, o.get("id"))
            self.orders_table.setItem(row, 0, number_item)
            cust = o.get("customers") or {}
            self.orders_table.setItem(
                row, 1, QTableWidgetItem(cust.get("name") or "-")
            )
            self.orders_table.setItem(
                row,
                2,
                QTableWidgetItem(STATUS_LABELS.get(o.get("status"), o.get("status") or "")),
            )
            self.orders_table.setItem(
                row, 3, QTableWidgetItem(format_currency(o.get("total_amount") or 0))
            )
            payment_status = {
                "pending": "Beklemede",
                "paid": "Ödendi",
                "partial": "Kısmi",
            }.get(o.get("payment_status") or "", o.get("payment_status") or "")
            self.orders_table.setItem(row, 4, QTableWidgetItem(payment_status))

    # ------------------------------------------------------------------
    def _on_courier_selected(self) -> None:
        row = self.courier_table.currentRow()
        if row < 0:
            self._current_courier_id = None
        else:
            item = self.courier_table.item(row, 0)
            self._current_courier_id = (
                item.data(Qt.ItemDataRole.UserRole) if item else None
            )
        self._reload_orders()

    def _on_order_double_click(self, row: int, _col: int) -> None:
        item = self.orders_table.item(row, 0)
        if not item:
            return
        order_id = item.data(Qt.ItemDataRole.UserRole)
        if order_id:
            self.open_order_requested.emit(order_id)

    # ------------------------------------------------------------------
    def _add_courier(self) -> None:
        dlg = CourierDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["name"] or not v["phone"]:
            QMessageBox.warning(self, "Eksik", "İsim ve telefon zorunlu.")
            return
        try:
            couriers_db.create_courier(
                name=v["name"],
                phone=v["phone"],
                password=v["password"],
                is_active=v["is_active"],
            )
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _edit_courier(self, row: int, _col: int) -> None:
        item = self.courier_table.item(row, 0)
        if not item:
            return
        cr_id = item.data(Qt.ItemDataRole.UserRole)
        if not cr_id:
            return
        cr = couriers_db.get_courier(cr_id)
        if not cr:
            return
        dlg = CourierDialog(self, courier=cr)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        try:
            updates = {
                "name": v["name"],
                "phone": v["phone"],
                "is_active": v["is_active"],
            }
            if v["password"]:
                updates["password"] = v["password"]
            couriers_db.update_courier(cr_id, updates)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _delete_courier(self, courier_id: str) -> None:
        confirm = QMessageBox.question(
            self, "Sil", "Bu kurye silinecek. Onaylıyor musun?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            couriers_db.delete_courier(courier_id)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
