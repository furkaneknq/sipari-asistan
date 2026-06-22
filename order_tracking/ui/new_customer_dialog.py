"""Yeni müşteri ekleme diyaloğu (gelen aramadan veya manuel)."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from database import customers_db
from utils.helpers import format_phone, normalize_phone, parse_maps_link, to_uppercase_tr


class NewCustomerDialog(QDialog):
    """Yeni müşteri (ve isteğe bağlı varsayılan adres) ekler."""

    def __init__(self, parent=None, prefill_phone: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("Yeni Müşteri")
        self.setMinimumWidth(400)
        # WindowModal: popup gibi bağımsız top-level pencereleri bloklamasın
        self.setWindowModality(Qt.WindowModality.WindowModal)

        self.created_customer: dict[str, Any] | None = None

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ad Soyad")

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("0532 123 45 67")
        if prefill_phone:
            # Android'den gelen "+905321234567" ham formu yerine
            # okunabilir "0532 123 45 67" göster
            pretty = format_phone(prefill_phone) or prefill_phone
            self.phone_input.setText(pretty)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("opsiyonel")

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Not (opsiyonel)")
        self.notes_input.setMaximumHeight(60)

        self.address_input = QTextEdit()
        self.address_input.setPlaceholderText("Açık adres (opsiyonel)")
        self.address_input.setMaximumHeight(70)

        self.address_title_input = QLineEdit("Ev")

        self.is_default_checkbox = QCheckBox("Varsayılan adres olarak ayarla")
        self.is_default_checkbox.setChecked(True)

        # Konum linki
        self.location_link_input = QLineEdit()
        self.location_link_input.setPlaceholderText("Google Maps linki yapıştırın")

        form = QFormLayout()
        form.addRow("Ad Soyad *", self.name_input)
        form.addRow("Telefon *", self.phone_input)
        form.addRow("E-posta", self.email_input)
        form.addRow("Not", self.notes_input)
        form.addRow("Adres Başlığı", self.address_title_input)
        form.addRow("Adres", self.address_input)
        form.addRow("Konum Linki", self.location_link_input)
        form.addRow("", self.is_default_checkbox)

        save_btn = QPushButton("Kaydet")
        save_btn.setObjectName("SuccessButton")
        save_btn.clicked.connect(self._on_save)

        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.clicked.connect(self.reject)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(cancel_btn)
        button_row.addWidget(save_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(button_row)

        self.name_input.setFocus()

    # ------------------------------------------------------------------
    def _on_save(self) -> None:
        name = to_uppercase_tr(self.name_input.text().strip())
        phone_raw = self.phone_input.text().strip()
        email = self.email_input.text().strip() or None
        notes = to_uppercase_tr(self.notes_input.toPlainText().strip()) or None
        address_text = to_uppercase_tr(self.address_input.toPlainText().strip())
        address_title = to_uppercase_tr(self.address_title_input.text().strip()) or "EV"

        if not name or not phone_raw:
            QMessageBox.warning(self, "Eksik Bilgi", "Ad Soyad ve Telefon zorunludur.")
            return

        phone = normalize_phone(phone_raw)
        if not phone or len(phone) < 10:
            QMessageBox.warning(self, "Geçersiz Telefon", "Telefon en az 10 hane olmalıdır.")
            return

        existing = customers_db.get_customer_by_phone(phone)
        if existing and not existing.get("is_guest"):
            QMessageBox.warning(
                self,
                "Zaten Var",
                "Bu telefon numarası zaten kayıtlı:\n"
                f"{existing.get('name', '-')}",
            )
            return

        # Konum bilgilerini linkten çıkar
        location_link = self.location_link_input.text().strip()
        latitude, longitude = parse_maps_link(location_link)
        if location_link and latitude is None:
            QMessageBox.warning(
                self, "Geçersiz Konum Linki",
                "Girilen linkten konum bilgisi çıkarılamadı.\n"
                "Google Maps linki veya koordinat (örn: 39.9208,32.8541) yapıştırın."
            )
            return

        try:
            if existing and existing.get("is_guest"):
                # Misafir kayıt zaten varsa onu gerçek müşteriye yükselt
                # (UNIQUE phone constraint'ini patlatmadan).
                cust = customers_db.update_customer(
                    existing["id"],
                    {
                        "name": name,
                        "email": email,
                        "notes": notes,
                        "is_guest": False,
                    },
                )
            else:
                cust = customers_db.create_customer(name, phone, email, notes)
            cust_id = cust.get("id")
            if address_text and cust_id:
                customers_db.create_address(
                    cust_id,
                    address_text=address_text,
                    title=address_title,
                    latitude=latitude,
                    longitude=longitude,
                    is_default=self.is_default_checkbox.isChecked(),
                )
            self.created_customer = cust
            self.accept()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Kayıt Hatası", str(exc))

    # ------------------------------------------------------------------
    def keyPressEvent(self, event):  # noqa: N802 - Qt API
        if event.key() == Qt.Key.Key_Return and not self.notes_input.hasFocus() \
                and not self.address_input.hasFocus():
            self._on_save()
        else:
            super().keyPressEvent(event)
