"""Sipariş paneli - Sipariş Asistan tarzı liste/tablo görünümü.

Sol panel : Mini takvim, hızlı tarih butonları, müşteri arama, işlem butonları
Sağ üst   : Sipariş tablosu (S.No, Tarih, Müşteri, Telefon, Ödeme, Adet, Tutar...)
Sağ orta  : Toplam kutuları (kayıt sayısı, toplam tutar, ödenen)
Sağ alt   : Seçilen siparişin kalemleri tablosu
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database import couriers_db, customers_db, orders_db, products_db
from ui.order_detail_dialog import _ClearOnZeroSpinBox
from database.orders_db import STATUS_DELIVERED, STATUS_NEW
from utils.helpers import format_currency, format_phone, parse_iso_datetime


PAYMENT_LABELS = {
    "cash": "Nakit",
    "credit_card": "Kredi Kartı",
    "iban": "IBAN",
    None: "-",
    "": "-",
}

COURIER_FILTER_TUM = "__all__"
COURIER_FILTER_ATANMAMIS = "__none__"


class NumericItem(QTableWidgetItem):
    """Sayısal değere göre sıralanan tablo hücresi."""

    def __init__(self, display_text: str, value: float):
        super().__init__(display_text)
        self._value = value

    def __lt__(self, other):  # noqa: D401 - Qt API
        if isinstance(other, NumericItem):
            return self._value < other._value
        return super().__lt__(other)


class OrdersPanel(QWidget):
    """Sipariş listesi paneli."""

    create_order_requested = pyqtSignal(object)
    open_order_requested = pyqtSignal(str)
    print_order_requested = pyqtSignal(str)
    print_bulk_customer_requested = pyqtSignal(list)
    print_preparation_requested = pyqtSignal(list)
    open_customer_requested = pyqtSignal(str)
    show_last_call_popup_requested = pyqtSignal()

    # Sütun indexleri
    COL_CHECK = 0
    COL_NUMBER = 1
    COL_DATE = 2
    COL_CUSTOMER = 3
    COL_PHONE = 4
    COL_ADDRESS = 5
    COL_PAYMENT = 6
    COL_QUANTITY = 7
    COL_AMOUNT = 8
    COL_PAID = 9
    COL_COURIER = 10
    COL_STATUS = 11

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.start_date: date = date.today()
        self.end_date: date = date.today()
        self._current_orders: list[dict[str, Any]] = []
        self._auto_refresh = True
        self._courier_filter: str | None = None  # None=Tümü, "__none__"=Atanmamış, uuid=spesifik kurye
        self._syncing_selection = False  # checkbox ↔ satır seçim senkronizasyon kilidi
        self._skip_next_refresh = False  # inline düzenleme sonrası polling refresh'i atla

        self._build_ui()
        self.refresh()

    # ==================================================================
    # UI
    # ==================================================================
    def _build_ui(self) -> None:
        # ---- SOL PANEL ----
        # Takvim
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.clicked.connect(self._on_calendar_clicked)
        self.calendar.setMaximumHeight(220)

        # Hızlı tarih butonları (sadece tek gün seçimi)
        today_btn = QPushButton("Bugün")
        today_btn.clicked.connect(lambda: self._set_range_today())
        yesterday_btn = QPushButton("Dün")
        yesterday_btn.clicked.connect(lambda: self._set_range_yesterday())

        for b in (today_btn, yesterday_btn):
            b.setObjectName("SecondaryButton")

        date_buttons = QHBoxLayout()
        date_buttons.addWidget(today_btn)
        date_buttons.addWidget(yesterday_btn)

        self.range_label = QLabel("")
        self.range_label.setObjectName("SettingsInfo")
        self.range_label.setWordWrap(True)

        calendar_box = QGroupBox("📅 Takvim")
        cal_layout = QVBoxLayout()
        cal_layout.addWidget(self.calendar)
        cal_layout.addLayout(date_buttons)
        cal_layout.addWidget(self.range_label)
        calendar_box.setLayout(cal_layout)

        # Kurye filtresi (couriers tablosundan dinamik doldurulacak)
        self.courier_filter_combo = QComboBox()
        self._populate_courier_filter()
        self.courier_filter_combo.currentIndexChanged.connect(self._on_courier_filter)

        filter_box = QGroupBox("🔍 Filtreler")
        f_layout = QVBoxLayout()
        f_layout.addWidget(QLabel("Kurye:"))
        f_layout.addWidget(self.courier_filter_combo)
        filter_box.setLayout(f_layout)

        # İşlem butonları (kısayol tuşları ile)
        new_btn = QPushButton("+ Yeni Sipariş")
        new_btn.setObjectName("SuccessButton")
        new_btn.setShortcut(QKeySequence("F2"))
        new_btn.setToolTip("Yeni sipariş oluştur (F2)")
        new_btn.clicked.connect(lambda: self.create_order_requested.emit(None))

        edit_btn = QPushButton("✏ Sipariş Düzelt")
        edit_btn.setShortcut(QKeySequence("F3"))
        edit_btn.setToolTip("Seçili siparişi düzenle (F3)")
        edit_btn.clicked.connect(self._edit_selected)

        delete_btn = QPushButton("🗑 Sil")
        delete_btn.setObjectName("DangerButton")
        delete_btn.setShortcut(QKeySequence("Delete"))
        delete_btn.setToolTip("Seçili sipariş(ler)i sil (Del)")
        delete_btn.clicked.connect(self._delete_selected)

        print_btn = QPushButton("🖨 Sipariş Fişi")
        print_btn.setShortcut(QKeySequence("Ctrl+P"))
        print_btn.setToolTip("Seçili sipariş(ler)in sipariş fişini yazdır (Ctrl+P)")
        print_btn.clicked.connect(self._print_customer_receipt)

        prep_btn = QPushButton("📋 Hazırlama Fişi")
        prep_btn.setShortcut(QKeySequence("Ctrl+H"))
        prep_btn.setToolTip("Seçili sipariş(ler)in hazırlama fişini yazdır (Ctrl+H)")
        prep_btn.clicked.connect(self._print_preparation_receipt)

        deliver_btn = QPushButton("✓ Teslim Edildi")
        deliver_btn.setObjectName("SuccessButton")
        deliver_btn.setShortcut(QKeySequence("Ctrl+D"))
        deliver_btn.setToolTip("Seçili sipariş(ler)i 'Teslim Edildi' yap (Ctrl+D)")
        deliver_btn.clicked.connect(self._mark_delivered)

        self.auto_refresh_check = QCheckBox("Listeyi otomatik güncelle")
        self.auto_refresh_check.setChecked(True)
        self.auto_refresh_check.toggled.connect(self._toggle_auto_refresh)

        show_popup_btn = QPushButton("📲 Son Çağrıyı Göster")
        show_popup_btn.setToolTip("Son gelen arama popup'ını tekrar aç")
        show_popup_btn.clicked.connect(self.show_last_call_popup_requested.emit)

        actions_box = QGroupBox("⚙ İşlemler")
        a_layout = QVBoxLayout()
        a_layout.addWidget(new_btn)
        a_layout.addWidget(show_popup_btn)
        a_layout.addWidget(edit_btn)
        a_layout.addWidget(deliver_btn)
        a_layout.addWidget(print_btn)
        a_layout.addWidget(prep_btn)
        a_layout.addWidget(delete_btn)
        a_layout.addSpacing(10)
        a_layout.addWidget(self.auto_refresh_check)
        actions_box.setLayout(a_layout)

        # Sol panel toplam — QScrollArea ile küçük ekranlarda kaydırılabilir
        left_content = QWidget()
        left_layout = QVBoxLayout(left_content)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.addWidget(calendar_box)
        left_layout.addWidget(filter_box)
        left_layout.addWidget(actions_box)
        left_layout.addStretch()

        left_panel = QScrollArea()
        left_panel.setWidget(left_content)
        left_panel.setWidgetResizable(True)
        left_panel.setFrameShape(QFrame.Shape.NoFrame)
        left_panel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_panel.setMinimumWidth(280)
        left_panel.setMaximumWidth(340)

        # ---- SAĞ PANEL ----
        # Üst başlık
        self.list_title = QLabel("Sipariş Listesi")
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        self.list_title.setFont(font)

        refresh_btn = QPushButton("🔄")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.setToolTip("Yenile (F5)")
        refresh_btn.setShortcut(QKeySequence("F5"))
        refresh_btn.setMaximumWidth(40)
        refresh_btn.clicked.connect(self.refresh)

        title_row = QHBoxLayout()
        title_row.addWidget(self.list_title)
        title_row.addStretch()
        title_row.addWidget(refresh_btn)

        # Sipariş tablosu
        self.orders_table = QTableWidget(0, 12)
        self.orders_table.setHorizontalHeaderLabels(
            [
                "✓",
                "S.No",
                "Tarih",
                "Müşteri",
                "Telefon",
                "Adres",
                "Ödeme",
                "Adet",
                "Tutar",
                "Ödenen",
                "Kurye",
                "Durum",
            ]
        )
        # Checkbox sütununu dar tut
        self.orders_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.orders_table.setColumnWidth(0, 36)
        self.orders_table.horizontalHeader().setSectionResizeMode(
            self.COL_ADDRESS, QHeaderView.ResizeMode.Stretch
        )
        self.orders_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.orders_table.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )
        # Checkbox dışına tıklayınca seçimi sıfırlamayı engelle
        self.orders_table.mousePressEvent = self._table_mouse_press
        self.orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.orders_table.setAlternatingRowColors(True)
        self.orders_table.setSortingEnabled(True)
        self.orders_table.verticalHeader().setVisible(False)
        self.orders_table.itemSelectionChanged.connect(self._on_order_selected)
        self.orders_table.cellDoubleClicked.connect(self._on_order_double_click)
        self.orders_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.orders_table.customContextMenuRequested.connect(self._show_context_menu)

        # Toplam kutuları (Sip.Asistan tarzı)
        self.summary_count = self._make_summary_box("0")
        self.summary_qty = self._make_summary_box("0")
        self.summary_total = self._make_summary_box("₺0,00")
        self.summary_paid = self._make_summary_box("₺0,00")

        summary_row = QHBoxLayout()
        summary_row.setSpacing(8)
        summary_row.addStretch()
        summary_row.addWidget(QLabel("Kayıt:"))
        summary_row.addWidget(self.summary_count)
        summary_row.addSpacing(12)
        summary_row.addWidget(QLabel("Adet:"))
        summary_row.addWidget(self.summary_qty)
        summary_row.addSpacing(12)
        summary_row.addWidget(QLabel("Sipariş Tutarı:"))
        summary_row.addWidget(self.summary_total)
        summary_row.addSpacing(12)
        summary_row.addWidget(QLabel("Ödenen:"))
        summary_row.addWidget(self.summary_paid)

        # Alt: Sipariş kalemleri
        items_label = QLabel("Sipariş Kalemleri")
        items_label.setStyleSheet("font-weight: bold; padding-top: 6px;")
        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(
            ["Kategori", "Ürün Adı", "Birim Fiyatı", "Adet", "Tutarı"]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setMaximumHeight(220)

        self.items_summary_qty = self._make_summary_box("0")
        self.items_summary_total = self._make_summary_box("₺0,00")
        items_summary_row = QHBoxLayout()
        items_summary_row.addStretch()
        items_summary_row.addWidget(QLabel("Toplam Adet:"))
        items_summary_row.addWidget(self.items_summary_qty)
        items_summary_row.addSpacing(12)
        items_summary_row.addWidget(QLabel("Toplam:"))
        items_summary_row.addWidget(self.items_summary_total)

        # Sipariş açıklaması
        self.order_notes_label = QLabel("Sipariş Açıklaması: -")
        self.order_notes_label.setObjectName("OrderNotes")
        self.order_notes_label.setWordWrap(True)

        # Sağ panel toplam
        right_top = QWidget()
        right_top_layout = QVBoxLayout(right_top)
        right_top_layout.setContentsMargins(4, 4, 4, 4)
        right_top_layout.addLayout(title_row)
        right_top_layout.addWidget(self.orders_table, 1)
        right_top_layout.addLayout(summary_row)

        right_bottom = QWidget()
        right_bottom_layout = QVBoxLayout(right_bottom)
        right_bottom_layout.setContentsMargins(4, 4, 4, 4)
        right_bottom_layout.addWidget(items_label)
        right_bottom_layout.addWidget(self.items_table, 1)
        right_bottom_layout.addLayout(items_summary_row)
        right_bottom_layout.addWidget(self.order_notes_label)

        right_split = QSplitter(Qt.Orientation.Vertical)
        right_split.addWidget(right_top)
        right_split.addWidget(right_bottom)
        right_split.setStretchFactor(0, 3)
        right_split.setStretchFactor(1, 2)

        # Ana layout
        main_split = QSplitter(Qt.Orientation.Horizontal)
        main_split.addWidget(left_panel)
        main_split.addWidget(right_split)
        main_split.setStretchFactor(0, 0)
        main_split.setStretchFactor(1, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.addWidget(main_split)

        self._update_range_label()

    def _make_summary_box(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("SummaryBox")
        lbl.setFrameShape(QFrame.Shape.Panel)
        lbl.setFrameShadow(QFrame.Shadow.Sunken)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setMinimumWidth(90)
        return lbl

    # ==================================================================
    # Tarih aralığı kontrolü
    # ==================================================================
    def _set_range_today(self) -> None:
        self.start_date = self.end_date = date.today()
        self._sync_calendar()
        self.refresh()

    def _set_range_yesterday(self) -> None:
        self.start_date = self.end_date = date.today() - timedelta(days=1)
        self._sync_calendar()
        self.refresh()

    def _on_calendar_clicked(self, qdate: QDate) -> None:
        d = date(qdate.year(), qdate.month(), qdate.day())
        self.start_date = self.end_date = d
        self.refresh()

    def _sync_calendar(self) -> None:
        self.calendar.blockSignals(True)
        self.calendar.setSelectedDate(
            QDate(self.end_date.year, self.end_date.month, self.end_date.day)
        )
        self.calendar.blockSignals(False)

    def _update_range_label(self) -> None:
        if self.start_date == self.end_date:
            self.range_label.setText(f"Tarih: {self.start_date.strftime('%d.%m.%Y')}")
        else:
            self.range_label.setText(
                f"Aralık: {self.start_date.strftime('%d.%m.%Y')} - "
                f"{self.end_date.strftime('%d.%m.%Y')}"
            )

    # ==================================================================
    # Filtre
    # ==================================================================
    def _on_courier_filter(self) -> None:
        val = self.courier_filter_combo.currentData()
        self._courier_filter = val if val != COURIER_FILTER_TUM else None
        self.refresh()

    def _populate_courier_filter(self) -> None:
        """Kurye combobox'ını DB'den günceller (yeni eklenen kuryeler için)."""
        # Mevcut seçimi koru
        current_data = self.courier_filter_combo.currentData() if hasattr(
            self, "courier_filter_combo"
        ) and self.courier_filter_combo.count() else COURIER_FILTER_TUM

        self.courier_filter_combo.blockSignals(True)
        self.courier_filter_combo.clear()
        self.courier_filter_combo.addItem("Tümü", COURIER_FILTER_TUM)
        self.courier_filter_combo.addItem("Atanmamış", COURIER_FILTER_ATANMAMIS)
        try:
            for c in couriers_db.list_couriers(only_active=True):
                self.courier_filter_combo.addItem(c.get("name") or "?", c.get("id"))
        except Exception as exc:  # noqa: BLE001
            print(f"[orders_panel] Kurye listesi yüklenemedi: {exc}")

        # Önceki seçimi geri yükle
        idx = self.courier_filter_combo.findData(current_data)
        if idx >= 0:
            self.courier_filter_combo.setCurrentIndex(idx)
        self.courier_filter_combo.blockSignals(False)

    def _toggle_auto_refresh(self, checked: bool) -> None:
        self._auto_refresh = checked

    @property
    def auto_refresh_enabled(self) -> bool:
        return self._auto_refresh

    # ==================================================================
    # Yenileme
    # ==================================================================
    def refresh(self, *, reload_couriers: bool = False) -> None:
        # Inline düzenleme sonrası polling'den gelen refresh'i atla
        if self._skip_next_refresh:
            self._skip_next_refresh = False
            return
        self._update_range_label()
        # Kurye listesini sadece istendiğinde güncelle (performans)
        if reload_couriers or not hasattr(self, "_couriers_loaded"):
            self._populate_courier_filter()
            self._couriers_loaded = True
        try:
            orders = orders_db.list_orders(
                start_date=self.start_date,
                end_date=self.end_date,
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Yükleme Hatası", str(exc))
            return

        self._current_orders = orders
        self._populate_orders_table(orders)
        self.list_title.setText(f"Sipariş Listesi  (Kayıt: {len(orders)})")

    def _populate_orders_table(self, orders: list[dict[str, Any]]) -> None:
        # Seçili sipariş ID'lerini kaydet (refresh sonrası geri yükle)
        _prev_selected_ids: set[str] = set()
        for idx in self.orders_table.selectedIndexes():
            item = self.orders_table.item(idx.row(), self.COL_NUMBER)
            if item:
                oid = item.data(Qt.ItemDataRole.UserRole)
                if oid:
                    _prev_selected_ids.add(oid)

        # Filtreleme (UI tarafında, hızlı)
        filtered = self._apply_local_filters(orders)

        # Batch kalem özetleri — N+1 sorgu yerine tek sorgu
        order_ids = [o.get("id") for o in filtered if o.get("id")]
        try:
            items_summary = orders_db.batch_order_items_summary(order_ids)
        except Exception:  # noqa: BLE001
            items_summary = {}

        self.orders_table.setUpdatesEnabled(False)
        self.orders_table.setSortingEnabled(False)
        self.orders_table.blockSignals(True)
        self.orders_table.setRowCount(0)

        total_qty = 0.0
        total_amt = 0.0
        total_paid = 0.0

        for order in filtered:
            row = self.orders_table.rowCount()
            self.orders_table.insertRow(row)

            customer = order.get("customers") or {}
            courier = order.get("couriers") or {}

            # Checkbox — satır seçimi ile senkron
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.toggled.connect(lambda checked, r=row: self._on_checkbox_toggled(r, checked))
            chk_wrapper = QWidget()
            chk_layout = QHBoxLayout(chk_wrapper)
            chk_layout.addWidget(checkbox)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk_layout.setContentsMargins(2, 0, 2, 0)
            chk_layout.setSpacing(0)
            self.orders_table.setCellWidget(row, self.COL_CHECK, chk_wrapper)

            # S.No (sayısal sıralanabilir)
            number = order.get("order_number") or 0
            num_item = NumericItem(str(number), float(number))
            num_item.setData(Qt.ItemDataRole.UserRole, order.get("id"))
            num_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
            self.orders_table.setItem(row, self.COL_NUMBER, num_item)

            # Tarih (order_date + delivery_time, takvim seçimiyle eşleşsin)
            od = order.get("order_date") or ""
            dtime = order.get("delivery_time") or ""
            if od:
                try:
                    from datetime import datetime as _dt
                    d_obj = _dt.strptime(od, "%Y-%m-%d")
                    date_display = d_obj.strftime("%d.%m.%Y")
                    if dtime:
                        date_display += f" {dtime[:5]}"
                    sort_key = d_obj.timestamp()
                except Exception:
                    date_display = od
                    sort_key = 0
            else:
                dt = parse_iso_datetime(order.get("created_at"))
                date_display = dt.strftime("%d.%m.%Y %H:%M") if dt else ""
                sort_key = dt.timestamp() if dt else 0
            date_item = NumericItem(date_display, sort_key)
            self.orders_table.setItem(row, self.COL_DATE, date_item)

            # Müşteri
            self.orders_table.setItem(
                row, self.COL_CUSTOMER, QTableWidgetItem(customer.get("name") or "-")
            )

            # Telefon
            self.orders_table.setItem(
                row,
                self.COL_PHONE,
                QTableWidgetItem(format_phone(customer.get("phone") or "")),
            )

            # Adres (snapshot tercihli, yoksa join'den gelen adres)
            snapshot_addr = order.get("address_text") or ""
            if snapshot_addr:
                addr_display = snapshot_addr
            else:
                addr = order.get("customer_addresses") or {}
                addr_text = addr.get("address_text") or ""
                addr_title = addr.get("title") or ""
                addr_display = f"{addr_title} - {addr_text}".strip(" -") if addr_text else "-"
            addr_item = QTableWidgetItem(addr_display)
            addr_item.setToolTip(addr_display)
            self.orders_table.setItem(row, self.COL_ADDRESS, addr_item)

            # Ödeme
            payment = PAYMENT_LABELS.get(order.get("payment_method"), "-")
            self.orders_table.setItem(row, self.COL_PAYMENT, QTableWidgetItem(payment))

            # Adet — toplam miktar (batch'ten oku, N+1 yok)
            summary = items_summary.get(order.get("id"), {})
            qty = summary.get("quantity", 0)
            qty_item = NumericItem(self._format_qty(qty), float(qty))
            qty_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.orders_table.setItem(row, self.COL_QUANTITY, qty_item)
            total_qty += qty

            amt = float(order.get("total_amount") or 0)
            total_amt += amt

            # Sipariş Tutarı (inline edit edilebilir)
            amt_sort_item = NumericItem("", amt)
            self.orders_table.setItem(row, self.COL_AMOUNT, amt_sort_item)
            amt_spin = self._make_amount_spin(order.get("id"), amt, row)
            self.orders_table.setCellWidget(row, self.COL_AMOUNT, amt_spin)

            # Ödenen (inline edit edilebilir)
            # Önce paid_amount kolonu, yoksa eski mantığa düş (payment_status='paid')
            if "paid_amount" in order and order.get("paid_amount") is not None:
                paid = float(order.get("paid_amount") or 0)
            else:
                payment_status = order.get("payment_status") or "pending"
                paid = amt if payment_status == "paid" else 0.0

            # Sıralama için arka planda numeric item
            paid_item = NumericItem("", paid)
            self.orders_table.setItem(row, self.COL_PAID, paid_item)

            # Üstüne edit edilebilir QDoubleSpinBox
            paid_spin = self._make_paid_spin(order.get("id"), paid, amt, row)
            self.orders_table.setCellWidget(row, self.COL_PAID, paid_spin)

            total_paid += paid

            # Kurye
            self.orders_table.setItem(
                row,
                self.COL_COURIER,
                QTableWidgetItem(courier.get("name") or "-"),
            )

            # Durum
            self.orders_table.setItem(
                row, self.COL_STATUS, QTableWidgetItem(self._status_label(order))
            )

        self.orders_table.blockSignals(False)
        self.orders_table.setSortingEnabled(True)
        self.orders_table.setUpdatesEnabled(True)

        # Toplam kutuları
        self.summary_count.setText(str(len(filtered)))
        self.summary_qty.setText(self._format_qty(total_qty))
        self.summary_total.setText(format_currency(total_amt))
        self.summary_paid.setText(format_currency(total_paid))

        # Sütun genişlikleri
        self.orders_table.resizeColumnsToContents()
        # Checkbox sütununu dar tut (resizeColumnsToContents sıfırlar)
        self.orders_table.horizontalHeader().setSectionResizeMode(
            self.COL_CHECK, QHeaderView.ResizeMode.Fixed
        )
        self.orders_table.setColumnWidth(self.COL_CHECK, 36)
        self.orders_table.horizontalHeader().setSectionResizeMode(
            self.COL_ADDRESS, QHeaderView.ResizeMode.Stretch
        )

        # Önceki seçimi geri yükle
        if _prev_selected_ids:
            self._syncing_selection = True
            model = self.orders_table.selectionModel()
            for row in range(self.orders_table.rowCount()):
                item = self.orders_table.item(row, self.COL_NUMBER)
                if item and item.data(Qt.ItemDataRole.UserRole) in _prev_selected_ids:
                    if model:
                        idx = self.orders_table.model().index(row, 0)
                        model.select(
                            idx,
                            model.SelectionFlag.Select | model.SelectionFlag.Rows,
                        )
                    wrapper = self.orders_table.cellWidget(row, self.COL_CHECK)
                    if wrapper:
                        cb = wrapper.findChild(QCheckBox)
                        if cb:
                            cb.setChecked(True)
            self._syncing_selection = False

        # Detay tablosunu temizle
        self.items_table.setRowCount(0)
        self.items_summary_qty.setText("0")
        self.items_summary_total.setText("₺0,00")
        self.order_notes_label.setText("Sipariş Açıklaması: -")

    def _apply_local_filters(
        self, orders: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Kurye filtresini istemci tarafında uygular."""
        filtered = orders
        if self._courier_filter == COURIER_FILTER_ATANMAMIS:
            filtered = [o for o in filtered if not o.get("courier_id")]
        elif self._courier_filter:
            filtered = [
                o for o in filtered if o.get("courier_id") == self._courier_filter
            ]
        return filtered

    @staticmethod
    def _format_qty(value: float) -> str:
        if abs(value - int(value)) < 0.001:
            return str(int(value))
        return f"{value:.3f}".rstrip("0").rstrip(".")

    # ==================================================================
    # Inline Ödenen düzenleme
    # ==================================================================
    def _make_paid_spin(
        self, order_id: str, paid: float, total: float, row: int
    ) -> QDoubleSpinBox:
        spin = _ClearOnZeroSpinBox()
        spin.setDecimals(2)
        spin.setMaximum(999_999.99)
        spin.setSingleStep(1.0)
        spin.setSuffix(" ₺")
        spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        spin.setValue(paid)
        # Edit edilmek için tıklamak yeter; klavye odaklanınca direkt düzenleme
        spin.setProperty("order_id", order_id)
        spin.setProperty("order_total", total)
        spin.setProperty("_last_saved", paid)  # çift tetikleme önleme
        # Görünüm: tam ödeme yeşil, kısmi sarı, ödenmemiş gri
        self._style_paid_spin(spin, paid, total)
        # editingFinished = focus kaybedince tetiklenir
        spin.editingFinished.connect(lambda s=spin: self._on_paid_edited(s))
        return spin

    @staticmethod
    def _style_paid_spin(spin: QDoubleSpinBox, paid: float, total: float) -> None:
        if paid <= 0.005:
            color = "#9E9E9E"  # gri (ödenmedi)
            bg = "transparent"
        elif paid + 0.005 >= total:
            color = "#A6E3A1"  # yeşil (tam ödeme)
            bg = "rgba(166,227,161,0.15)"
        else:
            color = "#FAB387"  # turuncu (kısmi)
            bg = "rgba(250,179,135,0.15)"
        spin.setStyleSheet(
            f"QDoubleSpinBox {{ color: {color}; background: {bg}; "
            f"font-weight: bold; padding: 2px 6px; border: 1px solid #45475A; "
            f"border-radius: 3px; }}"
        )

    def _on_paid_edited(self, spin: QDoubleSpinBox) -> None:
        order_id = spin.property("order_id")
        order_total = spin.property("order_total")
        if not order_id:
            return
        new_paid = float(spin.value())
        # Çift tetikleme önleme: değer değişmediyse DB'ye yazma
        last = spin.property("_last_saved")
        if last is not None and abs(float(last) - new_paid) < 0.005:
            return
        spin.setProperty("_last_saved", new_paid)

        # DB'ye yaz, payment_status otomatik türetilir
        try:
            orders_db.set_paid_amount(order_id, new_paid, order_total)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ödeme Kayıt Hatası", str(exc))
            return
        self._skip_next_refresh = True  # polling refresh'i atla

        # Lokal cache + sıralama item'ı güncelle
        for order in self._current_orders:
            if order.get("id") == order_id:
                order["paid_amount"] = new_paid
                if new_paid <= 0:
                    order["payment_status"] = "pending"
                elif new_paid + 0.005 >= float(order_total or 0):
                    order["payment_status"] = "paid"
                else:
                    order["payment_status"] = "partial"
                break

        # Spinbox stilini yenile
        self._style_paid_spin(spin, new_paid, float(order_total or 0))

        # Üstteki sıralama item'ını ve toplam kutularını güncelle
        self._refresh_paid_sort_value(order_id, new_paid)
        self._recalculate_summary()

    def _refresh_paid_sort_value(self, order_id: str, new_paid: float) -> None:
        """Sıralama için arka plandaki NumericItem'ın değerini günceller."""
        for row in range(self.orders_table.rowCount()):
            num_item = self.orders_table.item(row, self.COL_NUMBER)
            if not num_item:
                continue
            if num_item.data(Qt.ItemDataRole.UserRole) == order_id:
                paid_item = self.orders_table.item(row, self.COL_PAID)
                if isinstance(paid_item, NumericItem):
                    paid_item._value = new_paid  # noqa: SLF001
                break

    def _recalculate_summary(self) -> None:
        """Tablo altındaki toplam kutularını yeniden hesaplar (refresh yapmadan)."""
        total_qty = 0.0
        total_amt = 0.0
        total_paid = 0.0
        for order in self._current_orders:
            try:
                summary = orders_db.order_items_summary(order.get("id"))
                total_qty += summary.get("quantity", 0)
            except Exception:  # noqa: BLE001
                pass
            total_amt += float(order.get("total_amount") or 0)
            paid_val = order.get("paid_amount")
            if paid_val is None:
                paid_val = (
                    float(order.get("total_amount") or 0)
                    if order.get("payment_status") == "paid"
                    else 0
                )
            total_paid += float(paid_val)

        self.summary_count.setText(str(len(self._current_orders)))
        self.summary_qty.setText(self._format_qty(total_qty))
        self.summary_total.setText(format_currency(total_amt))
        self.summary_paid.setText(format_currency(total_paid))

    # ==================================================================
    # Inline Sipariş Tutarı düzenleme
    # ==================================================================
    def _make_amount_spin(
        self, order_id: str, amount: float, row: int
    ) -> QDoubleSpinBox:
        spin = _ClearOnZeroSpinBox()
        spin.setDecimals(2)
        spin.setMaximum(999_999.99)
        spin.setSingleStep(1.0)
        spin.setSuffix(" ₺")
        spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        spin.setValue(amount)
        spin.setProperty("order_id", order_id)
        spin.setProperty("_last_saved", amount)  # çift tetikleme önleme
        spin.setStyleSheet(
            "QDoubleSpinBox { font-weight: bold; padding: 2px 6px; "
            "border: 1px solid #45475A; border-radius: 3px; }"
        )
        spin.editingFinished.connect(lambda s=spin: self._on_amount_edited(s))
        return spin

    def _on_amount_edited(self, spin: QDoubleSpinBox) -> None:
        order_id = spin.property("order_id")
        if not order_id:
            return
        new_amount = float(spin.value())
        # Çift tetikleme önleme
        last = spin.property("_last_saved")
        if last is not None and abs(float(last) - new_amount) < 0.005:
            return
        spin.setProperty("_last_saved", new_amount)

        try:
            orders_db.update_order_payment(order_id, total_amount=new_amount)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Tutar Kayıt Hatası", str(exc))
            return
        self._skip_next_refresh = True  # polling refresh'i atla

        # Lokal cache güncelle
        for order in self._current_orders:
            if order.get("id") == order_id:
                order["total_amount"] = new_amount
                break

        # Aynı satırdaki Ödenen spinbox'ın order_total'ını da güncelle
        for row in range(self.orders_table.rowCount()):
            num_item = self.orders_table.item(row, self.COL_NUMBER)
            if not num_item:
                continue
            if num_item.data(Qt.ItemDataRole.UserRole) == order_id:
                amt_item = self.orders_table.item(row, self.COL_AMOUNT)
                if isinstance(amt_item, NumericItem):
                    amt_item._value = new_amount  # noqa: SLF001
                paid_spin = self.orders_table.cellWidget(row, self.COL_PAID)
                if isinstance(paid_spin, QDoubleSpinBox):
                    paid_spin.setProperty("order_total", new_amount)
                    self._style_paid_spin(
                        paid_spin, float(paid_spin.value()), new_amount
                    )
                break

        self._recalculate_summary()

    @staticmethod
    def _status_label(order: dict[str, Any]) -> str:
        status = order.get("status")
        if status == STATUS_DELIVERED:
            return "✓ Teslim Edildi"
        if order.get("courier_id"):
            return "🏍 Yolda"
        return "⏳ Yeni"

    # ==================================================================
    # Seçim ve detay tablosu
    # ==================================================================
    def _selected_order(self) -> dict[str, Any] | None:
        """En son seçili (current) tek sipariş."""
        row = self.orders_table.currentRow()
        if row < 0:
            return None
        item = self.orders_table.item(row, self.COL_NUMBER)
        if not item:
            return None
        order_id = item.data(Qt.ItemDataRole.UserRole)
        return next((o for o in self._current_orders if o.get("id") == order_id), None)

    def _selected_orders(self) -> list[dict[str, Any]]:
        """Tüm seçili siparişleri döndür (satır seçimi = checkbox seçimi, senkron)."""
        result: list[dict[str, Any]] = []
        selected_rows = {idx.row() for idx in self.orders_table.selectedIndexes()}

        for row in sorted(selected_rows):
            item = self.orders_table.item(row, self.COL_NUMBER)
            if not item:
                continue
            oid = item.data(Qt.ItemDataRole.UserRole)
            order = next((o for o in self._current_orders if o.get("id") == oid), None)
            if order:
                result.append(order)
        return result

    # ------------------------------------------------------------------
    # Checkbox ↔ satır seçimi senkronizasyonu
    # ------------------------------------------------------------------
    def _on_checkbox_toggled(self, row: int, checked: bool) -> None:
        """Checkbox tıklanınca ilgili satırın seçim durumunu güncelle."""
        if self._syncing_selection:
            return
        self._syncing_selection = True
        try:
            model = self.orders_table.selectionModel()
            if model:
                flag = model.SelectionFlag.Select if checked else model.SelectionFlag.Deselect
                flag |= model.SelectionFlag.Rows
                idx = self.orders_table.model().index(row, 0)
                model.select(idx, flag)
            # Focus tabloya ver — seçim rengi ancak focus varken görünür
            self.orders_table.setFocus()
        finally:
            self._syncing_selection = False

    def _table_mouse_press(self, event) -> None:
        """Checkbox sütunu dışına tıklayınca mevcut seçimi korur.

        Boş alana tıklama seçimi sıfırlamaz. Veri satırına normal tıklama
        tek-seçim yapar; Ctrl/Shift ile çoklu seçim korunur.
        """
        from PyQt6.QtWidgets import QAbstractItemView
        idx = self.orders_table.indexAt(event.pos())
        if not idx.isValid():
            # Boş alana tıklama — seçimi koru, hiçbir şey yapma
            return
        # Checkbox sütunu: normal QTableWidget davranışı (widget zaten handler'a sahip)
        if idx.column() == self.COL_CHECK:
            QTableWidget.mousePressEvent(self.orders_table, event)
            return
        # Diğer sütunlar: varsayılan davranış (Ctrl/Shift destekli satır seçimi)
        QTableWidget.mousePressEvent(self.orders_table, event)

    def _on_order_selected(self) -> None:
        """Satır seçimi değişince checkbox'ları senkronize et + detay göster."""
        if not self._syncing_selection:
            self._syncing_selection = True
            try:
                selected_rows = {idx.row() for idx in self.orders_table.selectedIndexes()}
                for row in range(self.orders_table.rowCount()):
                    wrapper = self.orders_table.cellWidget(row, self.COL_CHECK)
                    if wrapper:
                        cb = wrapper.findChild(QCheckBox)
                        if cb:
                            cb.setChecked(row in selected_rows)
            finally:
                self._syncing_selection = False

        orders = self._selected_orders()
        if not orders:
            self.items_table.setRowCount(0)
            self.order_notes_label.setText("Sipariş Açıklaması: -")
            return
        # Çoklu seçimde ilk seçiliyi göster
        self._populate_items_table(orders[0])

    def _populate_items_table(self, order: dict[str, Any]) -> None:
        try:
            items = orders_db.list_order_items(order.get("id"))
        except Exception:  # noqa: BLE001
            items = []

        self.items_table.setRowCount(0)
        total_qty = 0.0
        total_amt = 0.0
        for item in items:
            row = self.items_table.rowCount()
            self.items_table.insertRow(row)
            product = item.get("products") or {}

            self.items_table.setItem(
                row, 0, QTableWidgetItem("")
            )  # Kategori (henüz join yok)
            self.items_table.setItem(
                row, 1, QTableWidgetItem(product.get("name") or "-")
            )

            unit_price = float(item.get("unit_price") or 0)
            up_item = QTableWidgetItem(format_currency(unit_price))
            up_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.items_table.setItem(row, 2, up_item)

            qty = float(item.get("quantity") or 0)
            qty_item = QTableWidgetItem(
                f"{self._format_qty(qty)} {item.get('unit') or ''}"
            )
            qty_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.items_table.setItem(row, 3, qty_item)

            line_total = float(item.get("total_price") or 0)
            lt_item = QTableWidgetItem(format_currency(line_total))
            lt_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.items_table.setItem(row, 4, lt_item)

            total_qty += qty
            total_amt += line_total

        self.items_summary_qty.setText(self._format_qty(total_qty))
        self.items_summary_total.setText(format_currency(total_amt))

        notes = order.get("notes") or "-"
        self.order_notes_label.setText(f"Sipariş Açıklaması: {notes}")

    # ==================================================================
    # Aksiyonlar
    # ==================================================================
    def _on_order_double_click(self, _row: int, _col: int) -> None:
        self._edit_selected()

    def _edit_selected(self) -> None:
        order = self._selected_order()
        if not order:
            QMessageBox.information(self, "Seçim", "Önce bir sipariş seçin.")
            return
        self.open_order_requested.emit(order["id"])

    def _print_selected(self) -> None:
        order = self._selected_order()
        if not order:
            QMessageBox.information(self, "Seçim", "Önce bir sipariş seçin.")
            return
        self.print_order_requested.emit(order["id"])

    def _print_customer_receipt(self) -> None:
        """Seçili sipariş(ler)in müşteri fişini yazdır."""
        orders = self._selected_orders()
        if not orders:
            QMessageBox.information(self, "Seçim", "Önce sipariş seçin.")
            return
        order_ids = [o["id"] for o in orders]
        self.print_bulk_customer_requested.emit(order_ids)

    def _print_preparation_receipt(self) -> None:
        """Seçili sipariş(ler)in hazırlama fişini yazdır."""
        orders = self._selected_orders()
        if not orders:
            QMessageBox.information(self, "Seçim", "Önce sipariş seçin.")
            return
        order_ids = [o["id"] for o in orders]
        self.print_preparation_requested.emit(order_ids)

    def _delete_selected(self) -> None:
        orders = self._selected_orders()
        if not orders:
            return
        count = len(orders)
        if count == 1:
            text = (
                f"#{orders[0].get('order_number')} numaralı sipariş "
                "silinecek. Onaylıyor musun?"
            )
        else:
            text = f"{count} adet sipariş toplu olarak silinecek. Onaylıyor musun?"
        confirm = QMessageBox.question(self, "Sil", text)
        if confirm != QMessageBox.StandardButton.Yes:
            return
        errors: list[str] = []
        for order in orders:
            try:
                orders_db.delete_order(order["id"])
            except Exception as exc:  # noqa: BLE001
                errors.append(f"#{order.get('order_number')}: {exc}")
        self.refresh()
        if errors:
            QMessageBox.critical(self, "Silme Hatası", "\n".join(errors))

    def _mark_delivered(self) -> None:
        orders = self._selected_orders()
        if not orders:
            return
        errors: list[str] = []
        for order in orders:
            try:
                orders_db.mark_delivered(order["id"])
            except Exception as exc:  # noqa: BLE001
                errors.append(f"#{order.get('order_number')}: {exc}")
        self.refresh()
        if errors:
            QMessageBox.critical(self, "Hata", "\n".join(errors))

    def _assign_courier(self, order_id: str, courier_id: str | None) -> None:
        try:
            orders_db.assign_courier(order_id, courier_id)
            # Mevcut siparişin durumunu kontrol et (delivered ise dokunma)
            current = next(
                (o for o in self._current_orders if o.get("id") == order_id),
                {},
            )
            if current.get("status") != STATUS_DELIVERED:
                # Kurye atandıysa "yolda", kaldırıldıysa "yeni"
                from database.orders_db import STATUS_ON_WAY

                new_status = STATUS_ON_WAY if courier_id else STATUS_NEW
                orders_db.update_order_status(order_id, new_status)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _assign_couriers_bulk(self, courier_id: str | None) -> None:
        """Tüm seçili siparişlere aynı kuryeyi ata (veya kaldır)."""
        orders = self._selected_orders()
        if not orders:
            return
        errors: list[str] = []
        for order in orders:
            try:
                self._assign_courier(order["id"], courier_id)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"#{order.get('order_number')}: {exc}")
        self.refresh()
        if errors:
            QMessageBox.critical(self, "Kurye Atama Hatası", "\n".join(errors))

    # ==================================================================
    # Sağ tık menüsü
    # ==================================================================
    def _show_context_menu(self, pos) -> None:
        orders = self._selected_orders()
        if not orders:
            return
        order = orders[0]  # menü aksiyonları için ilk seçili referans

        menu = QMenu(self)

        edit_act = QAction("✏ Düzelt", self)
        edit_act.triggered.connect(self._edit_selected)
        menu.addAction(edit_act)

        # Müşteri Detayı (kayıtlı müşteri ise)
        cust_id = order.get("customer_id")
        if cust_id:
            cust_act = QAction("👤 Müşteri Detayını Aç", self)
            cust_act.triggered.connect(
                lambda _checked=False, cid=cust_id: self.open_customer_requested.emit(cid)
            )
            menu.addAction(cust_act)

        print_act = QAction("🖨 Sipariş Fişi", self)
        print_act.triggered.connect(self._print_customer_receipt)
        menu.addAction(print_act)

        prep_act = QAction("📋 Hazırlama Fişi", self)
        prep_act.triggered.connect(self._print_preparation_receipt)
        menu.addAction(prep_act)

        # Kurye alt menüsü (çoklu seçimde tümüne atanır)
        courier_menu = QMenu("🏍 Kuryeye Ata", self)
        try:
            couriers = couriers_db.list_couriers(only_active=True)
        except Exception:  # noqa: BLE001
            couriers = []

        none_act = QAction("(Atamayı Kaldır)", self)
        none_act.triggered.connect(lambda: self._assign_couriers_bulk(None))
        courier_menu.addAction(none_act)
        courier_menu.addSeparator()
        for cr in couriers:
            cr_id = cr.get("id")
            label = cr.get("name") or "-"
            if order.get("courier_id") == cr_id:
                label = f"• {label}"
            act = QAction(label, self)
            act.triggered.connect(
                lambda _checked=False, cid=cr_id: self._assign_couriers_bulk(cid)
            )
            courier_menu.addAction(act)
        menu.addMenu(courier_menu)

        # Teslim et / geri al (tüm seçili siparişlere)
        if order.get("status") != STATUS_DELIVERED:
            deliver_act = QAction("✓ Teslim Edildi olarak işaretle", self)
            deliver_act.triggered.connect(self._mark_delivered)
            menu.addAction(deliver_act)
        else:
            undeliver_act = QAction("↶ Geri Al (Yeni)", self)
            undeliver_act.triggered.connect(self._mark_undelivered)
            menu.addAction(undeliver_act)

        menu.addSeparator()
        delete_act = QAction("🗑 Sil", self)
        delete_act.triggered.connect(self._delete_selected)
        menu.addAction(delete_act)

        menu.exec(self.orders_table.viewport().mapToGlobal(pos))

    def _mark_undelivered(self) -> None:
        """Seçili sipariş(ler)i 'Yeni' olarak işaretle."""
        orders = self._selected_orders()
        if not orders:
            return
        errors: list[str] = []
        for order in orders:
            try:
                orders_db.update_order_status(order["id"], STATUS_NEW)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"#{order.get('order_number')}: {exc}")
        self.refresh()
        if errors:
            QMessageBox.critical(self, "Hata", "\n".join(errors))

    def _set_status(self, order_id: str, status: str) -> None:
        try:
            orders_db.update_order_status(order_id, status)
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))
