"""Müşteri detay penceresi: müşteri bilgisi + adresler + sipariş geçmişi."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from database import customers_db, orders_db
from database.orders_db import STATUS_LABELS
from utils.helpers import fit_to_screen, format_currency, format_phone, parse_maps_link, short_date


class CustomerDetailDialog(QDialog):
    def __init__(self, customer_id: str, parent=None) -> None:
        super().__init__(parent)
        # WindowModal: popup gibi bağımsız top-level pencereleri bloklamasın
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.customer_id = customer_id
        self.setWindowTitle("Müşteri Detayı")
        fit_to_screen(self, 900, 640, min_w_ratio=0.5, min_h_ratio=0.5)

        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        # Sol: bilgi formu
        self.name_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.email_input = QLineEdit()
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)

        info_form = QFormLayout()
        info_form.addRow("Ad Soyad", self.name_input)
        info_form.addRow("Telefon", self.phone_input)
        info_form.addRow("E-posta", self.email_input)
        info_form.addRow("Not", self.notes_input)

        save_btn = QPushButton("Bilgileri Kaydet")
        save_btn.setObjectName("SuccessButton")
        save_btn.clicked.connect(self._save_info)

        info_box = QVBoxLayout()
        info_box.addLayout(info_form)
        info_box.addWidget(save_btn)
        info_box.addStretch()

        info_widget = QFrame()
        info_widget.setLayout(info_box)

        # Adres tablosu
        self.address_table = QTableWidget(0, 4)
        self.address_table.setHorizontalHeaderLabels(
            ["Başlık", "Adres", "Konum", "Varsayılan"]
        )
        self.address_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.address_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.address_table.cellDoubleClicked.connect(self._on_address_double_click)

        add_addr_btn = QPushButton("+ Yeni Adres")
        add_addr_btn.clicked.connect(self._add_address)

        edit_addr_btn = QPushButton("✏ Adres Düzenle")
        edit_addr_btn.clicked.connect(self._edit_address)

        edit_loc_btn = QPushButton("📍 Konum Düzenle")
        edit_loc_btn.clicked.connect(self._edit_location)

        del_addr_btn = QPushButton("Adresi Sil")
        del_addr_btn.setObjectName("DangerButton")
        del_addr_btn.clicked.connect(self._delete_address)

        addr_btn_row = QHBoxLayout()
        addr_btn_row.addWidget(add_addr_btn)
        addr_btn_row.addWidget(edit_addr_btn)
        addr_btn_row.addWidget(edit_loc_btn)
        addr_btn_row.addWidget(del_addr_btn)
        addr_btn_row.addStretch()

        addr_layout = QVBoxLayout()
        addr_layout.addWidget(QLabel("Adresler"))
        addr_layout.addWidget(self.address_table)
        addr_layout.addLayout(addr_btn_row)

        addr_widget = QFrame()
        addr_widget.setLayout(addr_layout)

        # Sipariş geçmişi tablosu
        self.orders_table = QTableWidget(0, 7)
        self.orders_table.setHorizontalHeaderLabels(
            ["Sipariş", "Tarih", "Saat", "Adres", "Tutar", "Durum", "Ödeme"]
        )
        self.orders_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.orders_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.orders_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.orders_table.setAlternatingRowColors(True)
        self.orders_table.verticalHeader().setVisible(False)
        self.orders_table.doubleClicked.connect(lambda _: self._edit_order())

        edit_order_btn = QPushButton("✏️ Düzenle")
        edit_order_btn.setToolTip("Seçili siparişi düzenle")
        edit_order_btn.clicked.connect(self._edit_order)
        del_order_btn = QPushButton("🗑 Sil")
        del_order_btn.setToolTip("Seçili siparişi sil")
        del_order_btn.setStyleSheet("color: #D32F2F;")
        del_order_btn.clicked.connect(self._delete_order)

        order_btn_row = QHBoxLayout()
        order_btn_row.addStretch()
        order_btn_row.addWidget(edit_order_btn)
        order_btn_row.addWidget(del_order_btn)

        orders_layout = QVBoxLayout()
        orders_layout.addWidget(QLabel("Geçmiş Siparişler"))
        orders_layout.addWidget(self.orders_table)
        orders_layout.addLayout(order_btn_row)

        orders_widget = QFrame()
        orders_widget.setLayout(orders_layout)

        # Layout
        right_split = QSplitter(Qt.Orientation.Vertical)
        right_split.addWidget(addr_widget)
        right_split.addWidget(orders_widget)
        right_split.setStretchFactor(0, 1)
        right_split.setStretchFactor(1, 2)

        main_split = QSplitter(Qt.Orientation.Horizontal)
        main_split.addWidget(info_widget)
        main_split.addWidget(right_split)
        main_split.setStretchFactor(0, 1)
        main_split.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.addWidget(main_split)

    # ------------------------------------------------------------------
    def _load(self) -> None:
        cust = customers_db.get_customer(self.customer_id)
        if not cust:
            QMessageBox.warning(self, "Bulunamadı", "Müşteri bulunamadı.")
            self.reject()
            return
        self.name_input.setText(cust.get("name") or "")
        self.phone_input.setText(format_phone(cust.get("phone") or ""))
        self.email_input.setText(cust.get("email") or "")
        self.notes_input.setPlainText(cust.get("notes") or "")
        self._reload_addresses()
        self._reload_orders()

    def _reload_addresses(self) -> None:
        addresses = customers_db.list_addresses(self.customer_id)
        self.address_table.setRowCount(0)
        for addr in addresses:
            row = self.address_table.rowCount()
            self.address_table.insertRow(row)
            self.address_table.setItem(row, 0, QTableWidgetItem(addr.get("title") or ""))
            self.address_table.setItem(row, 1, QTableWidgetItem(addr.get("address_text") or ""))
            lat, lng = addr.get("latitude"), addr.get("longitude")
            loc = f"{lat:.5f}, {lng:.5f}" if lat and lng else "⚠ Konum bulunamadı"
            self.address_table.setItem(row, 2, QTableWidgetItem(loc))
            self.address_table.setItem(
                row, 3, QTableWidgetItem("✓" if addr.get("is_default") else "")
            )
            for col in range(4):
                self.address_table.item(row, col).setData(
                    Qt.ItemDataRole.UserRole, addr.get("id")
                )

    def _reload_orders(self) -> None:
        orders = orders_db.list_orders_by_customer(self.customer_id, limit=50)
        self.orders_table.setRowCount(0)
        for order in orders:
            row = self.orders_table.rowCount()
            self.orders_table.insertRow(row)

            # Sipariş numarası (order_id gizli)
            num_item = QTableWidgetItem(f"#{order.get('order_number')}")
            num_item.setData(Qt.ItemDataRole.UserRole, order.get("id"))
            self.orders_table.setItem(row, 0, num_item)

            # Tarih
            od = order.get("order_date") or ""
            if od:
                try:
                    from datetime import datetime as _dt
                    d = _dt.strptime(od, "%Y-%m-%d")
                    od = d.strftime("%d.%m.%Y")
                except Exception:  # noqa: BLE001
                    pass
            self.orders_table.setItem(row, 1, QTableWidgetItem(od))

            # Saat
            dt = order.get("delivery_time") or ""
            self.orders_table.setItem(
                row, 2, QTableWidgetItem(dt[:5] if dt else "-")
            )

            # Adres
            addr = (order.get("customer_addresses") or {}).get("address_text") or "-"
            addr_item = QTableWidgetItem(addr[:50])
            addr_item.setToolTip(addr)
            self.orders_table.setItem(row, 3, addr_item)

            # Tutar
            self.orders_table.setItem(
                row, 4, QTableWidgetItem(format_currency(order.get("total_amount")))
            )

            # Durum
            self.orders_table.setItem(
                row, 5,
                QTableWidgetItem(STATUS_LABELS.get(order.get("status"), order.get("status", ""))),
            )

            # Ödeme
            payment_status = order.get("payment_status") or ""
            payment = {
                "pending": "Beklemede",
                "paid": "Ödendi",
                "partial": "Kısmi",
            }.get(payment_status, payment_status)
            self.orders_table.setItem(row, 6, QTableWidgetItem(payment))

        self.orders_table.resizeColumnsToContents()
        self.orders_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )

    # ------------------------------------------------------------------
    def _save_info(self) -> None:
        from utils.helpers import normalize_phone

        name = self.name_input.text().strip()
        phone = normalize_phone(self.phone_input.text())
        email = self.email_input.text().strip() or None
        notes = self.notes_input.toPlainText().strip() or None
        if not name or not phone:
            QMessageBox.warning(self, "Eksik Bilgi", "İsim ve telefon zorunlu.")
            return
        try:
            customers_db.update_customer(
                self.customer_id,
                {"name": name, "phone": phone, "email": email, "notes": notes},
            )
            QMessageBox.information(self, "Kaydedildi", "Müşteri bilgileri güncellendi.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _add_address(self) -> None:
        text, ok = QInputDialog.getText(
            self, "Yeni Adres", "Açık adres:", QLineEdit.EchoMode.Normal, ""
        )
        if not ok or not text.strip():
            return
        title, ok2 = QInputDialog.getItem(
            self,
            "Adres Tipi",
            "Başlık:",
            ["Ev", "İş", "Diğer"],
            0,
            True,
        )
        if not ok2:
            return

        # Konum bilgisi
        latitude, longitude = self._ask_location()

        is_default_msg = QMessageBox.question(
            self,
            "Varsayılan",
            "Bu adresi varsayılan yapayım mı?",
        )
        is_default = is_default_msg == QMessageBox.StandardButton.Yes
        try:
            customers_db.create_address(
                self.customer_id,
                address_text=text.strip(),
                title=title,
                latitude=latitude,
                longitude=longitude,
                is_default=is_default,
            )
            self._reload_addresses()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _ask_location(self) -> tuple[float | None, float | None]:
        """Kullanıcıdan Google Maps linki ister, koordinat çıkarır."""
        link, ok = QInputDialog.getText(
            self, "Konum Linki",
            "Google Maps linki yapıştırın (boş bırakabilirsiniz):",
            QLineEdit.EchoMode.Normal, ""
        )
        if not ok or not link.strip():
            return None, None
        lat, lng = parse_maps_link(link)
        if lat is None:
            QMessageBox.warning(
                self, "Geçersiz Link",
                "Linkten konum çıkarılamadı.\n"
                "Google Maps linki veya koordinat (örn: 39.9208,32.8541) yapıştırın."
            )
            return None, None
        return lat, lng

    def _edit_location(self) -> None:
        """Seçili adresin konumunu Google Maps linki ile düzenle."""
        row = self.address_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Seçim", "Lütfen bir adres satırı seçin.")
            return
        item = self.address_table.item(row, 0)
        if not item:
            return
        addr_id = item.data(Qt.ItemDataRole.UserRole)
        if not addr_id:
            return

        link, ok = QInputDialog.getText(
            self, "Konum Düzenle",
            "Google Maps linki yapıştırın:\n"
            "(Boş bırakıp Tamam'a basırsanız konum silinir)",
            QLineEdit.EchoMode.Normal, ""
        )
        if not ok:
            return

        latitude, longitude = None, None
        if link.strip():
            latitude, longitude = parse_maps_link(link)
            if latitude is None:
                QMessageBox.warning(
                    self, "Geçersiz Link",
                    "Linkten konum çıkarılamadı.\n"
                    "Google Maps linki veya koordinat (örn: 39.9208,32.8541) yapıştırın."
                )
                return

        try:
            customers_db.update_address(addr_id, {
                "latitude": latitude,
                "longitude": longitude,
            })
            self._reload_addresses()
            QMessageBox.information(self, "Kaydedildi", "Konum güncellendi.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _delete_address(self) -> None:
        row = self.address_table.currentRow()
        if row < 0:
            return
        item = self.address_table.item(row, 0)
        if not item:
            return
        addr_id = item.data(Qt.ItemDataRole.UserRole)
        if not addr_id:
            return
        confirm = QMessageBox.question(
            self, "Sil", "Bu adres silinecek. Onaylıyor musun?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            customers_db.delete_address(addr_id)
            self._reload_addresses()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _on_address_double_click(self, row: int, col: int) -> None:
        """Adres satırı çift tıklandığında düzenleme dialog'u aç."""
        if row < 0:
            return
        self._edit_address()

    def _edit_address(self) -> None:
        """Seçili adresin metnini düzenle."""
        row = self.address_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Seçim", "Lütfen bir adres satırı seçin.")
            return
        item = self.address_table.item(row, 0)
        if not item:
            return
        addr_id = item.data(Qt.ItemDataRole.UserRole)
        if not addr_id:
            return

        current_title = self.address_table.item(row, 0).text() if self.address_table.item(row, 0) else ""
        current_address = self.address_table.item(row, 1).text() if self.address_table.item(row, 1) else ""

        title, ok1 = QInputDialog.getItem(
            self,
            "Adres Başlığı",
            "Başlık:",
            ["Ev", "İş", "Diğer"],
            ["Ev", "İş", "Diğer"].index(current_title) if current_title in ["Ev", "İş", "Diğer"] else 0,
            True,
        )
        if not ok1:
            return

        address, ok2 = QInputDialog.getText(
            self,
            "Adres Metni",
            "Açık adres:",
            QLineEdit.EchoMode.Normal,
            current_address,
        )
        if not ok2 or not address.strip():
            return

        try:
            customers_db.update_address(addr_id, {
                "title": title.strip(),
                "address_text": address.strip(),
            })
            self._reload_addresses()
            QMessageBox.information(self, "Kaydedildi", "Adres güncellendi.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    # ------------------------------------------------------------------
    # Sipariş düzenle / sil
    # ------------------------------------------------------------------
    def _selected_order_id(self) -> str | None:
        row = self.orders_table.currentRow()
        if row < 0:
            return None
        item = self.orders_table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _edit_order(self) -> None:
        oid = self._selected_order_id()
        if not oid:
            return
        mw = self.window()
        if mw and hasattr(mw, "_open_order"):
            self.close()
            mw._open_order(oid)

    def _delete_order(self) -> None:
        oid = self._selected_order_id()
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
        self._reload_orders()
