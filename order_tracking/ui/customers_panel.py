"""Müşteri paneli - arama, listeleme, Excel import/export, silme."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QCheckBox,
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
        delete_btn.setToolTip("Seçili müşteri(ler)i sil (Del)")
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

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["✓", "Ad Soyad", "Telefon", "E-posta", "Sipariş Sayısı"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
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
            if search:
                customers = customers_db.list_customers(search=search, limit=200)
            else:
                customers = customers_db.list_customers(limit=200)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Yükleme Hatası", str(exc))
            return

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for cust in customers:
            row = self.table.rowCount()
            self.table.insertRow(row)
            id_value = cust.get("id")

            # Checkbox
            checkbox = QCheckBox()
            checkbox.setStyleSheet("QCheckBox { margin-left: 4px; }")
            checkbox.setChecked(False)
            self.table.setCellWidget(row, 0, checkbox)

            # Ad Soyad
            name_item = QTableWidgetItem(cust.get("name") or "")
            name_item.setData(Qt.ItemDataRole.UserRole, id_value)
            self.table.setItem(row, 1, name_item)

            # Telefon
            self.table.setItem(
                row, 2, QTableWidgetItem(format_phone(cust.get("phone") or ""))
            )
            # E-posta
            self.table.setItem(row, 3, QTableWidgetItem(cust.get("email") or ""))

            # Sipariş Sayısı (detayda gösterilir, listede yüklenmez)
            count_item = QTableWidgetItem("")
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 4, count_item)
        self.table.setSortingEnabled(True)

    # ------------------------------------------------------------------
    def _selected_customer_id(self) -> str | None:
        """En son seçili (current) tek müşteri."""
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 1)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _selected_customer_ids(self) -> list[str]:
        """Tüm seçili müşteri ID'lerini döndür (satır seçimi + checkbox seçimi)."""
        result: list[str] = []
        checked_rows: set[int] = set()

        # Checkbox'lardan seçilen satırları bul
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if widget and isinstance(widget, QCheckBox) and widget.isChecked():
                checked_rows.add(row)

        # Seçili satırları da ekle
        selected_rows = {idx.row() for idx in self.table.selectedIndexes()}
        all_rows = checked_rows | selected_rows

        for row in sorted(all_rows):
            item = self.table.item(row, 1)
            if item:
                cid = item.data(Qt.ItemDataRole.UserRole)
                if cid:
                    result.append(cid)
        return result

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
        cids = self._selected_customer_ids()
        if not cids:
            QMessageBox.information(self, "Seçim", "Önce silinecek müşteriyi seçin.")
            return
        count = len(cids)
        if count == 1:
            text = "Bu müşteri ve tüm adresleri kalıcı olarak silinecek."
        else:
            text = f"{count} müşteri ve tüm adresleri kalıcı olarak silinecek."
        confirm = QMessageBox.question(
            self, "Müşteriyi Sil", f"{text}\n\nOnaylıyor musun?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        errors: list[str] = []
        for cid in cids:
            try:
                customers_db.delete_customer(cid)
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
        self.refresh()
        if errors:
            QMessageBox.critical(
                self,
                "Silme Hatası",
                f"{len(errors)} müşteri silinemedi.\n\n"
                + "\n".join(errors[:5])
                + ("\n…" if len(errors) > 5 else ""),
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
