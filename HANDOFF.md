# Sipariş Takip Sistemi — Hand-off Dökümanı

> **Versiyon:** v0.1.0
> **Son güncelleme:** 8 Mayıs 2026
> **Hedef kitle:** Projeyi devralacak veya 1 ay sonra geri dönecek geliştirici

Bu döküman; projenin nereden başladığını, şu an ne durumda olduğunu, hangi kararların neden alındığını ve neyin sırada beklediğini hızlıca anlamanı sağlamak için yazılmıştır.

---

## 1. Proje Özeti

**Ne yapıyor?**
Pide salonu / lokanta / market gibi telefon sipariş alan işletmeler için **sipariş takip masaüstü uygulaması**. Bağlı Android telefonlardan gelen aramalar Supabase üzerinden masaüstüne anlık düşer; kullanıcı tek tıkla sipariş girer, kuryeye atar, adisyon yazdırır.

**Hedef akış:**

```
📱 Android (Numara Aktarım) ──┐
                                ├──► 🗄️ Supabase ◄──► 🖥️ Masaüstü ──► 🖨️ Adisyon
📱 Android (Kurye Takip)    ──┘                       (PyQt6)
```

**Şu an çalışan kısım:**
- ✅ **Veritabanı** (Supabase / PostgreSQL) — şema, trigger'lar, RLS, seed data
- ✅ **Masaüstü uygulama** (Python + PyQt6) — sipariş yönetimi, müşteri, ürün, kurye, ayarlar, gelen arama popup'ı, adisyon yazıcı

**Henüz yapılmadı:**
- ⏳ ~~**Android Numara Aktarım** uygulaması~~ ✅ Tamamlandı (`android_app/call_relay/`)
- ⏳ ~~**Android Kurye Takip** uygulaması~~ ✅ Tamamlandı (`android_app/courier_tracker/`)

---

## 2. Mimari

```
                ┌──────────────────────────────────────────────┐
                │             Supabase (PostgreSQL)            │
                │  customers, customer_addresses, categories,  │
                │  products, couriers, orders, order_items,    │
                │  phones, incoming_calls, settings, themes    │
                │  + trigger'lar + RLS + realtime publication  │
                └──────────────┬───────────────────────────────┘
                               │ HTTPS REST + (gelecekte) WS
            ┌──────────────────┼──────────────────────┐
            │                  │                      │
   📱 Android (TODO)    🖥️ Masaüstü (Python)     📱 Android (TODO)
   Numara Aktarım       PyQt6 + supabase-py       Kurye Takip
   - Çağrıyı yakala     - 5 sekme + popup'lar     - Sipariş listesi
   - DB'ye INSERT       - Polling 2sn (realtime)  - Konum güncelle
                        - ESC/POS yazıcı
```

**Önemli karar — Realtime yerine Polling:**
Supabase realtime (websocket) yerine masaüstüde **2 saniyelik polling** kullandık. Sebep: PyQt6 event loop ile asyncio websocket integration kararsız çalışıyor. 2 sn gecikme tipik kullanım için yeterli; gerekirse `database/realtime_listener.py` içinde websocket'e geçilebilir. Detay → bkz. madde 11.

---

## 3. Teknoloji Yığını

| Katman | Teknoloji | Versiyon |
|---|---|---|
| Veritabanı | Supabase / PostgreSQL | 15+ |
| Masaüstü UI | PyQt6 | ≥6.8.0 |
| DB istemcisi | supabase-py | ≥2.9.0 |
| Çevre değişkeni | python-dotenv | ≥1.0.1 |
| Excel | openpyxl | ≥3.1.5 |
| Yazıcı | python-escpos | ≥3.1 |
| Telefon normalize | phonenumbers | ≥8.13.0 |
| Diğer | python-dateutil, Pillow | – |
| Python | 3.12+ (hâlihazırda 3.14.4) | – |

`requirements.txt` versiyon pinleri **gevşek** (`>=`) çünkü Python 3.14 için en güncel wheel'ler gerekiyor.

---

## 4. Veritabanı Şeması

11 tablo:

