"""Müşteri paneli - arama, listeleme, Excel import/export, silme."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database import customers_db
from utils.excel_handler import export_customers, import_customers
from utils.helpers import format_phone


class CustomersPanel(QWidget):
    """Müşteri arama + tablo + Excel butonları + silme."""

    open_customer_requested = pyqtSignal(str)
    new_customer_requested = pyqtSignal()
    refresh_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Ara: isim veya telefon")
        self.search_input.textChanged.connect(self.refresh)

        new_btn = QPushButton("+ Yeni Müşteri")
        new_btn.setObjectName("SuccessButton")
        new_btn.setShortcut(QKeySequence("F2"))
        new_btn.setToolTip("Yeni müşteri ekle (F2)")
        new_btn.clicked.connect(self.new_customer_requested.emit)

        edit_btn = QPushButton("✏ Düzenle")
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.setShortcut(QKeySequence("F3"))
        edit_btn.setToolTip("Seçili müşteriyi düzenle (F3)")
        edit_btn.clicked.connect(self._edit_selected)

        delete_btn = QPushButton("🗑 Sil")
        delete_btn.setObjectName("DangerButton")
        delete_btn.setShortcut(QKeySequence("Delete"))
        delete_btn.setToolTip("Seçili müşteriyi sil (Del)")
        delete_btn.clicked.connect(self._delete_selected)

        # Ctrl+F: Arama kutusuna odaklan
        search_sc = QShortcut(QKeySequence("Ctrl+F"), self)
        search_sc.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        search_sc.activated.connect(self._focus_search)

        import_btn = QPushButton("📥 Excel'den Aktar")
        import_btn.setObjectName("SecondaryButton")
        import_btn.clicked.connect(self._import_excel)

        export_btn = QPushButton("📤 Excel'e Aktar")
        export_btn.setObjectName("SecondaryButton")
        export_btn.clicked.connect(self._export_excel)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(import_btn)
        toolbar.addWidget(export_btn)
        toolbar.addWidget(edit_btn)
        toolbar.addWidget(delete_btn)
        toolbar.addWidget(new_btn)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Ad Soyad", "Telefon", "E-posta", "Sipariş Sayısı"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self.table, 1)

    # ------------------------------------------------------------------
    def _focus_search(self) -> None:
        """Ctrl+F: Arama kutusuna odaklan ve içeriği seç."""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def refresh(self) -> None:
        search = self.search_input.text().strip()
        try:
            customers = customers_db.list_customers(search=search)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Yükleme Hatası", str(exc))
            return

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for cust in customers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_value = cust.get("id")

            name_item = QTableWidgetItem(cust.get("name") or "")
            name_item.setData(Qt.ItemDataRole.UserRole, id_value)
            self.table.setItem(row, 0, name_item)

            self.table.setItem(
                row, 1, QTableWidgetItem(format_phone(cust.get("phone") or ""))
            )
            self.table.setItem(row, 2, QTableWidgetItem(cust.get("email") or ""))

            try:
                count = customers_db.count_customer_orders(id_value)
            except Exception:  # noqa: BLE001
                count = 0
            count_item = QTableWidgetItem(str(count))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, count_item)
        self.table.setSortingEnabled(True)

    # ------------------------------------------------------------------
    def _selected_customer_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_double_click(self, _row: int, _col: int) -> None:
        cid = self._selected_customer_id()
        if cid:
            self.open_customer_requested.emit(cid)

    def _edit_selected(self) -> None:
        cid = self._selected_customer_id()
        if not cid:
            QMessageBox.information(self, "Seçim", "Önce bir müşteri seçin.")
            return
        self.open_customer_requested.emit(cid)

    def _delete_selected(self) -> None:
        cid = self._selected_customer_id()
        if not cid:
            QMessageBox.information(self, "Seçim", "Önce silinecek müşteriyi seçin.")
            return
        # Müşterinin sipariş sayısı varsa uyar
        try:
            count = customers_db.count_customer_orders(cid)
        except Exception:  # noqa: BLE001
            count = 0
        warn = ""
        if count > 0:
            warn = (
                f"\n\nUYARI: Bu müşterinin {count} adet siparişi var. "
                "Müşteri silinirse bu siparişlerin müşteri bağlantısı kopar "
                "ve veritabanı bütünlüğü hatası alabilirsin."
            )
        confirm = QMessageBox.question(
            self,
            "Müşteriyi Sil",
            f"Bu müşteri ve tüm adresleri kalıcı olarak silinecek.{warn}\n\n"
            "Onaylıyor musun?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            customers_db.delete_customer(cid)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                "Silme Hatası",
                f"Müşteri silinemedi.\n\n{exc}\n\n"
                "Eğer aktif siparişleri varsa önce o siparişleri silin.",
            )

    # ------------------------------------------------------------------
    def _show_context_menu(self, pos) -> None:
        cid = self._selected_customer_id()
        if not cid:
            return
        menu = QMenu(self)

        open_act = QAction("📋 Detayı Aç", self)
        open_act.triggered.connect(lambda: self.open_customer_requested.emit(cid))
        menu.addAction(open_act)

        edit_act = QAction("✏ Düzenle", self)
        edit_act.triggered.connect(lambda: self.open_customer_requested.emit(cid))
        menu.addAction(edit_act)

        menu.addSeparator()

        del_act = QAction("🗑 Sil", self)
        del_act.triggered.connect(self._delete_selected)
        menu.addAction(del_act)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    def _export_excel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Excel'e Aktar", "musteriler.xlsx", "Excel (*.xlsx)"
        )
        if not path:
            return
        try:
            count = export_customers(path)
            QMessageBox.information(
                self, "Başarılı", f"{count} müşteri Excel'e aktarıldı."
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Excel'den Aktar", "", "Excel (*.xlsx *.xls)"
        )
        if not path:
            return
        try:
            stats = import_customers(path)
            QMessageBox.information(
                self,
                "İçe Aktarma Tamamlandı",
                f"Toplam: {stats['total']}\n"
                f"Eklendi: {stats['inserted']}\n"
                f"Atlandı (zaten var): {stats['skipped']}\n"
                f"Hatalı: {stats['failed']}",
            )
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "İçe Aktarma Hatası", str(exc))
