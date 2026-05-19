"""Ayarlar paneli: işletme bilgisi, tema, yazıcı, telefonlar, veritabanı testi."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database.supabase_client import get_client, test_connection
from ui import themes
import config


# Settings tablosundaki anahtarlar (key -> label)
SETTING_KEYS = [
    ("company_name", "İşletme Adı"),
    ("company_phone", "Telefon"),
    ("company_address", "Adres"),
    ("company_iban", "IBAN"),
    ("printer_name", "Yazıcı Adı"),
    ("printer_paper_size", "Kağıt Boyutu"),
    ("active_theme", "Aktif Tema"),
]


class SettingsPanel(QWidget):
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._inputs: dict[str, QLineEdit] = {}
        self._build_ui()
        self._load_settings()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(10)

        # 1) Genel ayarlar
        general_box = QGroupBox("📌 Genel Ayarlar")
        general_form = QFormLayout()
        for key, label in [
            ("company_name", "İşletme Adı"),
            ("company_phone", "Telefon"),
            ("company_address", "Adres"),
            ("company_iban", "IBAN"),
        ]:
            inp = QLineEdit()
            self._inputs[key] = inp
            general_form.addRow(label, inp)
        save_general = QPushButton("Kaydet")
        save_general.setObjectName("SuccessButton")
        save_general.clicked.connect(self._save_general)
        general_form.addRow("", save_general)
        general_box.setLayout(general_form)
        main_layout.addWidget(general_box)

        # 2) Tema
        theme_box = QGroupBox("🎨 Tema")
        self.theme_combo = QComboBox()
        for name in themes.list_theme_names():
            self.theme_combo.addItem(themes.theme_label(name), name)
        self.theme_combo.currentIndexChanged.connect(self._apply_theme)
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Tema:"))
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        theme_box.setLayout(theme_layout)
        main_layout.addWidget(theme_box)

        # 3) Yazıcı
        printer_box = QGroupBox("🖨️ Yazıcı")
        printer_form = QFormLayout()
        self.printer_type_label = QLabel(config.PRINTER_TYPE)
        self.printer_paper_label = QLabel(f"{config.PRINTER_PAPER_WIDTH}mm")
        printer_form.addRow("Tip", self.printer_type_label)
        printer_form.addRow("Kağıt Genişliği", self.printer_paper_label)
        info = QLabel(
            "Not: Yazıcı bilgisi .env dosyasından okunur. "
            "Değiştirmek için PRINTER_TYPE, PRINTER_PAPER_WIDTH, "
            "PRINTER_USB_VENDOR_ID, PRINTER_USB_PRODUCT_ID değerlerini "
            "düzenleyip uygulamayı yeniden başlatın."
        )
        info.setWordWrap(True)
        info.setObjectName("SettingsInfo")

        test_print_btn = QPushButton("Test Yazdır")
        test_print_btn.clicked.connect(self._test_print)
        printer_form.addRow("", info)
        printer_form.addRow("", test_print_btn)
        printer_box.setLayout(printer_form)
        main_layout.addWidget(printer_box)

        # 4) Bağlı telefonlar
        phones_box = QGroupBox("📱 Bağlı Telefonlar")
        self.phones_table = QTableWidget(0, 4)
        self.phones_table.setHorizontalHeaderLabels(
            ["Cihaz Adı", "Cihaz Kimliği", "Aktif", "Son Görülme"]
        )
        self.phones_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.phones_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        refresh_phones_btn = QPushButton("🔄 Yenile")
        refresh_phones_btn.setObjectName("SecondaryButton")
        refresh_phones_btn.clicked.connect(self._reload_phones)
        phones_layout = QVBoxLayout()
        phones_layout.addWidget(self.phones_table)
        phones_layout.addWidget(refresh_phones_btn)
        phones_box.setLayout(phones_layout)
        main_layout.addWidget(phones_box)

        # 5) Veritabanı
        db_box = QGroupBox("💾 Veritabanı")
        db_layout = QFormLayout()
        self.url_label = QLabel(config.SUPABASE_URL or "(yapılandırılmadı)")
        self.url_label.setWordWrap(True)
        self.key_label = QLabel(
            ("**** **** " + config.SUPABASE_KEY[-6:]) if config.SUPABASE_KEY else "(yapılandırılmadı)"
        )
        db_layout.addRow("URL", self.url_label)
        db_layout.addRow("Key", self.key_label)
        test_db_btn = QPushButton("Bağlantıyı Test Et")
        test_db_btn.clicked.connect(self._test_db)
        db_layout.addRow("", test_db_btn)
        db_box.setLayout(db_layout)
        main_layout.addWidget(db_box)

        main_layout.addStretch()

        scroll_area.setWidget(content_widget)
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll_area)

    # ------------------------------------------------------------------
    def _load_settings(self) -> None:
        try:
            res = get_client().table("settings").select("*").execute()
            rows = res.data or []
        except Exception:  # noqa: BLE001
            rows = []
        kv = {r["key"]: r.get("value") for r in rows}

        for key, inp in self._inputs.items():
            inp.setText(kv.get(key) or "")

        active_theme = kv.get("active_theme") or "light"
        idx = self.theme_combo.findData(active_theme)
        if idx >= 0:
            self.theme_combo.blockSignals(True)
            self.theme_combo.setCurrentIndex(idx)
            self.theme_combo.blockSignals(False)

        self._reload_phones()

    def _save_general(self) -> None:
        try:
            client = get_client()
            for key, inp in self._inputs.items():
                value = inp.text().strip()
                # upsert: var ise güncelle, yoksa ekle
                existing = (
                    client.table("settings").select("id").eq("key", key).limit(1).execute()
                )
                if existing.data:
                    client.table("settings").update({"value": value}).eq(
                        "key", key
                    ).execute()
                else:
                    client.table("settings").insert(
                        {"key": key, "value": value, "description": key}
                    ).execute()
            QMessageBox.information(self, "Kaydedildi", "Ayarlar kaydedildi.")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Hata", str(exc))

    def _apply_theme(self) -> None:
        theme_name = self.theme_combo.currentData()
        if not theme_name:
            return
        try:
            client = get_client()
            existing = (
                client.table("settings")
                .select("id")
                .eq("key", "active_theme")
                .limit(1)
                .execute()
            )
            if existing.data:
                client.table("settings").update({"value": theme_name}).eq(
                    "key", "active_theme"
                ).execute()
            else:
                client.table("settings").insert(
                    {"key": "active_theme", "value": theme_name}
                ).execute()
        except Exception:  # noqa: BLE001
            pass
        self.theme_changed.emit(theme_name)

    def _reload_phones(self) -> None:
        try:
            res = get_client().table("phones").select("*").order("device_name").execute()
            phones = res.data or []
        except Exception:  # noqa: BLE001
            phones = []
        self.phones_table.setRowCount(0)
        for p in phones:
            row = self.phones_table.rowCount()
            self.phones_table.insertRow(row)
            self.phones_table.setItem(row, 0, QTableWidgetItem(p.get("device_name") or ""))
            self.phones_table.setItem(row, 1, QTableWidgetItem(p.get("device_id") or ""))
            self.phones_table.setItem(
                row, 2, QTableWidgetItem("🟢 Aktif" if p.get("is_active") else "🔴 Pasif")
            )
            self.phones_table.setItem(row, 3, QTableWidgetItem(p.get("last_seen") or ""))

    def _test_db(self) -> None:
        ok, msg = test_connection()
        if ok:
            QMessageBox.information(self, "Bağlantı", msg)
        else:
            QMessageBox.warning(self, "Bağlantı", msg)

    def _test_print(self) -> None:
        # Boş örnek bir adisyon hazırla
        from utils.printer_handler import print_receipt

        order = {
            "order_number": "TEST",
            "total_amount": 0,
            "payment_method": "cash",
            "payment_status": "pending",
            "created_at": "",
        }
        items: list[dict[str, Any]] = []
        settings = {
            "company_name": self._inputs["company_name"].text() or "TEST",
            "company_phone": self._inputs["company_phone"].text(),
            "company_address": self._inputs["company_address"].text(),
        }
        ok, msg = print_receipt(order, items, settings)
        QMessageBox.information(self, "Test Yazdır", msg)
