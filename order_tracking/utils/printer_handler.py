"""Adisyon yazıcısı (ESC/POS termal yazıcı) yardımcısı.

Üç moda destek verir:
    * usb     : USB termal yazıcı (vendor/product id ile)
    * network : Ağ üzerinden yazıcı (IP + port 9100)
    * dummy   : Yazıcı yokken metin önizlemesi üretir (geliştirme)

Aynı şablon hem gerçek yazıcı hem de "Adisyon Önizleme" penceresi
için kullanılabilsin diye fiş metnini ayrı bir fonksiyon üretir.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import config


# ---------------------------------------------------------------------
# Fiş metni üretimi (önizleme + yazıcı için ortak)
# ---------------------------------------------------------------------
def build_receipt_text(
    order: dict[str, Any],
    items: list[dict[str, Any]],
    settings: dict[str, str],
    width: int = 32,
) -> str:
    """Düz metin halinde adisyon fişi üretir.

    width = 32 → 80mm yazıcı (tipik)
    width = 24 → 58mm yazıcı
    """
    from utils.helpers import format_currency, format_phone

    company_name = settings.get("company_name", "İşletme")
    company_address = settings.get("company_address", "")
    company_phone = settings.get("company_phone", "")

    lines: list[str] = []

    def hr(char: str = "=") -> str:
        return char * width

    def center(text: str) -> str:
        text = text.strip()
        if len(text) >= width:
            return text[:width]
        pad = (width - len(text)) // 2
        return " " * pad + text

    def two_col(left: str, right: str) -> str:
        right = str(right)
        if len(left) + len(right) >= width:
            left = left[: width - len(right) - 1]
        gap = width - len(left) - len(right)
        return left + " " * gap + right

    lines.append(hr("="))
    lines.append(center(company_name.upper()))
    if company_address:
        for chunk in _wrap(company_address, width):
            lines.append(center(chunk))
    if company_phone:
        lines.append(center(f"Tel: {format_phone(company_phone)}"))
    lines.append(hr("="))

    order_no = order.get("order_number")
    created_at = order.get("created_at") or datetime.now().isoformat()
    try:
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        created_str = dt.strftime("%d.%m.%Y %H:%M")
    except Exception:  # noqa: BLE001
        created_str = str(created_at)
    lines.append(f"Sipariş No: #{order_no}")
    lines.append(f"Tarih: {created_str}")
    lines.append(hr("-"))

    customer = order.get("customers") or {}
    address = order.get("customer_addresses") or {}
    courier = order.get("couriers") or {}

    if customer:
        lines.append(f"Müşteri: {customer.get('name', '-')}")
        if customer.get("phone"):
            lines.append(f"Tel: {format_phone(customer['phone'])}")
    if address.get("address_text"):
        lines.append("Adres:")
        for chunk in _wrap(address["address_text"], width - 2):
            lines.append("  " + chunk)

    lines.append(hr("-"))
    lines.append(two_col("Ürün", "Tutar"))
    lines.append(hr("-"))

    for item in items:
        product = item.get("products") or {}
        name = product.get("name") or item.get("name") or "-"
        qty = item.get("quantity", 0)
        unit = item.get("unit") or product.get("unit", "adet")
        try:
            qty_disp = f"{float(qty):g}"
        except (TypeError, ValueError):
            qty_disp = str(qty)
        line1 = name[:width]
        line2 = two_col(
            f"  {qty_disp} {unit}",
            format_currency(item.get("total_price", 0)),
        )
        lines.append(line1)
        lines.append(line2)

    lines.append(hr("-"))
    lines.append(two_col("TOPLAM:", format_currency(order.get("total_amount", 0))))
    lines.append(hr("-"))

    payment_method = {
        "cash": "Nakit",
        "credit_card": "Kredi Kartı",
        "iban": "IBAN",
    }.get(order.get("payment_method") or "", "-")
    lines.append(f"Ödeme: {payment_method}")
    if order.get("payment_status") == "paid":
        lines.append("Durum: Ödendi")
    elif order.get("payment_status") == "partial":
        lines.append("Durum: Kısmi ödeme")
    else:
        lines.append(f"Alınacak: {format_currency(order.get('total_amount', 0))}")

    if courier.get("name"):
        lines.append(f"Kurye: {courier['name']}")

    if order.get("notes"):
        lines.append(hr("-"))
        lines.append("Not:")
        for chunk in _wrap(order["notes"], width - 2):
            lines.append("  " + chunk)

    lines.append(hr("="))
    lines.append(center("Afiyet olsun!"))
    lines.append(hr("="))
    return "\n".join(lines)


def _wrap(text: str, width: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    out: list[str] = []
    while text:
        if len(text) <= width:
            out.append(text)
            break
        # boşluktan kır
        cut = text.rfind(" ", 0, width)
        if cut <= 0:
            cut = width
        out.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    return out


# ---------------------------------------------------------------------
# Gerçek yazıcıya gönderim
# ---------------------------------------------------------------------
def print_receipt(
    order: dict[str, Any],
    items: list[dict[str, Any]],
    settings: dict[str, str],
    printer_type: str | None = None,
    printer_options: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    """Adisyonu yazıcıya gönderir. (success, message) döner.

    printer_type  : 'dummy' | 'usb' | 'network' | 'serial'
    printer_options:
        usb:  {'vendor_id': '0x1234', 'product_id': '0x5678'}
        network: {'host': '192.168.1.100', 'port': 9100}
        serial:  {'devfile': '/dev/ttyUSB0', 'baudrate': 9600}
    """
    ptype = (printer_type or config.PRINTER_TYPE or "dummy").lower()
    opts = printer_options or {}

    width = 48 if config.PRINTER_PAPER_WIDTH == 80 else 32
    text = build_receipt_text(order, items, settings, width=width)

    if ptype == "dummy":
        return True, "Yazıcı yapılandırılmadı (dummy mod). Sadece önizleme."

    try:
        if ptype == "usb":
            from escpos.printer import Usb

            vendor = int(
                opts.get("vendor_id") or config.PRINTER_USB_VENDOR_ID or "0x04b8", 16
            )
            product = int(
                opts.get("product_id") or config.PRINTER_USB_PRODUCT_ID or "0x0202", 16
            )
            printer = Usb(vendor, product)
        elif ptype == "network":
            from escpos.printer import Network

            host = opts.get("host") or config.PRINTER_NETWORK_HOST or "192.168.1.100"
            port = int(opts.get("port") or config.PRINTER_NETWORK_PORT or 9100)
            printer = Network(host, port=port)
        elif ptype == "serial":
            from escpos.printer import Serial

            dev = opts.get("devfile") or "/dev/ttyUSB0"
            baud = int(opts.get("baudrate") or 9600)
            printer = Serial(devfile=dev, baudrate=baud)
        else:
            return False, f"Bilinmeyen yazıcı tipi: {ptype}"

        printer.set(align="left", font="a", width=1, height=1)
        printer.text(text + "\n\n\n")
        printer.cut()
        return True, "Adisyon yazdırıldı."
    except Exception as exc:  # noqa: BLE001
        return False, f"Yazıcı hatası: {exc}"
