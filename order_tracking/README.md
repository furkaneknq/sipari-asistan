# Sipariş Takip Masaüstü Uygulaması

PyQt6 + Supabase tabanlı sipariş takip masaüstü uygulaması.

## Özellikler

- **Kanban tarzı sipariş paneli** — Yeni / Hazırlanıyor / Yolda / Teslim Edildi / İptal sütunları
- **Tarih seçici** — geçmiş ve ileri tarihli siparişlerin görüntülenmesi
- **Kuryeye / duruma göre görünüm** seçenekleri
- **Gelen arama popup'ları** — birden fazla telefon eş zamanlı çağrı yapabilir, her biri sağ üstte istiflenir
- **Otomatik müşteri eşleştirme** (DB trigger'ı + son 10 hane normalizasyonu)
- **Müşteri yönetimi** — arama, çoklu adres, sipariş geçmişi
- **Excel import/export** (openpyxl)
- **Ürün/Kategori yönetimi**
- **Kurye yönetimi** + aktif sipariş sayıları
- **Adisyon önizleme + termal yazıcı** desteği (python-escpos, 80mm/58mm)
- **Açık/Koyu tema** (QSS)
- **"Son kayıt" göstergesi** — ana pencerenin sağ üstünde her zaman görünür
- **Polling tabanlı realtime** — 2 saniyede bir veri tabanını sorgular, değişiklikleri Qt sinyalleri olarak yayınlar

## Kurulum

### 1) Sanal ortam (önerilen)

```bash
cd order_tracking
python3 -m venv .venv
source .venv/bin/activate          # Linux / macOS
# veya: .venv\Scripts\activate      # Windows
```

### 2) Bağımlılıklar

```bash
pip install -r requirements.txt
```

### 3) `.env` dosyası

```bash
cp .env.example .env
# .env'i aç ve değerleri Supabase Dashboard'dan kopyala
```

`.env` içine şunları doldur:

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SECRET_KEY=eyJhbGciOi...   # Settings → API → Secret keys → Reveal
```

### 4) Çalıştır

```bash
python main.py
```

## Yazıcı Yapılandırması

`.env` dosyasında `PRINTER_TYPE` değerini değiştirerek yazıcı türünü seçebilirsin:

| Değer     | Açıklama                                         |
| --------- | ------------------------------------------------ |
| `dummy`   | Yazıcı yok, sadece önizleme (varsayılan)         |
| `usb`     | USB termal yazıcı (`PRINTER_USB_VENDOR_ID/...`)  |
| `network` | Ağ yazıcısı (`PRINTER_NETWORK_HOST` + port 9100) |
| `serial`  | Seri port (`/dev/ttyUSB0`, baudrate 9600)        |

## Klasör Yapısı

```
order_tracking/
├── main.py
├── config.py
├── requirements.txt
├── .env.example
│
├── database/                # Supabase katmanı
│   ├── supabase_client.py
│   ├── customers_db.py
│   ├── orders_db.py
│   ├── products_db.py
│   ├── couriers_db.py
│   └── realtime_listener.py
│
├── ui/                      # PyQt6 arayüz
│   ├── main_window.py
│   ├── orders_panel.py      (Kanban)
│   ├── customers_panel.py
│   ├── products_panel.py
│   ├── couriers_panel.py
│   ├── settings_panel.py
│   ├── incoming_call_popup.py
│   ├── order_detail_dialog.py
│   ├── customer_detail_dialog.py
│   ├── new_customer_dialog.py
│   ├── receipt_preview.py
│   └── themes.py
│
├── utils/
│   ├── helpers.py
│   ├── excel_handler.py
│   └── printer_handler.py
│
└── assets/
    ├── icons/
    └── styles/
        ├── light.qss
        └── dark.qss
```

## Realtime Hakkında

Kod, Supabase realtime websocket yerine **polling** (2 saniye aralıkla DB sorgusu) kullanır. Sebep: PyQt6 event loop ile asyncio websocket integration'ı kararsız. Polling tüm tablolardaki `updated_at` değişikliklerini ve `incoming_calls` tablosundaki yeni satırları yakalar.

İleride websocket'e geçmek istenirse `database/realtime_listener.py` içindeki `RealtimeListener` sınıfı `AsyncRealtimeListener` ile değiştirilebilir.

## Sorun Giderme

| Hata                                     | Çözüm                                                                |
| ---------------------------------------- | -------------------------------------------------------------------- |
| `ModuleNotFoundError: No module named …` | `pip install -r requirements.txt` çalıştırılmadı                     |
| `Yapılandırma Eksik`                     | `.env` dosyası yok veya `SUPABASE_URL`/`SUPABASE_SECRET_KEY` boş     |
| `Bağlantı Hatası`                        | Supabase URL veya key yanlış, ya da internet bağlantısı yok          |
| `RLS denied`                             | Publishable key kullanıyorsan → `SUPABASE_SECRET_KEY` (service_role) |
| Yazıcı bulunamadı                        | `.env` içinde `PRINTER_TYPE=dummy` yap, veya doğru USB ID gir        |
```