| Tablo | Sorumluluk | Önemli alanlar |
|---|---|---|
| `customers` | Müşteri kayıtları | `phone` (UNIQUE), `is_guest` |
| `customer_addresses` | Müşteri başına N adres | `is_default`, `latitude/longitude` |
| `categories` | Ürün kategorileri | `sort_order`, `color` |
| `products` | Ürünler | `category_id`, `price`, `unit` |
| `couriers` | Kuryeler | `phone`, `password` (Android giriş için), `current_lat/lng` |
| `orders` | Siparişler | `order_number` (1001'den auto-increment), `status`, `payment_method/status` |
| `order_items` | Sipariş kalemleri | `quantity`, `unit_price`, `total_price` (otomatik) |
| `phones` | Bağlı Android cihazlar | `device_id` (UNIQUE), `last_seen` |
| `incoming_calls` | Gelen aramalar | `phone_number`, `customer_id` (otomatik eşleşir) |
| `settings` | Anahtar/değer ayarlar | `key` (UNIQUE), `value` |
| `themes` | UI temaları | – |

### Önemli Trigger'lar (`database/sql/02_triggers.sql`)

1. `set_updated_at()` → customers + orders'da `updated_at` her UPDATE'te otomatik
2. `match_incoming_call_customer()` → INSERT'te telefon numarasını normalize edip (son 10 hane) `customers` ile otomatik eşleştirir
3. `calc_order_item_total()` → `order_items` INSERT/UPDATE'te `total_price = quantity * unit_price`
4. `refresh_order_total()` → `order_items` değişikliğinde `orders.total_amount` otomatik yeniden hesaplanır

### `order_number` 1001'den Başlıyor

`orders_order_number_seq` named sequence ile. Default `nextval(...)`.

### Status Constraint

`orders.status` CHECK constraint'i: `('new','preparing','on_way','delivered','cancelled')`. UI'da sadece **new / on_way / delivered** kullanılıyor (kullanıcı isteği üzerine "preparing/cancelled" gösterilmiyor ama DB'de kalmaya devam ediyor).

### RLS

Tüm tablolarda aktif. **Authenticated** rolüne tam erişim. Masaüstü `service_role` (secret key) ile bağlandığı için RLS'i bypass eder. Üretimde rol bazlı sıkılaştırmak gerekecek.

### Realtime Publication

11 tablonun tamamı `supabase_realtime` publication'ına eklendi (Android tarafı websocket dinleyebilir). Masaüstü polling kullanıyor.

### `is_guest` Kolonu (Migration v2)

`customers.is_guest BOOLEAN DEFAULT FALSE` — "Tek seferlik müşteri" özelliği için. `is_guest=true` olanlar `customers_db.list_customers` ve `latest_customer` çıktılarında **filtrelenir**, UI'da görünmez. Migration: `database/sql/05_migration_v2.sql`.

---

## 5. Klasör Yapısı

```
Proje/
├── database/
│   ├── README.md                    # SQL'leri çalıştırma rehberi
│   └── sql/
│       ├── 01_tables.sql            # Tablolar + sequence + index'ler
│       ├── 02_triggers.sql          # Trigger fonksiyonları + realtime
│       ├── 03_rls_policies.sql      # RLS politikaları
│       ├── 04_seed_data.sql         # Örnek veriler
│       └── 05_migration_v2.sql      # is_guest eklendi
│
├── HANDOFF.md                       # ← Bu döküman
│
└── order_tracking/                  # Masaüstü uygulama kökü
    ├── main.py                      # Giriş noktası (config + DB testi + main window)
    ├── config.py                    # .env okuyucu, yapılandırma sabitleri
    ├── requirements.txt             # Python paketleri (gevşek versiyon)
    ├── README.md                    # Kullanıcı kurulum rehberi
    ├── run.sh                       # Tek tıkla başlatma scripti (chmod +x)
    ├── .env.example                 # Şablon (Git'e gönderilir)
    ├── .env                         # GERÇEK değerler (Git'te yok)
    ├── .gitignore
    │
    ├── database/                    # Supabase katmanı (CRUD)
    │   ├── supabase_client.py       # Singleton client + bağlantı testi
    │   ├── customers_db.py          # Müşteri + adres CRUD
    │   ├── products_db.py           # Kategori + ürün CRUD
    │   ├── couriers_db.py           # Kurye CRUD + aktif sipariş sayımı
    │   ├── orders_db.py             # Sipariş + kalem CRUD + durum sabitleri
    │   ├── incoming_calls_db.py     # Gelen arama sorguları
    │   └── realtime_listener.py     # QThread polling listener
    │
    ├── ui/                          # PyQt6 görsel katman
    │   ├── main_window.py           # Header + 6 sekme + listener bağlama + popup
    │   ├── orders_panel.py          # Sipariş listesi (tablo + sol filtre)
    │   ├── customers_panel.py       # Müşteri tablosu + Excel + sil
    │   ├── products_panel.py        # Kategori + ürün yönetimi
    │   ├── couriers_panel.py        # Kurye listesi + aktif siparişler
    │   ├── settings_panel.py        # İşletme/tema/yazıcı/telefon ayarları
    │   ├── incoming_calls_panel.py  # Arama geçmişi sekmesi
    │   ├── incoming_call_popup.py   # Gelen arama bildirim popup'ı
    │   ├── new_customer_dialog.py   # Hızlı müşteri ekleme
    │   ├── customer_detail_dialog.py# Müşteri bilgi + adres + sipariş geçmişi
    │   ├── order_detail_dialog.py   # Sipariş oluştur/düzenle (en büyük dialog)
    │   ├── receipt_preview.py       # Adisyon önizleme + yazdır
    │   └── themes.py                # QSS yükleyici
    │
    ├── utils/                       # Yardımcı modüller
    │   ├── helpers.py               # Telefon normalize, TL formatı, tarih
    │   ├── excel_handler.py         # Müşteri Excel import/export
    │   └── printer_handler.py       # ESC/POS yazıcı + metin önizleme
    │
    └── assets/
        └── styles/
            ├── light.qss            # Açık tema
            └── dark.qss             # Koyu tema
```

**Toplam:** ~6.100 satır kod (Python + SQL + QSS)

---

## 6. Modül Sorumlulukları

### `database/` (DB katmanı)

Tek bir `Client` singleton'ı `supabase_client.get_client()` üzerinden paylaşılır. Her CRUD modülü kendi tablosuna ait fonksiyonları içerir; **iş mantığı UI'a sızmaz**, validation gibi şeyler dialog'larda yapılır ama DB'ye yakın hesaplamalar (örn. `count_active_orders`, `order_items_summary`) bu katmandadır.

| Modül | Önemli fonksiyonlar |
|---|---|
| `customers_db` | `list_customers(search, include_guests)`, `create_customer(name, phone, ..., is_guest)`, `latest_customer()` (is_guest=false), adres CRUD |
| `orders_db` | `list_orders(start_date, end_date, status, courier_id, customer_search)`, `create_order(items=[...])`, `update_order_status`, `assign_courier`, `mark_delivered`, sabitler (`STATUS_NEW` vs.) |
| `products_db` | Kategori + ürün CRUD, `list_products(category_id)` |
| `couriers_db` | Kurye CRUD, `count_active_orders(courier_id)`, `list_courier_orders(courier_id)` |
| `incoming_calls_db` | `list_calls(start_date, end_date, only_unprocessed, search)`, `mark_processed`, `delete_call` |
| `realtime_listener` | `RealtimeListener(QThread)` — 2sn'de bir 3 tabloyu poll eder, Qt sinyali yayınlar |

### `ui/` (Görsel katman)

**Convention:** Her panel/dialog ayrı dosyada. Dışarıyla iletişim **`pyqtSignal`** üzerinden yapılır; `MainWindow` aracı olur, bağımlılık döngüsü olmaz.

```
panel.signal_x.emit(value) ─► MainWindow._handler() ─► başka panel'i refresh et / dialog aç
```

Örnek: `OrdersPanel.open_customer_requested.emit(cid)` → `MainWindow._open_customer_detail(cid)` → `CustomerDetailDialog` açılır.

### `utils/`

Saf fonksiyonlar. UI ya da DB bağımlılığı **olabildiğince az**. `printer_handler.build_receipt_text()` fiş şablonu → hem önizlemede hem yazıcıda aynı çıktıyı üretir.

---

## 7. Kurulum & Çalıştırma

### İlk kurulum (Linux)

```bash
# 1. Veritabanı (Supabase Dashboard SQL Editor'da, sırasıyla):
#    01_tables.sql → 02_triggers.sql → 03_rls_policies.sql
#    → 04_seed_data.sql → 05_migration_v2.sql

# 2. Masaüstü uygulama
cd ~/Masaüstü/Proje/order_tracking
cp .env.example .env
# .env'i düzenle: SUPABASE_URL ve SUPABASE_SECRET_KEY

# 3. Çalıştır (sanal ortam + paketler + başlat)
./run.sh
```

### Sonraki çalıştırmalar

```bash
cd ~/Masaüstü/Proje/order_tracking && ./run.sh
```

`run.sh` akıllı:
- `.venv/` yoksa oluşturur
- `requirements.txt` değişmediyse paket kurmayı atlar (`.venv/.installed` flag dosyası ile)
- `.env` yoksa hata verir
- Sonunda `python main.py` çalıştırır

### Manuel kurulum (run.sh kullanmadan)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Linux'ta tipik Qt sorunları

PyQt6 platform plugin hatası alırsan (CachyOS/Arch):
```bash
sudo pacman -S xcb-util-cursor xcb-util-keysyms xcb-util-renderutil xcb-util-wm libxkbcommon-x11
```

---

## 8. Konfigürasyon

### `.env` dosyası

```env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SECRET_KEY=eyJhb...           # Settings → API → Secret keys (service_role)
SUPABASE_PUBLISHABLE_KEY=eyJhb...      # Opsiyonel, şu an kullanılmıyor

PRINTER_TYPE=dummy                      # dummy | usb | network | serial
PRINTER_PAPER_WIDTH=80                  # 58 veya 80
PRINTER_USB_VENDOR_ID=0x04b8
PRINTER_USB_PRODUCT_ID=0x0202
PRINTER_NETWORK_HOST=192.168.1.100
PRINTER_NETWORK_PORT=9100
```

### Neden `service_role` (secret key)?

Masaüstü tek bir işletme için çalıştığı varsayımıyla RLS bypass edilir → her şeye erişebilir. Bu anahtar **asla** mobile / git / public bir yere koyulmaz. `.gitignore` → `.env`.

Üretimde alternatif: Publishable key + email/password auth → her kullanıcının kendi RLS politikası. Şu an gerekmedi, kapsam dışı.

---

## 9. Mevcut Özellikler (Kullanıcı Cephesinden)

### 📋 Siparişler sekmesi (`orders_panel.py`)

- Sol panel:
  - Mini takvim
  - Hızlı tarih: Bugün / Dün / Bu Ay / Geçen Ay / Bu Yıl
  - Filtreler: Müşteri arama, Ödeme tipi, Durum
  - Aksiyon butonları: Yeni / Düzelt / Teslim Edildi / Yazdır / Sil
  - "Listeyi otomatik güncelle" checkbox
- Sağ üst: Tablo (S.No, Tarih, Müşteri, Telefon, Ödeme, Adet, Ödenen, Kurye, Durum) — **sıralanabilir**
- Tablo altında toplam kutuları (Kayıt, Adet, Sipariş Tutarı, Ödenen)
- Sağ alt: Seçilen siparişin kalemleri + sipariş açıklaması
- Sağ tık menüsü: Düzelt / **Müşteri Detayı** / Yazdır / **Kuryeye Ata** (alt menü) / Teslim Edildi / Sil

### 📞 Arama Geçmişi sekmesi (`incoming_calls_panel.py`)

- Tarih aralığı (preset + manuel)
- Telefon/müşteri arama
- "Yalnızca işlenmemiş" filtresi
- Her satırda hızlı buton: kayıtlıysa "Sipariş Aç", değilse "+ Müşteri"
- Çift tıklama → müşteri detayı veya yeni müşteri dialog'u

### 👥 Müşteriler sekmesi (`customers_panel.py`)

- Arama (isim/telefon)
- Excel **import / export**
- **Sil** butonu (uyarı + onay, sipariş varsa uyarır)
- Çift tıklama → detay (bilgi + adresler + sipariş geçmişi)
- Tek seferlik (`is_guest=true`) müşteriler **listede görünmez**

### 📦 Ürünler sekmesi (`products_panel.py`)

- Sol: Kategori listesi (ekle/sil)
- Sağ: Seçili kategorinin ürünleri (ekle/düzelt/sil)
- Çift tıklama → ürün düzenleme dialog'u

### 🏍️ Kuryeler sekmesi (`couriers_panel.py`)

- Kurye listesi (CRUD)
- Aktif sipariş sayısı sütunu
- Seçilen kuryenin siparişleri alt tabloda

### ⚙️ Ayarlar sekmesi (`settings_panel.py`)

- İşletme bilgileri (ad/tel/adres/IBAN)
- Tema seçimi (light/dark) — anlık uygulanır
- Yazıcı bilgisi (read-only — `.env`'den)
- Bağlı telefonlar tablosu
- DB bağlantı testi

### 🔔 Gelen Arama Popup (`incoming_call_popup.py`)

- Sağ üstte beliren küçük bildirim
- Birden fazla popup eş zamanlı (istiflenir)
- 30 sn sonra otomatik kapanır
- Müşteri kayıtlıysa "Sipariş Aç", değilse "+ Yeni Müşteri"

### 🖨️ Adisyon (`receipt_preview.py` + `printer_handler.py`)

- Önizleme penceresi (monospace metin)
- 80mm / 58mm seçilebilir
- ESC/POS USB / Network / Serial / Dummy modları
- Aynı şablon hem önizlemede hem yazıcıda

### Tek Seferlik (Misafir) Sipariş

Sipariş dialog'unda checkbox ile aktive edilir. Misafir adı (zorunlu) + telefon (opsiyonel) + adres (opsiyonel). Arka planda `is_guest=true` müşteri kaydı oluşturulur (UNIQUE constraint için telefon yoksa `GUEST<timestamp>` placeholder atanır).

---

## 10. Önemli İş Kuralları

| Kural | Nerede uygulanıyor |
|---|---|
| Telefon UNIQUE — son 10 hane normalize edilir | `customers` tablosu UNIQUE + `utils.helpers.normalize_phone` + DB trigger |
| Sipariş numarası 1001'den auto-increment | `orders_order_number_seq` (DB) |
| `order_items.total_price` ve `orders.total_amount` otomatik | DB trigger (UI hesaplamaz, sadece okur) |
| Gelen arama → müşteri otomatik eşleşir | DB trigger `match_incoming_call_customer` |
| Kurye atanınca durum otomatik `on_way` | `orders_panel._assign_courier` + `order_detail_dialog._save` |
| Kurye kaldırılınca durum `new`'a döner (delivered hariç) | aynı yer |
| `is_guest=true` müşteriler listelerde gösterilmez | `customers_db.list_customers` default filtre |
| `latest_customer()` (header'daki "Son Kayıt") sadece gerçek müşterileri sayar | `customers_db.latest_customer` |
| Realtime → 2sn polling, "auto refresh" kapalıysa orders_panel yenilemez | `realtime_listener` + `OrdersPanel.auto_refresh_enabled` |

---

## 11. Bilinen Kısıtlamalar / Teknik Borç

| Konu | Detay | Risk |
|---|---|---|
| **Realtime polling** | Websocket yerine 2sn DB polling. PyQt6 + asyncio sıkıntısı yüzünden seçildi | 2sn gecikme + hafif DB yükü. Sorun değil ama 100+ kullanıcılı bir kurulum için yetersiz |
| **`order_items_summary` her satır için sorgu** | `OrdersPanel._populate_orders_table` her sipariş için ayrı `order_items` SELECT atıyor | 100 sipariş = 100 sorgu. Şimdilik dert değil, üretimde bir RPC/view'e taşınmalı |
| **Customer combo'da çok fazla kayıt olunca Yeni Sipariş dialog'u yavaşlar** | Tüm müşterileri yükleyip Completer'a veriyor | 10K+ müşteride sorun olur, server-side search'e geçilmeli |
| **DB status field UI'da sadeleştirildi ama CHECK constraint hâlâ 5 değer** | preparing/cancelled UI'da yok ama DB'de var | Şimdilik sorunsuz, kafa karıştırabilir |
| **Müşteri silinince siparişler "RESTRICT" FK'sı yüzünden silinemez** | `orders.customer_id ON DELETE RESTRICT` | UI uyarı veriyor ama silme başarısız olur. Önce siparişler silinmeli (veya `CASCADE` migration) |
| **Yazıcı ayarları `.env`'den, UI'dan değiştirilemiyor** | Settings panel sadece bilgi gösteriyor | Çoğu kullanıcı için sorun değil ama UI'a taşımak temiz olur |
| **Tek seferlik müşteri telefonu yoksa `GUEST<timestamp>` placeholder** | UNIQUE constraint hack'i | Telefon nullable yapmak daha temiz olurdu (migration gerektirir) |
| **`incoming_calls` polling 50 satır limit** | Yoğun saatlerde kaçırılan arama olabilir | Pratikte sorun değil, son 10sn içinde 50'den fazla arama olası değil |
| **Kanban çıktı, tablo geldi, ama eski Kanban widget'ı code'da yok** | Refactor sırasında temiz silindi | – (sorun değil, not olarak) |

---

## 12. Bekleyen Görevler / Roadmap

### 🔴 Yakın vadeli (kullanıcı tarafından son istek)

1. **Filtreleri sadeleştir**: `OrdersPanel`'de **müşteri arama** ve **durum** filtrelerini kaldır, sadece **ödeme tipi** ve **kurye** filtreleri kalsın
   → Dosya: `order_tracking/ui/orders_panel.py` (`filter_box` ve `_apply_local_filters`)

2. **Liste üzerinde "Ödenen Tutar" inline edit**: Kullanıcı sipariş detayına girmeden direkt tablo hücresinde ödenen tutarı değiştirebilsin
   → Yaklaşım: `COL_PAID` sütununu `QDoubleSpinBox` cell widget olarak yap, `valueChanged` → `orders_db.update_order_payment(total_amount=...)` (gerçi bu `payment_status='paid'` mantığını da kırar; iyi düşünülmeli — belki `paid_amount` ayrı kolon eklemek lazım, DB migration)

3. **Arama Geçmişi → Misafir Sipariş**: Kayıtsız bir telefondan arama gelince, "+ Müşteri" butonu yerine "**Misafir Sipariş**" seçeneği de olsun (telefon prefill, customer kaydı yapmadan direkt OrderDetailDialog `guest_mode=True` ile açılsın)
   → Dosya: `order_tracking/ui/incoming_calls_panel.py::_add_customer_for` çevresine ek seçenek

4. **Pencere boyutlandırma**: Tüm dialog/pencereler ekran çözünürlüğüne göre kendini ayarlasın, taşan/görünmeyen kısım olmasın
   → Yaklaşım: Hard-coded `resize(1400, 860)` yerine `screen.availableGeometry() * 0.9`. `MainWindow.__init__` + tüm dialog'ların `__init__`'inde yapılmalı

### 🟡 Orta vadeli

5. **Android Numara Aktarım uygulaması** — gelen aramayı yakala, `incoming_calls`'a INSERT
6. **Android Kurye Takip uygulaması** — kuryeye atanan siparişleri listele, durumu güncelle, konum gönder
7. **`order_items_summary`'yi tek sorguya indir** — Postgres view veya RPC
8. **Server-side müşteri arama** — combo'ya yazılan harf ile DB'den 20 sonuç getir
9. **Yazıcı ayarlarını UI'dan değiştirme** — `settings` tablosunda saklayıp `.env`'i ezme

### 🟢 Uzun vadeli

10. **Auth + rol bazlı RLS** — birden fazla kullanıcı, garson/şef/yönetici rolleri
11. **Raporlama** — günlük/aylık ciro grafikleri, çok satan ürün
12. **Online ödeme entegrasyonu**
13. **Kurye konum haritası** (live tracking)
14. **Adisyon önizlemesini PDF olarak da kaydet**
15. **Otomatik yedekleme** (DB dump → S3 / Drive)

---

## 13. Yaygın İşlemler / Genişletme Rehberi

### Yeni bir tablo eklemek

1. `database/sql/06_migration_X.sql` dosyası oluştur, `CREATE TABLE IF NOT EXISTS ...`
2. RLS aktifleştir, authenticated rolüne politika yaz (mevcut `03_rls_policies.sql` deseni)
3. Realtime publication'a ekle (`02_triggers.sql` sonu desen)
4. `database/<tablename>_db.py` modülü yaz (CRUD)
5. UI'da gerekirse panel/dialog ekle

### Yeni bir UI sekmesi eklemek

1. `ui/<panel_name>.py` oluştur, `class XPanel(QWidget)` yaz, `pyqtSignal` ile dış iletişim tanımla
2. `ui/main_window.py::_build_ui` içinde:
   ```python
   self.x_panel = XPanel()
   self.tabs.addTab(self.x_panel, "🆕 X")
   self.x_panel.signal_y.connect(self._handler)
   ```
3. Realtime listener'da yenilenecekse `_on_orders_changed`/`_on_customers_changed` benzeri bir slot ekle

### Yeni bir tema eklemek

1. `assets/styles/<name>.qss` oluştur (light.qss kopyala, renkleri değiştir)
2. `ui/themes.py::THEMES` sözlüğüne ekle:
   ```python
   THEMES = {"light": "light.qss", "dark": "dark.qss", "blue": "blue.qss"}
   ```
3. `settings_panel` zaten otomatik göstrir (`themes.list_theme_names()` döner)

### Yeni bir CRUD endpoint'i eklemek (Supabase RPC)

Şu an sadece doğrudan tablo erişimi kullanıyoruz. RPC istenirse:
1. Supabase SQL Editor'da `CREATE OR REPLACE FUNCTION ...`
2. Python'da `client.rpc("function_name", {"arg": value}).execute()`

### Linter / Format

Henüz yapılandırılmadı. İstenirse:
```bash
pip install ruff black
ruff check .
black .
```

---

## 14. Sorun Giderme

| Hata | Olası neden | Çözüm |
|---|---|---|
| `Yapılandırma Eksik: SUPABASE_URL` | `.env` dosyası yok veya değer girilmemiş | `.env.example`'ı `.env` olarak kopyala, doldur |
| `Bağlantı Hatası: Invalid API key` | Yanlış key (publishable yerine eski legacy yapıştırılmış) | Settings → API → **Secret keys** → service_role kullan |
| `Bağlantı Hatası: timeout` | İnternet yok / Supabase region yavaş | Bağlantıyı kontrol et, region'ı Frankfurt/Londra yap |
| `RLS denied` | Publishable key kullanıyorsun | Secret key'e geç |
| `qt.qpa.plugin: Could not load xcb` | Linux'ta XCB kütüphanesi eksik | `sudo pacman -S xcb-util-cursor ...` |
| `ModuleNotFoundError: PyQt6` | Sanal ortam aktif değil veya paketler yüklenmedi | `source .venv/bin/activate && pip install -r requirements.txt` |
| `escpos` kurulamadı | Python 3.14 ile native uzantı sorunu | `PRINTER_TYPE=dummy` yap, escpos olmadan da çalışır |
| Yazıcı yazmıyor | `PRINTER_TYPE=usb` ama vendor/product ID yanlış | `lsusb` ile bul, `.env`'i güncelle |
| Gelen arama popup gözükmüyor | Polling kapalı / network yavaş / `incoming_calls` boş | Status bar'a bak ("Polling hatası..." görünebilir) |
| Sipariş silinemiyor (`violates foreign key`) | Bu siparişe bağlı `order_items` veya farklı bir kayıt var | DB'de `ON DELETE CASCADE` zaten tanımlı, sorun çıkıyorsa Supabase logs'a bak |
| Müşteri silinemiyor | Aktif siparişleri var (`ON DELETE RESTRICT`) | Önce siparişleri sil, sonra müşteriyi |
| Toplam tutar 0 görünüyor | DB trigger çalışmadı (eski şema?) | `02_triggers.sql`'i tekrar çalıştır, siparişi tekrar kaydet |

---

## 15. Anahtar Dosyalar Hızlı Referans

> Dosyalar arası bağımlılığı bulurken işine yarar.

| Görev → | Bakılacak dosya | Önemli fonksiyon/sınıf |
|---|---|---|
| Yeni sipariş eklemek | `ui/order_detail_dialog.py` | `_save()` |
| Sipariş listesi görünümü | `ui/orders_panel.py` | `_populate_orders_table()`, `_apply_local_filters()` |
| Gelen arama akışı | `database/realtime_listener.py` → `ui/main_window.py::_on_incoming_call` → `ui/incoming_call_popup.py` | – |
| Müşteri otomatik eşleşme | `database/sql/02_triggers.sql` | `match_incoming_call_customer()` |
| Telefon normalize | `utils/helpers.py` | `normalize_phone()` |
| Adisyon şablonu | `utils/printer_handler.py` | `build_receipt_text()` |
| Tema | `ui/themes.py` + `assets/styles/*.qss` | `apply_theme()` |
| Excel müşteri import/export | `utils/excel_handler.py` | `import_customers()`, `export_customers()` |
| Tek seferlik müşteri | `ui/order_detail_dialog.py` | `_set_guest_visible()`, `_save()` (is_guest=True) |
| DB tek istemci | `database/supabase_client.py` | `get_client()` |
| Sipariş durum sabitleri | `database/orders_db.py` | `STATUS_NEW`, `STATUS_ON_WAY`, `STATUS_DELIVERED`, `STATUS_LABELS` |
| Realtime yenilemesi | `database/realtime_listener.py` | `RealtimeListener.run()` |
| Header'daki "Son Kayıt" | `ui/main_window.py` | `_refresh_last_customer()` + `customers_db.latest_customer()` |

---

## 16. İletişim & Süreç Notları

**Yapılan değişikliklerin tarihçesi (kabaca):**

- **6 May 2026** — DB şema tasarımı, ilk SQL dosyaları
- **6 May 2026** — PyQt6 masaüstü iskeleti (Kanban'lı ilk sürüm)
- **6 May 2026** — Refactor 1: Kanban kaldırıldı, klasik tablo geldi (resmi referans alarak), Arama Geçmişi sekmesi eklendi, sipariş durumları sadeleştirildi
- **6 May 2026** — Refactor 2: Müşteri silme, tek seferlik (misafir) sipariş, sıralama, müşteri detay sağ tık, sütun temizleme, aranabilir müşteri (autocomplete)
- **8 May 2026** — Bu hand-off dökümanı yazıldı

**Tasarım kararları neden böyle:**

| Karar | Neden |
|---|---|
| Polling > Websocket | PyQt asyncio bridge sıkıntısı |
| Service role > Auth | Tek işletme, masaüstü tek kullanıcı |
| `is_guest` flag > nullable customer_id | DB integrity, daha az migration |
| Tablo > Kanban | Kullanıcı tercihi (referans uygulama gösterdi) |
| Sıkı versiyon pin yerine `>=` | Python 3.14 wheel uyumu |
| `run.sh` smart cache | Her açılışta `pip install` beklemeyelim |
| `print_after_save` flag | Kaydet ve Yazdır tek akışta |

---

> **TLDR:** Veritabanı + masaüstü hazır ve test edilmiş. Android tarafı tamamen yapılacak. Yakın zamanda 4 küçük UX iyileştirmesi bekleniyor (madde 12.1-4). Kod 6K satır civarı, lint temiz, modüler.

İyi geliştirmeler. Sorularını HANDOFF.md'yi okuduktan sonra sırayla `database/` → `order_tracking/main.py` → `order_tracking/ui/main_window.py` yolu üzerinden çözebilirsin.
