"""80mm termal adisyon yazıcısı (ESC/POS).

İki fiş formatı:
  1. Müşteri fişi   — print_customer_receipt(order_data)
  2. Hazırlama fişi — print_preparation_receipt(selected_orders)

Üç bağlantı modu: usb | network | dummy (önizleme)
Türkçe karakter desteği, otomatik kağıt kesimi.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import config


# =====================================================================
# YAZDIRICI BAĞLANTISI
# =====================================================================

def _get_printer():
    """config ayarlarına göre yazıcı nesnesi döner. Bulamazsa None."""
    ptype = (config.PRINTER_TYPE or "dummy").lower()
    if ptype == "dummy":
        return None
    try:
        if ptype == "usb":
            from escpos.printer import Usb
            vendor = int(config.PRINTER_USB_VENDOR_ID or "0x04b8", 16)
            product = int(config.PRINTER_USB_PRODUCT_ID or "0x0202", 16)
            return Usb(vendor, product)
        elif ptype == "network":
            from escpos.printer import Network
            host = config.PRINTER_NETWORK_HOST or "192.168.1.100"
            port = int(config.PRINTER_NETWORK_PORT or 9100)
            return Network(host, port=port)
    except Exception:  # noqa: BLE001
        return None
    return None


def test_printer_connection() -> tuple[bool, str]:
    """Yazıcı bağlantı testi. (success, message) döner."""
    ptype = (config.PRINTER_TYPE or "dummy").lower()
    if ptype == "dummy":
        return False, "Yazıcı tipi 'dummy' olarak ayarlı. .env dosyasını kontrol edin."
    try:
        p = _get_printer()
        if p is None:
            return False, "Yazıcıya bağlanılamadı."
        p.close()
        return True, "Yazıcı bağlantısı başarılı."
    except Exception as e:  # noqa: BLE001
        return False, f"Yazıcı hatası: {e}"


# =====================================================================
# YARDIMCI FONKSİYONLAR
# =====================================================================

WIDTH = 32  # 80mm yazıcı karakter genişliği


def _hr(char: str = "─") -> str:
    return char * WIDTH


def _center(text: str) -> str:
    text = text.strip()
    if len(text) >= WIDTH:
        return text[:WIDTH]
    pad = (WIDTH - len(text)) // 2
    return " " * pad + text


def _two_col(left: str, right: str) -> str:
    right = str(right)
    max_left = WIDTH - len(right) - 1
    if len(left) > max_left:
        left = left[:max_left]
    gap = WIDTH - len(left) - len(right)
    return left + " " * gap + right


def _wrap(text: str, width: int | None = None) -> list[str]:
    w = width or WIDTH
    text = (text or "").strip()
    if not text:
        return []
    out: list[str] = []
    while text:
        if len(text) <= w:
            out.append(text)
            break
        cut = text.rfind(" ", 0, w)
        if cut <= 0:
            cut = w
        out.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    return out


def _fmt_currency(amount) -> str:
    try:
        return f"₺{float(amount):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "₺0"


# =====================================================================
# FORMAT 1: MÜŞTERİ FİŞİ
# =====================================================================

def build_customer_receipt_text(order_data: dict[str, Any]) -> str:
    """Müşteri fişi metin çıktısı üretir (önizleme ve yazdırma için)."""
    lines: list[str] = []

    # İşletme bilgisi
    lines.append("=" * WIDTH)
    lines.append(_center(order_data.get("business_name", "İŞLETME").upper()))
    if order_data.get("business_address"):
        for chunk in _wrap(order_data["business_address"]):
            lines.append(_center(chunk))
    if order_data.get("business_phone"):
        lines.append(_center(f"Tel: {order_data['business_phone']}"))
    lines.append("=" * WIDTH)

    # Sipariş no + tarih
    order_no = order_data.get("order_number", "")
    date = order_data.get("date", "")
    time = order_data.get("time", "")
    lines.append(f"Sipariş: #{order_no}")
    lines.append(f"Tarih: {date} {time}".strip())
    lines.append(_hr())

    # Müşteri bilgileri
    if order_data.get("customer_name"):
        lines.append(f"Müşteri: {order_data['customer_name']}")
    if order_data.get("customer_phone"):
        lines.append(f"Tel: {order_data['customer_phone']}")
    if order_data.get("customer_address"):
        addr_lines = _wrap(order_data["customer_address"], WIDTH - 7)
        lines.append(f"Adres: {addr_lines[0]}" if addr_lines else "Adres: -")
        for chunk in addr_lines[1:]:
            lines.append(f"       {chunk}")
    lines.append(_hr())

    # Ürün listesi
    lines.append(_two_col("Ürün", "Tutar"))
    lines.append(_hr())
    for item in order_data.get("items", []):
        name = item.get("name", "")
        qty = item.get("qty", item.get("quantity", 0))
        unit = item.get("unit", "adet")
        total = item.get("total", item.get("total_price", 0))
        try:
            qty_s = f"{float(qty):g}"
        except (TypeError, ValueError):
            qty_s = str(qty)
        left = f"{name} {qty_s}{unit}"
        right = _fmt_currency(total)
        lines.append(_two_col(left, right))
    lines.append(_hr())

    # Toplam
    lines.append(_two_col("TOPLAM:", _fmt_currency(order_data.get("total", 0))))
    lines.append(_hr())

    # Ödeme bilgisi
    if order_data.get("payment_method"):
        lines.append(f"Ödeme: {order_data['payment_method']}")
    if order_data.get("payment_amount") is not None:
        lines.append(f"Alınacak: {_fmt_currency(order_data['payment_amount'])}")
    if order_data.get("courier_name"):
        lines.append(f"Kurye: {order_data['courier_name']}")
    if order_data.get("note"):
        lines.append(f"Not: {order_data['note']}")

    # Alt mesaj
    lines.append("=" * WIDTH)
    lines.append(_center("Afiyet olsun!"))
    lines.append("=" * WIDTH)
    return "\n".join(lines)


def print_customer_receipt(order_data: dict[str, Any]) -> tuple[bool, str]:
    """Müşteri fişini yazıcıya gönderir."""
    text = build_customer_receipt_text(order_data)
    printer = _get_printer()
    if printer is None:
        return False, "Yazıcı bulunamadı veya dummy modda."
    try:
        printer.set(align="center", font="a", bold=True, width=2, height=2)
        printer.text(order_data.get("business_name", "İŞLETME").upper() + "\n")
        printer.set(align="left", font="a", bold=False, width=1, height=1)
        # Satır satır yazdır, TOPLAM büyük font
        for line in text.split("\n"):
            if line.startswith("TOPLAM:"):
                printer.set(bold=True, width=2, height=2)
                printer.text(line + "\n")
                printer.set(bold=False, width=1, height=1)
            else:
                printer.text(line + "\n")
        printer.cut()
        printer.close()
        return True, "Müşteri fişi yazdırıldı."
    except Exception as e:  # noqa: BLE001
        return False, f"Yazıcı hatası: {e}"


# =====================================================================
# FORMAT 2: HAZIRLAMA FİŞİ
# =====================================================================

def build_preparation_receipt_text(selected_orders: list[dict[str, Any]]) -> str:
    """Hazırlama fişi metin çıktısı üretir."""
    lines: list[str] = []
    now = datetime.now()

    lines.append("=" * WIDTH)
    lines.append(_center("★ HAZIRLANACAK SİPARİŞLER ★"))
    lines.append(_center(now.strftime("%d/%m/%Y - %H:%M")))
    if len(selected_orders) > 1:
        lines.append(_center(f"Toplam: {len(selected_orders)} Sipariş"))
    lines.append("=" * WIDTH)

    for order in selected_orders:
        order_no = order.get("order_number", "?")
        lines.append(f"■ SİPARİŞ #{order_no}")
        lines.append(_hr())
        for item in order.get("items", []):
            name = item.get("name", "")
            qty = item.get("qty", item.get("quantity", 0))
            unit = item.get("unit", "adet")
            try:
                qty_s = f"{float(qty):g}"
            except (TypeError, ValueError):
                qty_s = str(qty)
            left = f"{name} {qty_s}{unit}"
            right = "_______"
            lines.append(_two_col(left, right))

    lines.append("=" * WIDTH)
    return "\n".join(lines)


def print_preparation_receipt(selected_orders: list[dict[str, Any]]) -> tuple[bool, str]:
    """Hazırlama fişini yazıcıya gönderir."""
    if not selected_orders:
        return False, "Sipariş seçilmedi."
    text = build_preparation_receipt_text(selected_orders)
    printer = _get_printer()
    if printer is None:
        return False, "Yazıcı bulunamadı veya dummy modda."
    try:
        printer.set(align="left", font="a", bold=False, width=1, height=1)
        printer.text(text + "\n")
        printer.cut()
        printer.close()
        return True, "Hazırlama fişi yazdırıldı."
    except Exception as e:  # noqa: BLE001
        return False, f"Yazıcı hatası: {e}"


# =====================================================================
# ÖNİZLEME DIALOG (PyQt6)
# =====================================================================

def show_receipt_preview(parent, text: str, title: str = "Fiş Önizleme") -> bool:
    """Yazdırma öncesi fiş önizleme penceresi gösterir.

    Kullanıcı 'Yazdır' derse True, 'İptal' derse False döner.
    """
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
    from PyQt6.QtGui import QFont
    from PyQt6.QtCore import Qt

    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setMinimumSize(400, 500)
    layout = QVBoxLayout(dlg)
    layout.setContentsMargins(8, 8, 8, 8)

    text_edit = QTextEdit()
    text_edit.setReadOnly(True)
    text_edit.setFont(QFont("Courier New", 10))
    text_edit.setPlainText(text)
    text_edit.setStyleSheet(
        "QTextEdit { background: white; color: black; padding: 12px; }"
    )
    layout.addWidget(text_edit)

    buttons = QDialogButtonBox()
    btn_print = buttons.addButton("Yazdır", QDialogButtonBox.ButtonRole.AcceptRole)
    btn_cancel = buttons.addButton("İptal", QDialogButtonBox.ButtonRole.RejectRole)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    layout.addWidget(buttons)

    result = dlg.exec()
    return result == QDialog.DialogCode.Accepted


# =====================================================================
# ESKİ API UYUMLULUĞU (mevcut çağrılar için)
# =====================================================================

def build_receipt_text(
    order: dict[str, Any],
    items: list[dict[str, Any]],
    settings: dict[str, str],
    width: int = 32,
) -> str:
    """Eski API — build_customer_receipt_text'e yönlendirir."""
    from utils.helpers import format_currency, format_phone

    customer = order.get("customers") or {}
    address = order.get("customer_addresses") or {}
    courier = order.get("couriers") or {}

    created_at = order.get("created_at") or datetime.now().isoformat()
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        date_str = dt.strftime("%d/%m/%Y")
        time_str = dt.strftime("%H:%M")
    except Exception:  # noqa: BLE001
        date_str = str(created_at)
        time_str = ""

    order_data = {
        "business_name": settings.get("company_name", "İşletme"),
        "business_address": settings.get("company_address", ""),
        "business_phone": settings.get("company_phone", ""),
        "order_number": order.get("order_number", ""),
        "date": date_str,
        "time": time_str,
        "customer_name": customer.get("name", ""),
        "customer_phone": customer.get("phone", ""),
        "customer_address": (address.get("address_text") or
                            order.get("address_text", "")),
        "items": [
            {
                "name": (i.get("products") or {}).get("name") or i.get("name", ""),
                "qty": i.get("quantity", 0),
                "unit": i.get("unit") or (i.get("products") or {}).get("unit", "adet"),
                "total": i.get("total_price", 0),
            }
            for i in items
        ],
        "total": order.get("total_amount", 0),
        "payment_method": {
            "cash": "Nakit", "credit_card": "Kredi Kartı", "iban": "IBAN"
        }.get(order.get("payment_method") or "", "-"),
        "payment_amount": order.get("total_amount", 0),
        "courier_name": courier.get("name", ""),
        "note": order.get("notes", ""),
    }
    return build_customer_receipt_text(order_data)


def print_receipt(
    order: dict[str, Any],
    items: list[dict[str, Any]],
    settings: dict[str, str],
    printer_type: str | None = None,
    printer_options: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Eski API uyumluluğu — müşteri fişi yazdırır."""
    text = build_receipt_text(order, items, settings)
    printer = _get_printer()
    if printer is None:
        return True, "Yazıcı yapılandırılmadı (dummy mod). Sadece önizleme."
    try:
        printer.set(align="left", font="a", bold=False, width=1, height=1)
        printer.text(text + "\n\n\n")
        printer.cut()
        printer.close()
        return True, "Adisyon yazdırıldı."
    except Exception as exc:  # noqa: BLE001
        return False, f"Yazıcı hatası: {exc}"
