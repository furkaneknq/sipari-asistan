"""Genel yardımcı fonksiyonlar."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal


def normalize_phone(phone: str) -> str:
    """Telefon numarasını sadece rakamlardan oluşan, son 10 haneli forma çevirir.

    >>> normalize_phone("+90 532 123 45 67")
    '5321234567'
    >>> normalize_phone("0532-123-45-67")
    '5321234567'
    """
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 10:
        digits = digits[-10:]
    return digits


def format_phone(phone: str) -> str:
    """0532 123 45 67 formatında okunabilir görünüm."""
    normalized = normalize_phone(phone)
    if len(normalized) == 10:
        return f"0{normalized[0:3]} {normalized[3:6]} {normalized[6:8]} {normalized[8:10]}"
    return phone or ""


def format_currency(amount: float | Decimal | int | None, symbol: str = "₺") -> str:
    """1234.5 -> '₺1.234,50' (Türkçe biçim)."""
    if amount is None:
        amount = 0
    try:
        value = float(amount)
    except (TypeError, ValueError):
        value = 0.0
    formatted = f"{value:,.2f}"
    # 1,234.56 -> 1.234,56
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{symbol}{formatted}"


def parse_iso_datetime(value: str | None) -> datetime | None:
    """ISO 8601 string'i datetime'a çevirir ve yerel saate dönüştürür."""
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt
    except ValueError:
        return None


def short_time(value: str | datetime | None) -> str:
    """ISO veya datetime'dan 'HH:MM' formatı."""
    if isinstance(value, str):
        value = parse_iso_datetime(value)
    if not isinstance(value, datetime):
        return ""
    return value.strftime("%H:%M")


def short_date(value: str | datetime | None) -> str:
    if isinstance(value, str):
        value = parse_iso_datetime(value)
    if not isinstance(value, datetime):
        return ""
    return value.strftime("%d.%m.%Y")


def parse_maps_link(url: str) -> tuple[float | None, float | None]:
    """Google Maps linkinden enlem/boylam çıkarır.

    Desteklenen formatlar:
    - https://maps.google.com/?q=39.9208,32.8541
    - https://www.google.com/maps/@39.9208,32.8541,17z
    - https://www.google.com/maps/place/.../@39.9208,32.8541,...
    - https://maps.app.goo.gl/... (kısa link — yönlendirme takip edilir)
    - https://goo.gl/maps/... (kısa link — yönlendirme takip edilir)
    - Düz koordinat: 39.9208,32.8541
    """
    if not url:
        return None, None
    url = url.strip()

    # Kısa link ise yönlendirmeyi takip ederek tam URL'yi al
    if "goo.gl/" in url or "maps.app" in url:
        try:
            resolved = _resolve_short_url(url)
            if resolved and resolved != url:
                url = resolved
        except Exception:  # noqa: BLE001
            pass

    return _extract_coords(url)


def _extract_coords(url: str) -> tuple[float | None, float | None]:
    """URL veya metin içinden koordinat çıkarır."""
    patterns = [
        r"@(-?\d+\.?\d*),\s*(-?\d+\.?\d*)",      # @lat,lng
        r"[?&]q=(-?\d+\.?\d*),\s*(-?\d+\.?\d*)",  # ?q=lat,lng
        r"[?&]ll=(-?\d+\.?\d*),\s*(-?\d+\.?\d*)", # ?ll=lat,lng
        r"place/[^/]*/(-?\d+\.?\d*),\s*(-?\d+\.?\d*)",  # place/.../lat,lng
        r"!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)",      # !3dlat!4dlng (kısa link çözümleri)
        r"^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$",      # düz koordinat
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            try:
                lat = float(match.group(1))
                lng = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    return lat, lng
            except ValueError:
                continue

    return None, None


def _resolve_short_url(short_url: str) -> str | None:
    """Kısa URL'yi yönlendirme takip ederek tam URL'ye çevirir."""
    import urllib.request

    req = urllib.request.Request(short_url, method="HEAD")
    req.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.url
    except Exception:  # noqa: BLE001
        # HEAD başarısız olursa GET ile dene
        try:
            req2 = urllib.request.Request(short_url, method="GET")
            req2.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req2, timeout=5) as resp:
                return resp.url
        except Exception:  # noqa: BLE001
            return None


def fit_to_screen(
    widget,
    preferred_w: int,
    preferred_h: int,
    min_w_ratio: float = 0.42,
    min_h_ratio: float = 0.42,
    max_ratio: float = 0.92,
    min_w: int = 900,
    min_h: int = 600,
) -> None:
    """Widget'ı ekran çözünürlüğüne göre boyutlandırır.

    - Tercih edilen boyut > ekrandan büyükse ekranın %92'sine küçültür
    - Pencere her zaman ekrana sığar, taşan kısım kalmaz
    """
    from PyQt6.QtGui import QGuiApplication

    screen = QGuiApplication.primaryScreen()
    if screen is None:
        widget.resize(preferred_w, preferred_h)
        return
    geo = screen.availableGeometry()
    max_w = int(geo.width() * max_ratio)
    max_h = int(geo.height() * max_ratio)
    w = min(preferred_w, max_w)
    h = min(preferred_h, max_h)
    widget.resize(w, h)
    min_width = min(max(int(geo.width() * min_w_ratio), min_w), w)
    min_height = min(max(int(geo.height() * min_h_ratio), min_h), h)
    widget.setMinimumSize(min_width, min_height)
    # Mümkünse ekran içinde ortala
    try:
        widget.move(
            geo.left() + (geo.width() - w) // 2,
            geo.top() + (geo.height() - h) // 2,
        )
    except Exception:  # noqa: BLE001
        pass


def keep_widget_on_screen(widget, margin: int = 24) -> None:
    """Kayıtlı pencere konumu ekran dışında kalırsa görünür alana taşır."""
    from PyQt6.QtGui import QGuiApplication

    screens = QGuiApplication.screens()
    if not screens:
        return

    frame = widget.frameGeometry()
    for screen in screens:
        if screen.availableGeometry().intersects(frame):
            return

    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    geo = screen.availableGeometry()
    width = min(frame.width(), geo.width() - margin * 2)
    height = min(frame.height(), geo.height() - margin * 2)
    widget.resize(width, height)
    widget.move(
        geo.left() + (geo.width() - width) // 2,
        geo.top() + (geo.height() - height) // 2,
    )
