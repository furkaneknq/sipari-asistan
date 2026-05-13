"""Sipariş oluşturma / düzenleme penceresi.

Mod 1: Yeni sipariş (order_id=None) → kayıt sonrası yazdır seçeneği
Mod 2: Mevcut sipariş düzenleme → kalemler, tutar, ödeme, durum güncellenebilir
"""

from __future__ import annotations

from datetime import date
from typing import Any

from PyQt6.QtCore import QDate, Qt, QTime
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from database import couriers_db, customers_db, orders_db, products_db
from database.orders_db import STATUS_NEW, STATUS_ON_WAY
from utils import quick_notes as quick_notes_store
from utils.helpers import fit_to_screen, format_currency


class OrderDetailDialog(QDialog):
    def __init__(
        self,
        parent=None,
        order_id: str | None = None,
        prefill_customer_id: str | None = None,
        guest_mode: bool = False,
        prefill_phone: str | None = None,
    ) -> None:
        super().__init__(parent)
        # WindowModal: sadece parent (MainWindow) bloklanır; bağımsız top-level
        # popup'lar (gelen arama bildirimi gibi) serbest kalır.
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.order_id = order_id
        self.prefill_customer_id = prefill_customer_id
        self._initial_guest_mode = guest_mode
        self._prefill_phone = prefill_phone
        self.is_edit = order_id is not None

        self.setWindowTitle("Sipariş Düzenle" if self.is_edit else "Yeni Sipariş")
        fit_to_screen(self, 1100, 780, min_w_ratio=0.55, min_h_ratio=0.6)

        # Çalışma içi durum
        self._customers: list[dict[str, Any]] = []
        self._addresses: list[dict[str, Any]] = []
        self._categories: list[dict[str, Any]] = []
        self._couriers: list[dict[str, Any]] = []
        self._items: list[dict[str, Any]] = []  # in-memory kalemler
        self._existing_order: dict[str, Any] | None = None

        self.print_after_save = False
        self.saved_order_id: str | None = None

        self._build_ui()
        self._load_data()

    # ==================================================================
    # UI
    # ==================================================================
    def _build_ui(self) -> None:
        # ---- Tek Seferlik Müşteri Toggle ----
        self.guest_check = QCheckBox(
            "📌 Tek Seferlik Müşteri (kalıcı kayıt yapma)"
        )
        self.guest_check.toggled.connect(self._on_guest_toggled)

        # ---- Kayıtlı Müşteri Alanları ----
        # Aranabilir müşteri kombosu (yazarak filtreleme)
        self.customer_combo = QComboBox()
        self.customer_combo.setMinimumWidth(380)
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.customer_combo.lineEdit().setPlaceholderText("Müşteri seçin (yazarak ara)")
        completer = QCompleter()
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.customer_combo.setCompleter(completer)
        self.customer_combo.currentIndexChanged.connect(self._on_customer_changed)

        self.phone_label = QLabel("-")
        self.phone_label.setObjectName("SettingsInfo")

        self.address_combo = QComboBox()
        self.address_combo.setMinimumWidth(280)

        new_addr_btn = QPushButton("+ Yeni Adres")
        new_addr_btn.setObjectName("SecondaryButton")
        new_addr_btn.clicked.connect(self._add_address)

        # ---- Tek Seferlik Müşteri Alanları ----
        self.guest_name_input = QLineEdit()
        self.guest_name_input.setPlaceholderText("Ad Soyad")
        self.guest_phone_input = QLineEdit()
        self.guest_phone_input.setPlaceholderText("0532 123 45 67 (opsiyonel)")
        self.guest_address_input = QLineEdit()
        self.guest_address_input.setPlaceholderText("Açık adres (opsiyonel)")

        self.order_date = QDateEdit()
        self.order_date.setDate(QDate.currentDate())
        self.order_date.setCalendarPopup(True)
        self.order_date.setDisplayFormat("dd.MM.yyyy")

        self.delivery_time = QTimeEdit()
        self.delivery_time.setTime(QTime.currentTime())
        self.delivery_time.setDisplayFormat("HH:mm")

        # Form satırlarını ayrı ayrı tutuyoruz ki gizleyip gösterebilelim
        top_form = QFormLayout()
        top_form.addRow("", self.guest_check)

        top_form.addRow("Müşteri *", self.customer_combo)
        top_form.addRow("Telefon", self.phone_label)

        addr_row = QHBoxLayout()
        addr_row.addWidget(self.address_combo, 1)
        addr_row.addWidget(new_addr_btn)
        self._addr_row_widget = QWidget()
        self._addr_row_widget.setLayout(addr_row)
        top_form.addRow("Adres", self._addr_row_widget)

        # Misafir alanları (varsayılan gizli)
        top_form.addRow("Misafir Adı *", self.guest_name_input)
        top_form.addRow("Misafir Tel.", self.guest_phone_input)
        top_form.addRow("Misafir Adres", self.guest_address_input)

        date_row = QHBoxLayout()
        date_row.addWidget(self.order_date)
        date_row.addSpacing(12)
        date_row.addWidget(QLabel("Saat:"))
        date_row.addWidget(self.delivery_time)
        date_row.addStretch()
        date_row_widget = QWidget()
        date_row_widget.setLayout(date_row)
        top_form.addRow("Tarih *", date_row_widget)

        # Misafir alanlarını başlangıçta gizle
        self._top_form = top_form
        self._set_guest_visible(False)

        # Sol panel: Ürün seçimi (kategori sekmeleri)
        self.product_tabs = QTabWidget()
        self.product_tabs.setMinimumHeight(280)

        # Sağ panel: Sepet
        self.items_table = QTableWidget(0, 6)
        self.items_table.setHorizontalHeaderLabels(
            ["Ürün", "Miktar", "Birim", "Fiyat", "Toplam", ""]
        )
        self.items_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.total_label = QLabel("TOPLAM: ₺0,00")
        self.total_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #2E7D32;")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        cart_layout = QVBoxLayout()
        cart_layout.addWidget(QLabel("Sepet"))
        cart_layout.addWidget(self.items_table)
        cart_layout.addWidget(self.total_label)

        cart_widget = QFrame()
        cart_widget.setLayout(cart_layout)

        items_split = QHBoxLayout()
        items_split.addWidget(self.product_tabs, 1)
        items_split.addWidget(cart_widget, 1)

        # Ödeme bloğu
        self.payment_cash = QRadioButton("Nakit")
        self.payment_card = QRadioButton("Kredi Kartı")
        self.payment_iban = QRadioButton("IBAN")
        self.payment_cash.setChecked(True)
        self.payment_group = QButtonGroup(self)
        self.payment_group.addButton(self.payment_cash, 0)
        self.payment_group.addButton(self.payment_card, 1)
        self.payment_group.addButton(self.payment_iban, 2)

        payment_row = QHBoxLayout()
        payment_row.addWidget(self.payment_cash)
        payment_row.addWidget(self.payment_card)
        payment_row.addWidget(self.payment_iban)
        payment_row.addStretch()

        self.payment_amount = QDoubleSpinBox()
        self.payment_amount.setDecimals(2)
        self.payment_amount.setMaximum(999_999.99)
        self.payment_amount.setSingleStep(1.0)
        self.payment_amount.setSuffix("  ₺")

        # Hızlı doldur: sepet toplamına eşitle
        self.paid_full_btn = QPushButton("= Sepet Toplamı")
        self.paid_full_btn.setObjectName("SecondaryButton")
        self.paid_full_btn.clicked.connect(self._fill_paid_with_total)

        paid_row = QHBoxLayout()
        paid_row.addWidget(self.payment_amount, 1)
        paid_row.addWidget(self.paid_full_btn)
        paid_row_widget = QWidget()
        paid_row_widget.setLayout(paid_row)

        self.courier_combo = QComboBox()

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(70)
        self.notes_input.setPlaceholderText("Sipariş notu (opsiyonel)")

        # Hızlı notlar: kayıtlı şablonlardan tek tıkla ekle + yeni şablon kaydet
        self.quick_notes_combo = QComboBox()
        self.quick_notes_combo.setMinimumWidth(180)
        self.quick_notes_combo.setToolTip("Hızlı notlar — seçince not alanına eklenir")
        self.quick_notes_combo.activated.connect(self._on_quick_note_selected)

        save_qn_btn = QPushButton("💾 Şablon Kaydet")
        save_qn_btn.setObjectName("SecondaryButton")
        save_qn_btn.setToolTip("Not alanındaki metni hızlı notlara kaydet")
        save_qn_btn.clicked.connect(self._save_current_as_quick_note)

        manage_qn_btn = QPushButton("⚙")
        manage_qn_btn.setObjectName("SecondaryButton")
        manage_qn_btn.setToolTip("Hızlı notları yönet (sil)")
        manage_qn_btn.setMaximumWidth(36)
        manage_qn_btn.clicked.connect(self._manage_quick_notes)

        quick_notes_row = QHBoxLayout()
        quick_notes_row.setContentsMargins(0, 0, 0, 0)
        quick_notes_row.addWidget(QLabel("Hızlı Notlar:"))
        quick_notes_row.addWidget(self.quick_notes_combo, 1)
        quick_notes_row.addWidget(save_qn_btn)
        quick_notes_row.addWidget(manage_qn_btn)
        quick_notes_row_widget = QWidget()
        quick_notes_row_widget.setLayout(quick_notes_row)

        self._reload_quick_notes()

        bottom_form = QFormLayout()
        payment_row_widget = QWidget()
        payment_row_widget.setLayout(payment_row)
        bottom_form.addRow("Ödeme Yöntemi", payment_row_widget)
        bottom_form.addRow("Ödenen Tutar", paid_row_widget)
        bottom_form.addRow("Kurye", self.courier_combo)
        bottom_form.addRow("", quick_notes_row_widget)
        bottom_form.addRow("Not", self.notes_input)

        # Butonlar
        self.save_btn = QPushButton("Kaydet")
        self.save_btn.setObjectName("SuccessButton")
        self.save_btn.clicked.connect(lambda: self._save(print_after=False))

        self.save_print_btn = QPushButton("Kaydet ve Yazdır")
        self.save_print_btn.clicked.connect(lambda: self._save(print_after=True))

        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(cancel_btn)
        button_row.addWidget(self.save_print_btn)
        button_row.addWidget(self.save_btn)

        # İçerik widget'ı (scroll için)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addLayout(top_form)
        content_layout.addLayout(items_split, 1)
        content_layout.addLayout(bottom_form)

        scroll = QScrollArea()
        scroll.setWidget(content_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(scroll, 1)
        layout.addLayout(button_row)

    # ==================================================================
    # Misafir (tek seferlik) modu
    # ==================================================================
    def _on_guest_toggled(self, checked: bool) -> None:
        # Düzenleme modunda guest toggle'a izin verme (var olan müşteri ile bağ var)
        if self.is_edit and checked:
            QMessageBox.information(
                self,
                "Bilgi",
                "Mevcut bir siparişi tek seferlik moda çeviremezsin. "
                "Yeni sipariş açarken kullan.",
            )
            self.guest_check.setChecked(False)
            return
        self._set_guest_visible(checked)

    def _set_guest_visible(self, guest_mode: bool) -> None:
        """Form satırlarını mod'a göre göster/gizle."""
        # Kayıtlı müşteri tarafı: müşteri combo, telefon etiketi, adres satırı
        for widget in (
            self.customer_combo,
            self.phone_label,
            self._addr_row_widget,
        ):
            label = self._top_form.labelForField(widget)
            widget.setVisible(not guest_mode)
            if label:
                label.setVisible(not guest_mode)

        # Misafir tarafı
        for widget in (
            self.guest_name_input,
            self.guest_phone_input,
            self.guest_address_input,
        ):
            label = self._top_form.labelForField(widget)
            widget.setVisible(guest_mode)
            if label:
                label.setVisible(guest_mode)

    # ==================================================================
    # Veri yükleme
    # ==================================================================
    def _load_data(self) -> None:
        try:
            # Edit modunda misafir müşteriler de listede olsun ki
            # daha önce 'tek seferlik müşteri' ile açılan siparişler düzenlenebilsin.
            self._customers = customers_db.list_customers(
                include_guests=self.is_edit
            )
            self._categories = products_db.list_categories()
            self._couriers = couriers_db.list_couriers()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Veri Hatası", str(exc))
            return

        self.customer_combo.clear()
        self.customer_combo.addItem("", None)
        from utils.helpers import normalize_phone as np
        for c in self._customers:
            phone = c.get("phone", "") or ""
            norm_phone = np(phone) or ""
            norm_phone_nospace = norm_phone.replace(" ", "")
            label = f"{c.get('name')}  ({phone}) {norm_phone_nospace}"
            self.customer_combo.addItem(label, c.get("id"))

        # Completer'a aynı listeyi ver
        completer = self.customer_combo.completer()
        if completer is not None:
            from PyQt6.QtCore import QStringListModel

            items = [
                self.customer_combo.itemText(i)
                for i in range(self.customer_combo.count())
            ]
            completer.setModel(QStringListModel(items))

        self.courier_combo.clear()
        self.courier_combo.addItem("-- Atanmadı --", None)
        for cr in self._couriers:
            self.courier_combo.addItem(cr.get("name", ""), cr.get("id"))

        self._build_product_tabs()

        if self.is_edit and self.order_id:
            self._load_existing_order()
        elif self.prefill_customer_id:
            idx = self.customer_combo.findData(self.prefill_customer_id)
            if idx >= 0:
                self.customer_combo.setCurrentIndex(idx)
        elif self._initial_guest_mode:
            # Misafir sipariş modu: checkbox'ı işaretle, telefon prefill yap
            self.guest_check.setChecked(True)
            if self._prefill_phone:
                from utils.helpers import format_phone
                pretty = format_phone(self._prefill_phone) or self._prefill_phone
                self.guest_phone_input.setText(pretty)

    def _build_product_tabs(self) -> None:
        self.product_tabs.clear()
        if not self._categories:
            empty = QLabel("Kategori yok. Önce ürün/kategori ekleyin.")
            self.product_tabs.addTab(empty, "Ürünler")
            return

        for cat in self._categories:
            cat_id = cat.get("id")
            tab_widget = self._make_product_grid(cat_id)
            self.product_tabs.addTab(tab_widget, cat.get("name", "Kategori"))

    def _make_product_grid(self, category_id: str) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(8)

        try:
            products = products_db.list_products(category_id=category_id)
        except Exception:  # noqa: BLE001
            products = []

        if not products:
            grid.addWidget(QLabel("Bu kategoride aktif ürün yok."), 0, 0)
        else:
            cols = 3
            for i, p in enumerate(products):
                btn = QPushButton(
                    f"{p.get('name')}\n{format_currency(p.get('price', 0))} / {p.get('unit', 'adet')}"
                )
                btn.setObjectName("SecondaryButton")
                btn.setMinimumHeight(60)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                btn.clicked.connect(lambda _, prod=p: self._add_product(prod))
                grid.addWidget(btn, i // cols, i % cols)

        grid.setRowStretch(grid.rowCount(), 1)
        scroll.setWidget(container)
        return scroll

    def _load_existing_order(self) -> None:
        order = orders_db.get_order(self.order_id)
        if not order:
            QMessageBox.warning(self, "Bulunamadı", "Sipariş bulunamadı.")
            self.reject()
            return
        self._existing_order = order

        # Müşteri — combo'da yoksa DB'den çekip ekle (misafir veya silinmiş kayıt için)
        cust_id = order.get("customer_id")
        idx = self.customer_combo.findData(cust_id)
        if idx < 0 and cust_id:
            try:
                missing = customers_db.get_customer(cust_id)
            except Exception:  # noqa: BLE001
                missing = None
            if missing:
                self._customers.insert(0, missing)
                label = f"{missing.get('name')}  ({missing.get('phone', '')})"
                self.customer_combo.insertItem(1, label, missing.get("id"))
                idx = 1
        if idx >= 0:
            self.customer_combo.setCurrentIndex(idx)

        # Adres müşteri seçildiğinde yüklendi, doğru olanı seç
        addr_idx = self.address_combo.findData(order.get("address_id"))
        if addr_idx >= 0:
            self.address_combo.setCurrentIndex(addr_idx)

        # Tarih / saat
        order_date_str = order.get("order_date")
        if order_date_str:
            self.order_date.setDate(QDate.fromString(order_date_str, "yyyy-MM-dd"))

        delivery_time = order.get("delivery_time")
        if delivery_time:
            try:
                self.delivery_time.setTime(QTime.fromString(delivery_time[:5], "HH:mm"))
            except Exception:  # noqa: BLE001
                pass

        # Ödeme
        method = order.get("payment_method") or "cash"
        if method == "credit_card":
            self.payment_card.setChecked(True)
        elif method == "iban":
            self.payment_iban.setChecked(True)
        else:
            self.payment_cash.setChecked(True)

        try:
            # Edit modunda: paid_amount'tan yükle (yoksa eski mantığa düş)
            if order.get("paid_amount") is not None:
                self.payment_amount.setValue(float(order.get("paid_amount") or 0))
            elif order.get("payment_status") == "paid":
                self.payment_amount.setValue(float(order.get("total_amount") or 0))
            else:
                self.payment_amount.setValue(0.0)
        except (TypeError, ValueError):
            self.payment_amount.setValue(0.0)

        cr_idx = self.courier_combo.findData(order.get("courier_id"))
        if cr_idx >= 0:
            self.courier_combo.setCurrentIndex(cr_idx)

        self.notes_input.setPlainText(order.get("notes") or "")

        # Sipariş kalemleri
        try:
            existing_items = orders_db.list_order_items(self.order_id)
        except Exception:  # noqa: BLE001
            existing_items = []
        for it in existing_items:
            product = it.get("products") or {}
            self._items.append(
                {
                    "product_id": it.get("product_id"),
                    "name": product.get("name", "-"),
                    "quantity": float(it.get("quantity") or 0),
                    "unit": it.get("unit") or product.get("unit") or "adet",
                    "unit_price": float(it.get("unit_price") or 0),
                    "notes": it.get("notes"),
                }
            )
        self._refresh_items_table()

    # ==================================================================
    # Olaylar
    # ==================================================================
    def _on_customer_changed(self) -> None:
        cust_id = self.customer_combo.currentData()
        self.address_combo.clear()
        self.address_combo.addItem("-- Adres seçin --", None)
        self._addresses = []
        if not cust_id:
            self.phone_label.setText("-")
            return

        cust = next((c for c in self._customers if c.get("id") == cust_id), None)
        if cust:
            self.phone_label.setText(cust.get("phone", "-"))

        try:
            addresses = customers_db.list_addresses(cust_id)
        except Exception:  # noqa: BLE001
            addresses = []
        self._addresses = addresses
        for addr in addresses:
            label = f"{addr.get('title', 'Adres')} - {addr.get('address_text', '')}"
            self.address_combo.addItem(label[:80], addr.get("id"))
            if addr.get("is_default"):
                self.address_combo.setCurrentIndex(self.address_combo.count() - 1)

    def _add_address(self) -> None:
        cust_id = self.customer_combo.currentData()
        if not cust_id:
            QMessageBox.warning(self, "Uyarı", "Önce bir müşteri seçin.")
            return
        text, ok = QInputDialog.getText(
            self, "Yeni Adres", "Açık adres:", QLineEdit.EchoMode.Normal, ""
        )
        if not ok or not text.strip():
            return
        title, ok2 = QInputDialog.getItem(
            self, "Adres Tipi", "Başlık:", ["Ev", "İş", "Diğer"], 0, True
        )
        if not ok2:
            return
        try:
            addr = customers_db.create_address(
                cust_id, address_text=text.strip(), title=title, is_default=False
            )
            self._on_customer_changed()
            new_idx = self.address_combo.findData(addr.get("id"))
            if new_idx >= 0:
                self.address_combo.setCurrentIndex(new_idx)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _add_product(self, product: dict[str, Any]) -> None:
        # Aynı ürün varsa miktarı arttır
        for it in self._items:
            if it.get("product_id") == product.get("id"):
                it["quantity"] += 1
                self._refresh_items_table()
                return

        self._items.append(
            {
                "product_id": product.get("id"),
                "name": product.get("name"),
                "quantity": 1,
                "unit": product.get("unit", "adet"),
                "unit_price": float(product.get("price") or 0),
                "notes": None,
            }
        )
        self._refresh_items_table()

    # ==================================================================
    # Sepet (items_table)
    # ==================================================================
    def _refresh_items_table(self) -> None:
        self.items_table.blockSignals(True)
        self.items_table.setRowCount(0)
        for idx, item in enumerate(self._items):
            self.items_table.insertRow(idx)
            self.items_table.setItem(idx, 0, QTableWidgetItem(item.get("name", "")))

            qty_spin = QDoubleSpinBox()
            qty_spin.setDecimals(3)
            qty_spin.setMaximum(99_999)
            qty_spin.setMinimum(0)
            qty_spin.setSingleStep(1)
            qty_spin.setValue(float(item.get("quantity", 0)))
            qty_spin.valueChanged.connect(
                lambda v, i=idx: self._update_item(i, "quantity", v)
            )
            self.items_table.setCellWidget(idx, 1, qty_spin)

            unit_edit = QLineEdit(item.get("unit") or "adet")
            unit_edit.editingFinished.connect(
                lambda i=idx, w=unit_edit: self._update_item(i, "unit", w.text())
            )
            self.items_table.setCellWidget(idx, 2, unit_edit)

            price_spin = QDoubleSpinBox()
            price_spin.setDecimals(2)
            price_spin.setMaximum(999_999)
            price_spin.setValue(float(item.get("unit_price", 0)))
            price_spin.valueChanged.connect(
                lambda v, i=idx: self._update_item(i, "unit_price", v)
            )
            self.items_table.setCellWidget(idx, 3, price_spin)

            total = float(item.get("quantity", 0)) * float(item.get("unit_price", 0))
            total_item = QTableWidgetItem(format_currency(total))
            total_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.items_table.setItem(idx, 4, total_item)

            del_btn = QPushButton("🗑")
            del_btn.setObjectName("DangerButton")
            del_btn.setMaximumWidth(40)
            del_btn.clicked.connect(lambda _, i=idx: self._remove_item(i))
            self.items_table.setCellWidget(idx, 5, del_btn)

        self.items_table.blockSignals(False)
        self._refresh_total()

    def _update_item(self, idx: int, key: str, value: Any) -> None:
        if 0 <= idx < len(self._items):
            self._items[idx][key] = value
            # toplam kolonu güncelle (tüm tabloyu yenilemeden)
            total = float(self._items[idx].get("quantity", 0)) * float(
                self._items[idx].get("unit_price", 0)
            )
            cell = self.items_table.item(idx, 4)
            if cell:
                cell.setText(format_currency(total))
            self._refresh_total()

    def _remove_item(self, idx: int) -> None:
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._refresh_items_table()

    def _refresh_total(self) -> None:
        total = sum(
            float(it.get("quantity", 0)) * float(it.get("unit_price", 0))
            for it in self._items
        )
        self._cart_total = total
        self.total_label.setText(f"TOPLAM: {format_currency(total)}")

    def _fill_paid_with_total(self) -> None:
        """'= Sepet Toplamı' butonu — ödenen tutarı sepet toplamına eşitler."""
        total = getattr(self, "_cart_total", 0.0)
        self.payment_amount.setValue(float(total))

    # ==================================================================
    # Hızlı Notlar
    # ==================================================================
    def _reload_quick_notes(self) -> None:
        """Kayıtlı hızlı notları combo'ya yükler."""
        self.quick_notes_combo.blockSignals(True)
        self.quick_notes_combo.clear()
        self.quick_notes_combo.addItem("— Hızlı not seç —", "")
        for note in quick_notes_store.load_notes():
            self.quick_notes_combo.addItem(note, note)
        self.quick_notes_combo.blockSignals(False)

    def _on_quick_note_selected(self, index: int) -> None:
        """Combo'dan not seçilince notes_input'a ekler (mevcut metne append)."""
        if index <= 0:
            return
        text = self.quick_notes_combo.itemData(index) or ""
        if not text:
            return
        current = self.notes_input.toPlainText().strip()
        if current:
            self.notes_input.setPlainText(f"{current}, {text}")
        else:
            self.notes_input.setPlainText(text)
        # Combo'yu başa al ki tekrar seçilebilsin
        self.quick_notes_combo.setCurrentIndex(0)

    def _save_current_as_quick_note(self) -> None:
        """Not alanındaki metni hızlı notlara şablon olarak ekler."""
        text = self.notes_input.toPlainText().strip()
        if not text:
            QMessageBox.information(
                self,
                "Boş Not",
                "Önce not alanına şablon olarak kaydetmek istediğiniz metni yazın.",
            )
            return
        quick_notes_store.add_note(text)
        self._reload_quick_notes()
        QMessageBox.information(
            self, "Kaydedildi", f"Şablona eklendi:\n«{text}»"
        )

    def _manage_quick_notes(self) -> None:
        """Hızlı notları yönet — seçili olanı silme."""
        notes = quick_notes_store.load_notes()
        if not notes:
            QMessageBox.information(self, "Boş", "Kayıtlı hızlı not yok.")
            return
        item, ok = QInputDialog.getItem(
            self,
            "Hızlı Notu Sil",
            "Silinecek notu seçin:",
            notes,
            0,
            False,
        )
        if not ok or not item:
            return
        confirm = QMessageBox.question(
            self, "Sil", f"«{item}» silinsin mi?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        quick_notes_store.remove_note(item)
        self._reload_quick_notes()

    # ==================================================================
    # Kaydetme
    # ==================================================================
    def _save(self, print_after: bool = False) -> None:
        if not self._items:
            QMessageBox.warning(self, "Uyarı", "Sepet boş. Ürün ekleyin.")
            return

        is_guest = self.guest_check.isChecked() and not self.is_edit

        cust_id: str | None = None
        addr_id: str | None = None

        if is_guest:
            # Tek seferlik müşteri modu
            from utils.helpers import normalize_phone

            guest_name = self.guest_name_input.text().strip()
            guest_phone_raw = self.guest_phone_input.text().strip()
            guest_address = self.guest_address_input.text().strip()
            if not guest_name:
                QMessageBox.warning(self, "Uyarı", "Tek seferlik müşteri adı zorunlu.")
                return

            phone_norm = normalize_phone(guest_phone_raw)
            existing = None
            if phone_norm:
                # Aynı telefonla kayıt var mı? (UNIQUE constraint çakışmasını önle)
                try:
                    existing = customers_db.get_customer_by_phone(phone_norm)
                except Exception:  # noqa: BLE001
                    existing = None
            else:
                # Boş telefon → her seferinde benzersiz placeholder
                from datetime import datetime

                phone_norm = f"GUEST{int(datetime.now().timestamp() * 1000)}"

            try:
                if existing and existing.get("id"):
                    # Telefon zaten kayıtlı → mevcut müşteriyi kullan.
                    # is_guest fark etmiyor; sipariş o kişiye yazılır.
                    cust_id = existing["id"]
                else:
                    guest_cust = customers_db.create_customer(
                        name=guest_name,
                        phone=phone_norm,
                        notes="Tek seferlik müşteri (UI)",
                        is_guest=True,
                    )
                    cust_id = guest_cust.get("id")

                if cust_id and guest_address:
                    addr = customers_db.create_address(
                        cust_id,
                        address_text=guest_address,
                        title="Tek Seferlik",
                        is_default=False,
                    )
                    addr_id = addr.get("id")
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(
                    self,
                    "Müşteri Kayıt Hatası",
                    f"Tek seferlik müşteri kaydı yapılamadı.\n\n{exc}",
                )
                return
        else:
            cust_id = self.customer_combo.currentData()
            if not cust_id:
                QMessageBox.warning(self, "Uyarı", "Müşteri seçilmedi.")
                return
            addr_id = self.address_combo.currentData()

        order_d = self.order_date.date().toPyDate()
        delivery_t = self.delivery_time.time().toString("HH:mm")

        method = "cash"
        if self.payment_card.isChecked():
            method = "credit_card"
        elif self.payment_iban.isChecked():
            method = "iban"

        courier_id = self.courier_combo.currentData()
        notes = self.notes_input.toPlainText().strip() or None
        paid_amount = float(self.payment_amount.value())
        cart_total = float(getattr(self, "_cart_total", 0.0))

        # Kurye atandıysa durum otomatik "yolda", yoksa "yeni"
        # (Mevcut sipariş zaten "delivered" ise, dokunmuyoruz)
        existing_status = (
            (self._existing_order or {}).get("status") if self.is_edit else None
        )
        if existing_status == "delivered":
            new_status = "delivered"
        elif courier_id:
            new_status = STATUS_ON_WAY
        else:
            new_status = STATUS_NEW

        try:
            if self.is_edit and self.order_id:
                # Mevcut siparişi güncelle: kalemler + meta
                orders_db.replace_order_items(self.order_id, self._items)
                # Önce ödeme yöntemini güncelle (total DB trigger'ı tarafından yenilenir)
                orders_db.update_order_payment(
                    self.order_id,
                    payment_method=method,
                )
                # Sonra paid_amount + payment_status'ı tek seferde ayarla
                orders_db.set_paid_amount(self.order_id, paid_amount, cart_total)
                orders_db.update_order_status(self.order_id, new_status)
                orders_db.assign_courier(self.order_id, courier_id)
                # tarih/saat/notlar (orders_db kapsamı dışındaki alanlar)
                from database.supabase_client import get_client

                get_client().table("orders").update(
                    {
                        "address_id": addr_id,
                        "order_date": order_d.isoformat(),
                        "delivery_time": delivery_t,
                        "notes": notes,
                    }
                ).eq("id", self.order_id).execute()
                self.saved_order_id = self.order_id
            else:
                # Yeni sipariş — total DB trigger ile otomatik hesaplanır
                # paid_amount'tan payment_status'ı türet
                if paid_amount <= 0:
                    initial_status = "pending"
                elif paid_amount + 0.005 >= cart_total:
                    initial_status = "paid"
                else:
                    initial_status = "partial"
                created = orders_db.create_order(
                    customer_id=cust_id,
                    address_id=addr_id,
                    items=self._items,
                    payment_method=method,
                    payment_status=initial_status,
                    notes=notes,
                    courier_id=courier_id,
                    order_date=order_d,
                    delivery_time=delivery_t,
                    status=new_status,
                )
                new_id = created.get("id")
                # paid_amount'ı ayrıca yaz (create_order parametresi yok)
                if new_id and paid_amount > 0:
                    orders_db.set_paid_amount(new_id, paid_amount, cart_total)
                self.saved_order_id = new_id
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Kayıt Hatası", str(exc))
            return

        self.print_after_save = print_after
        self.accept()
