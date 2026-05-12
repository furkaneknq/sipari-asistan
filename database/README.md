# Sipariş Takip Sistemi - Veritabanı

Supabase PostgreSQL veritabanı için SQL dosyaları.

## Çalıştırma Sırası

Supabase Dashboard üzerinde:

1. Sol menüden **SQL Editor**'ü aç
2. **+ New query** ile yeni bir sekme oluştur
3. Aşağıdaki dosyaları **sırasıyla** kopyala-yapıştır ve **Run** ile çalıştır:

| Sıra | Dosya                       | Açıklama                                            |
| ---- | --------------------------- | --------------------------------------------------- |
| 1    | `sql/01_tables.sql`         | Tabloları, sequence'leri ve index'leri oluşturur    |
| 2    | `sql/02_triggers.sql`       | Trigger'ları, fonksiyonları ve realtime publication |
| 3    | `sql/03_rls_policies.sql`   | Row Level Security ve politikaları kurar            |
| 4    | `sql/04_seed_data.sql`      | Örnek veriler (kategori, ürün, müşteri, vb.)        |

> Sıra önemli: Tablolar olmadan trigger, trigger olmadan RLS, RLS olmadan seed çalışmaz.

## Tablolar

| Tablo                | Açıklama                                                      |
| -------------------- | ------------------------------------------------------------- |
| `customers`          | Müşteriler (telefon unique)                                   |
| `customer_addresses` | Müşteri adresleri (1 müşteri → N adres)                       |
| `categories`         | Ürün kategorileri                                             |
| `products`           | Ürünler (1 kategori → N ürün)                                 |
| `couriers`           | Kuryeler (anlık konum + giriş şifresi)                        |
| `orders`             | Siparişler (`order_number` 1001'den başlar, otomatik artar)   |
| `order_items`        | Sipariş kalemleri (toplam tutar otomatik hesaplanır)          |
| `phones`             | Bağlı Android telefonlar (numara aktarım için)                |
| `incoming_calls`     | Gelen aramalar (insert anında müşteri ile otomatik eşleşir)   |
| `settings`           | Anahtar/değer uygulama ayarları                               |
| `themes`             | UI temaları                                                   |

## Önemli Davranışlar

- **`order_number`** otomatik 1001, 1002, 1003 ... şeklinde ilerler.
- **`updated_at`** alanları `customers` ve `orders` tablolarında her UPDATE'de otomatik yenilenir.
- **`order_items`** eklenince/güncellenince:
  - `total_price` = `quantity * unit_price` otomatik hesaplanır.
  - Bağlı `orders.total_amount` otomatik güncellenir.
- **`incoming_calls`** tablosuna her INSERT'te:
  - Telefon numarası temizlenir (sadece son 10 hane).
  - `customers` tablosunda eşleşen kayıt varsa `customer_id` otomatik atanır.
- **Realtime**: Tüm tablolar `supabase_realtime` publication'ına eklenir → istemciler değişiklikleri canlı dinleyebilir.

## RLS Notu

`03_rls_policies.sql` tüm tablolara RLS açar ve **authenticated** rolüne tam erişim verir.
- Masaüstü uygulama Supabase'e Auth ile giriş yaptığında çalışır.
- Anon (anahtarsız) erişim **kapalıdır**.
- Üretime geçerken rol/cihaz bazlı daha sıkı politikalar yazılmalıdır.

## Sıfırlamak İstersen

> ⚠️ DİKKAT: Tüm verileri silen yıkıcı bir komuttur. Sadece geliştirme ortamında kullan.

```sql
DROP TABLE IF EXISTS public.order_items, public.orders, public.incoming_calls,
                     public.phones, public.customer_addresses, public.customers,
                     public.products, public.categories, public.couriers,
                     public.settings, public.themes CASCADE;
DROP SEQUENCE IF EXISTS public.orders_order_number_seq;
DROP FUNCTION IF EXISTS public.set_updated_at,
                        public.normalize_phone,
                        public.match_incoming_call_customer,
                        public.calc_order_item_total,
                        public.refresh_order_total CASCADE;
```
