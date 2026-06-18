"""Ürün paneli: kategori listesi (sol) + ürün tablosu (sağ)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database import products_db
from utils.helpers import format_currency


class ProductDialog(QDialog):
    """Ürün ekle/düzenle diyaloğu."""

    def __init__(
        self,
        parent=None,
        product: dict[str, Any] | None = None,
        category_id: str | None = None,
    ) -> None:
        super().__init__(parent)
        # WindowModal: popup gibi bağımsız top-level pencereleri bloklamasın
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.product = product
        self.category_id = (product or {}).get("category_id") or category_id
        self.setWindowTitle("Ürün Düzenle" if product else "Yeni Ürün")
        self.setMinimumWidth(360)

        self.name_input = QLineEdit((product or {}).get("name", ""))
        self.price_input = QDoubleSpinBox()
        self.price_input.setMaximum(999_999.99)
        self.price_input.setDecimals(2)
        self.price_input.setValue(float((product or {}).get("price") or 0))
        self.unit_input = QLineEdit((product or {}).get("unit", "adet"))
        self.sort_input = QSpinBox()
        self.sort_input.setMaximum(9999)
        self.sort_input.setValue(int((product or {}).get("sort_order") or 0))

        form = QFormLayout()
        form.addRow("Ad *", self.name_input)
        form.addRow("Fiyat *", self.price_input)
        form.addRow("Birim", self.unit_input)
        form.addRow("Sıra", self.sort_input)

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
            "price": float(self.price_input.value()),
            "unit": self.unit_input.text().strip() or "adet",
            "sort_order": int(self.sort_input.value()),
            "category_id": self.category_id,
        }


class ProductsPanel(QWidget):
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._categories: list[dict[str, Any]] = []
        self._current_category_id: str | None = None

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.cat_list = QListWidget()
        self.cat_list.itemSelectionChanged.connect(self._on_category_selected)
        self.cat_list.setMinimumWidth(200)
        self.cat_list.setMaximumWidth(280)

        add_cat_btn = QPushButton("+ Kategori")
        add_cat_btn.clicked.connect(self._add_category)
        del_cat_btn = QPushButton("Sil")
        del_cat_btn.setObjectName("DangerButton")
        del_cat_btn.clicked.connect(self._delete_category)

        cat_btn_row = QHBoxLayout()
        cat_btn_row.addWidget(add_cat_btn)
        cat_btn_row.addWidget(del_cat_btn)

        cat_layout = QVBoxLayout()
        cat_layout.addWidget(QLabel("Kategoriler"))
        cat_layout.addWidget(self.cat_list, 1)
        cat_layout.addLayout(cat_btn_row)

        cat_widget = QWidget()
        cat_widget.setLayout(cat_layout)

        # Sağ panel
        self.product_table = QTableWidget(0, 5)
        self.product_table.setHorizontalHeaderLabels(
            ["Ürün", "Fiyat", "Birim", "Aktif", ""]
        )
        self.product_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.product_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.product_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.product_table.cellDoubleClicked.connect(self._edit_product)

        new_prod_btn = QPushButton("+ Yeni Ürün")
        new_prod_btn.setObjectName("SuccessButton")
        new_prod_btn.setShortcut(QKeySequence("F2"))
        new_prod_btn.setToolTip("Yeni ürün ekle (F2)")
        new_prod_btn.clicked.connect(self._add_product)

        prod_layout = QVBoxLayout()
        prod_top = QHBoxLayout()
        prod_top.addWidget(QLabel("Ürünler"))
        prod_top.addStretch()
        prod_top.addWidget(new_prod_btn)
        prod_layout.addLayout(prod_top)
        prod_layout.addWidget(self.product_table, 1)

        prod_widget = QWidget()
        prod_widget.setLayout(prod_layout)

        main_layout = QHBoxLayout(self)
        main_layout.addWidget(cat_widget)
        main_layout.addWidget(prod_widget, 1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._reload_categories()
        self._reload_products()

    def _reload_categories(self) -> None:
        try:
            self._categories = products_db.list_categories(only_active=False)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
            return
        self.cat_list.clear()
        for cat in self._categories:
            it = QListWidgetItem(cat.get("name", ""))
            it.setData(Qt.ItemDataRole.UserRole, cat.get("id"))
            self.cat_list.addItem(it)
        if self._categories and self.cat_list.currentRow() < 0:
            self.cat_list.setCurrentRow(0)

    def _reload_products(self) -> None:
        self.product_table.setRowCount(0)
        if not self._current_category_id:
            return
        try:
            products = products_db.list_products(
                category_id=self._current_category_id, only_active=False
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
            return

        for p in products:
            row = self.product_table.rowCount()
            self.product_table.insertRow(row)
            id_value = p.get("id")

            name_item = QTableWidgetItem(p.get("name", ""))
            name_item.setData(Qt.ItemDataRole.UserRole, id_value)
            self.product_table.setItem(row, 0, name_item)
            self.product_table.setItem(
                row, 1, QTableWidgetItem(format_currency(p.get("price") or 0))
            )
            self.product_table.setItem(row, 2, QTableWidgetItem(p.get("unit") or ""))

            active = "✓" if p.get("is_active") else "—"
            active_item = QTableWidgetItem(active)
            active_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.product_table.setItem(row, 3, active_item)

            del_btn = QPushButton("🗑")
            del_btn.setObjectName("DangerButton")
            del_btn.setMaximumWidth(40)
            del_btn.clicked.connect(lambda _, pid=id_value: self._delete_product(pid))
            self.product_table.setCellWidget(row, 4, del_btn)

    # ------------------------------------------------------------------
    def _on_category_selected(self) -> None:
        item = self.cat_list.currentItem()
        if not item:
            self._current_category_id = None
            self._reload_products()
            return
        self._current_category_id = item.data(Qt.ItemDataRole.UserRole)
        self._reload_products()

    def _add_category(self) -> None:
        name, ok = QInputDialog.getText(self, "Yeni Kategori", "Kategori adı:")
        if not ok or not name.strip():
            return
        try:
            products_db.create_category(name.strip())
            self._reload_categories()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _delete_category(self) -> None:
        item = self.cat_list.currentItem()
        if not item:
            return
        cat_id = item.data(Qt.ItemDataRole.UserRole)
        if not cat_id:
            return
        confirm = QMessageBox.question(
            self,
            "Sil",
            f"'{item.text()}' kategorisi silinecek. İçindeki ürünlerin "
            "kategorisi boş bırakılacak. Onaylıyor musun?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            products_db.delete_category(cat_id)
            self._reload_categories()
            self._reload_products()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _add_product(self) -> None:
        if not self._current_category_id:
            QMessageBox.warning(self, "Uyarı", "Önce bir kategori seçin.")
            return
        dlg = ProductDialog(self, category_id=self._current_category_id)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        if not v["name"]:
            return
        try:
            products_db.create_product(
                name=v["name"],
                price=v["price"],
                unit=v["unit"],
                category_id=v["category_id"],
                sort_order=v["sort_order"],
            )
            self._reload_products()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _edit_product(self, row: int, _col: int) -> None:
        item = self.product_table.item(row, 0)
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole)
        if not pid:
            return
        try:
            products = products_db.list_products(
                category_id=self._current_category_id, only_active=False
            )
        except Exception:  # noqa: BLE001
            products = []
        product = next((p for p in products if p.get("id") == pid), None)
        if not product:
            return
        dlg = ProductDialog(self, product=product)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        v = dlg.values()
        try:
            products_db.update_product(
                pid,
                {
                    "name": v["name"],
                    "price": v["price"],
                    "unit": v["unit"],
                    "sort_order": v["sort_order"],
                },
            )
            self._reload_products()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _delete_product(self, product_id: str) -> None:
        confirm = QMessageBox.question(self, "Sil", "Bu ürün silinecek. Onaylıyor musun?")
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            products_db.delete_product(product_id)
            self._reload_products()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
