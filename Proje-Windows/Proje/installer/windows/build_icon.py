"""
app.ico üretici.

PyInstaller ve Inno Setup için Windows ikonu (.ico) oluşturur.
Birden fazla çözünürlük (16x16'dan 256x256'ya) içerir ki Windows
küçük/büyük her yerde keskin görünsün.

Çalıştırma:
    python installer/windows/build_icon.py

Çıktı: installer/windows/app.ico
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTPUT = Path(__file__).resolve().parent / "app.ico"
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# Ana renk: Sipariş Asistanı yeşili (#2E7D32)
PRIMARY = (46, 125, 50, 255)
ACCENT = (255, 255, 255, 255)


def _make_image(size: int) -> Image.Image:
    """Yuvarlak köşeli yeşil kare üzerine 'S' harfi."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Yuvarlak köşeli arkaplan
    radius = max(2, size // 6)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=PRIMARY)

    # Ortada büyük 'S' (sipariş)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(size * 0.62))
    except OSError:
        font = ImageFont.load_default()

    text = "S"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pos = ((size - tw) // 2 - bbox[0], (size - th) // 2 - bbox[1] - int(size * 0.04))
    draw.text(pos, text, font=font, fill=ACCENT)

    return img


def main() -> None:
    images = [_make_image(s[0]) for s in SIZES]
    base = images[-1]   # 256x256
    base.save(OUTPUT, format="ICO", sizes=SIZES)
    print(f"[ok] {OUTPUT} oluşturuldu  ({len(SIZES)} çözünürlük)")


if __name__ == "__main__":
    main()
