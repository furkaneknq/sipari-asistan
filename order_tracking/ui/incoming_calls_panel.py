"""Arama Geçmişi paneli - tüm gelen aramaların listesi."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QCheckBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database import incoming_calls_db
from utils.helpers import format_phone, parse_iso_datetime


class IncomingCallsPanel(QWidget):
    """Arama Geçmişi sekmesi içeriği."""

    create_order_requested = pyqtSignal(str)  # customer_id
    create_customer_requested = pyqtSignal(str)  # phone
    create_guest_order_requested = pyqtSignal(str)  # phone (misafir sipariş)
    open_customer_requested = pyqtSignal(str)  # customer_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._calls: list[dict[str, Any]] = []
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Tek tarih seçimi — sadece seçili günün aramaları görünür
        today = date.today()
        self.selected_date = QDateEdit()
        self.selected_date.setCalendarPopup(True)
        self.selected_date.setDate(QDate(today.year, today.month, today.day))
        self.selected_date.setDisplayFormat("dd.MM.yyyy")
        self.selected_date.dateChanged.connect(self.refresh)

        today_btn = QPushButton("Bugün")
        today_btn.setObjectName("SecondaryButton")
        today_btn.clicked.connect(self._set_today)

        yesterday_btn = QPushButton("Dün")
        yesterday_btn.setObjectName("SecondaryButton")
        yesterday_btn.clicked.connect(self._set_yesterday)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Telefon veya müşteri adı")
        self.search_input.textChanged.connect(self.refresh)

        self.unprocessed_check = QCheckBox("Yalnızca işlenmemiş")
        self.unprocessed_check.toggled.connect(self.refresh)

        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.clicked.connect(self.refresh)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("📅 Tarih:"))
        toolbar.addWidget(self.selected_date)
        toolbar.addWidget(today_btn)
        toolbar.addWidget(yesterday_btn)
        toolbar.addSpacing(12)
        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.unprocessed_check)
        toolbar.addWidget(refresh_btn)

        # Tablo
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Tarih / Saat", "Telefon", "Müşteri", "Cihaz Adı", "Durum", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellDoubleClicked.connect(self._on_double_click)

        # Toplam kutusu
        self.summary_label = QLabel("Toplam: 0 arama")
        self.summary_label.setObjectName("SummaryBox")
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(self.summary_label)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self.table, 1)
        layout.addLayout(bottom_row)

    # ------------------------------------------------------------------
    def _set_today(self) -> None:
        today = date.today()
        self.selected_date.setDate(QDate(today.year, today.month, today.day))

    def _set_yesterday(self) -> None:
        d = date.today() - timedelta(days=1)
        self.selected_date.setDate(QDate(d.year, d.month, d.day))

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        try:
            qd = self.selected_date.date()
            d = date(qd.year(), qd.month(), qd.day())
            calls = incoming_calls_db.list_calls(
                start_date=d,
                end_date=d,
                only_unprocessed=self.unprocessed_check.isChecked(),
                search=self.search_input.text().strip(),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Yükleme Hatası", str(exc))
            return

        self._calls = calls
        self.table.setRowCount(0)
        for call in calls:
            row = self.table.rowCount()
            self.table.insertRow(row)
            customer = call.get("customers") or {}
            # Müşteri silindiyse customer_id NULL olur, join boş döner
            # enrich fonksiyonu da bulamayabilir → kayıtsız göster
            cust_id = customer.get("id")

            dt = parse_iso_datetime(call.get("created_at"))
            date_str = dt.strftime("%d.%m.%Y %H:%M:%S") if dt else ""
            date_item = QTableWidgetItem(date_str)
            date_item.setData(Qt.ItemDataRole.UserRole, call.get("id"))
            self.table.setItem(row, 0, date_item)

            phone_str = format_phone(call.get("phone_number") or "")
            self.table.setItem(row, 1, QTableWidgetItem(phone_str))

            cust_name = customer.get("name") or "(Kayıtsız)"
            cust_item = QTableWidgetItem(cust_name)
            cust_item.setData(Qt.ItemDataRole.UserRole, cust_id)
            if not cust_id:
                cust_item.setForeground(Qt.GlobalColor.darkGray)
            self.table.setItem(row, 2, cust_item)

            # Cihaz adı: phones tablosundan device_name göster
            device_name = (call.get("phones") or {}).get("device_name") or ""
            device_display = device_name or call.get("device_id") or "-"
            self.table.setItem(row, 3, QTableWidgetItem(device_display))
            is_unanswered = call.get("is_unanswered", False)
            if is_unanswered:
                status_text = "❌ Cevapsız"
            elif call.get("is_processed"):
                status_text = "✓ İşlendi"
            else:
                status_text = "● Yeni"
            status_item = QTableWidgetItem(status_text)
            if is_unanswered:
                status_item.setBackground(Qt.GlobalColor.red)
                status_item.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 4, status_item)

            # Hızlı butonlar
            if cust_id:
                btn = QPushButton("Sipariş Aç")
                btn.setObjectName("SuccessButton")
                btn.clicked.connect(
                    lambda _, cid=cust_id, call_id=call.get(
                        "id"
                    ): self._open_order_for(cid, call_id)
                )
                self.table.setCellWidget(row, 5, btn)
            else:
                # Kayıtsız numara: 'Misafir Sipariş' (öncelikli) + '+ Müşteri'
                wrap = QWidget()
                wrap_layout = QHBoxLayout(wrap)
                wrap_layout.setContentsMargins(2, 2, 2, 2)
                wrap_layout.setSpacing(4)

                guest_btn = QPushButton("📌 Misafir")
                guest_btn.setObjectName("SuccessButton")
                guest_btn.setToolTip("Müşteri kaydı oluşturmadan sipariş aç")
                guest_btn.clicked.connect(
                    lambda _, ph=call.get("phone_number") or "", call_id=call.get(
                        "id"
                    ): self._open_guest_order_for(ph, call_id)
                )
                cust_btn = QPushButton("+ Müşteri")
                cust_btn.clicked.connect(
                    lambda _, ph=call.get("phone_number") or "", call_id=call.get(
                        "id"
                    ): self._add_customer_for(ph, call_id)
                )
                wrap_layout.addWidget(guest_btn)
                wrap_layout.addWidget(cust_btn)
                self.table.setCellWidget(row, 5, wrap)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.summary_label.setText(f"Toplam: {len(calls)} arama")

    # ------------------------------------------------------------------
    def _selected_call(self) -> dict[str, Any] | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        call_id = item.data(Qt.ItemDataRole.UserRole)
        return next((c for c in self._calls if c.get("id") == call_id), None)

    def _on_double_click(self, _row: int, _col: int) -> None:
        call = self._selected_call()
        if not call:
            return
        cust = call.get("customers") or {}
        if cust.get("id"):
            self.open_customer_requested.emit(cust["id"])
        else:
            self.create_customer_requested.emit(call.get("phone_number") or "")

    def _open_order_for(self, customer_id: str, call_id: str | None) -> None:
        if call_id:
            try:
                incoming_calls_db.mark_processed(call_id)
            except Exception:  # noqa: BLE001
                pass
        self.create_order_requested.emit(customer_id)
        self.refresh()

    def _add_customer_for(self, phone: str, call_id: str | None) -> None:
        if call_id:
            try:
                incoming_calls_db.mark_processed(call_id)
            except Exception:  # noqa: BLE001
                pass
        self.create_customer_requested.emit(phone)
        self.refresh()

    def _open_guest_order_for(self, phone: str, call_id: str | None) -> None:
        """Müşteri kaydetmeden, telefon prefilled olarak misafir siparişi başlat."""
        if call_id:
            try:
                incoming_calls_db.mark_processed(call_id)
            except Exception:  # noqa: BLE001
                pass
        self.create_guest_order_requested.emit(phone)
        self.refresh()

    # ------------------------------------------------------------------
    def _show_context_menu(self, pos) -> None:
        call = self._selected_call()
        if not call:
            return
        menu = QMenu(self)
        cust = call.get("customers") or {}
        phone = call.get("phone_number") or ""

        if cust.get("id"):
            act = QAction("Müşteri Detayını Aç", self)
            act.triggered.connect(
                lambda: self.open_customer_requested.emit(cust["id"])
            )
            menu.addAction(act)
            order_act = QAction("Bu Müşteri için Sipariş Aç", self)
            order_act.triggered.connect(
                lambda: self._open_order_for(cust["id"], call.get("id"))
            )
            menu.addAction(order_act)
        else:
            guest_act = QAction("📌 Misafir Sipariş Oluştur", self)
            guest_act.triggered.connect(
                lambda: self._open_guest_order_for(phone, call.get("id"))
            )
            menu.addAction(guest_act)

            act = QAction("Yeni Müşteri Olarak Ekle", self)
            act.triggered.connect(
                lambda: self._add_customer_for(phone, call.get("id"))
            )
            menu.addAction(act)

        menu.addSeparator()

        if not call.get("is_processed"):
            mp = QAction("İşlendi olarak işaretle", self)
            mp.triggered.connect(lambda: self._mark_processed(call.get("id")))
            menu.addAction(mp)

        del_act = QAction("Kayıttan Sil", self)
        del_act.triggered.connect(lambda: self._delete_call(call.get("id")))
        menu.addAction(del_act)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _mark_processed(self, call_id: str | None) -> None:
        if not call_id:
            return
        try:
            incoming_calls_db.mark_processed(call_id)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _delete_call(self, call_id: str | None) -> None:
        if not call_id:
            return
        confirm = QMessageBox.question(
            self, "Sil", "Bu arama kaydı silinecek. Onaylıyor musun?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            incoming_calls_db.delete_call(call_id)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
