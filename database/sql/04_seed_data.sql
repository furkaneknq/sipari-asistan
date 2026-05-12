-- =====================================================================
-- 04_SEED_DATA.SQL
-- Örnek veriler (ayarlar, temalar, kategoriler, ürünler, müşteriler vb.)
-- 03_rls_policies.sql çalıştırıldıktan SONRA çalıştırın
-- =====================================================================

-- ---------------------------------------------------------------------
-- SETTINGS - Uygulama Ayarları
-- ---------------------------------------------------------------------
INSERT INTO public.settings (key, value, description) VALUES
    ('company_name',       'Sipariş Takip Ltd.',      'İşletme adı'),
    ('company_phone',      '+90 555 000 00 00',       'İşletme telefonu'),
    ('company_address',    '',                        'İşletme adresi'),
    ('printer_name',       '',                        'Adisyon yazıcı adı'),
    ('printer_paper_size', '80mm',                    'Yazıcı kağıt boyutu (58mm/80mm)'),
    ('currency',           'TRY',                     'Para birimi'),
    ('default_unit',       'adet',                    'Varsayılan ürün birimi'),
    ('order_prefix',       'SP',                      'Sipariş numarası ön eki')
ON CONFLICT (key) DO NOTHING;

-- ---------------------------------------------------------------------
-- THEMES - Temalar
-- ---------------------------------------------------------------------
INSERT INTO public.themes (name, primary_color, secondary_color, background_color, text_color, is_active) VALUES
    ('Açık Tema',  '#1976D2', '#FFC107', '#FFFFFF', '#212121', TRUE),
    ('Koyu Tema',  '#2196F3', '#FFB300', '#121212', '#FAFAFA', FALSE),
    ('Yeşil Tema', '#2E7D32', '#FB8C00', '#F1F8E9', '#1B5E20', FALSE)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- CATEGORIES - Kategoriler
-- ---------------------------------------------------------------------
INSERT INTO public.categories (name, sort_order, color) VALUES
    ('İçecekler',       10, '#03A9F4'),
    ('Yiyecekler',      20, '#FF9800'),
    ('Tatlılar',        30, '#E91E63'),
    ('Atıştırmalıklar', 40, '#9C27B0'),
    ('Diğer',          100, '#607D8B')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- PRODUCTS - Ürünler (kategorilere bağlı)
-- Kategori adından id bulup ürünleri ekliyoruz
-- ---------------------------------------------------------------------
WITH cat AS (
    SELECT id, name FROM public.categories
)
INSERT INTO public.products (category_id, name, price, unit, sort_order)
SELECT cat.id, v.name, v.price, v.unit, v.sort_order
FROM (VALUES
    ('İçecekler',       'Su (0.5 lt)',         10.00,  'adet', 10),
    ('İçecekler',       'Ayran',               15.00,  'adet', 20),
    ('İçecekler',       'Kola (33cl)',         25.00,  'adet', 30),
    ('İçecekler',       'Çay',                  8.00,  'adet', 40),
    ('Yiyecekler',      'Pide',               120.00,  'adet', 10),
    ('Yiyecekler',      'Lahmacun',            60.00,  'adet', 20),
    ('Yiyecekler',      'Döner Porsiyon',     180.00,  'adet', 30),
    ('Yiyecekler',      'Salata',              80.00,  'adet', 40),
    ('Tatlılar',        'Künefe',             140.00,  'adet', 10),
    ('Tatlılar',        'Sütlaç',              70.00,  'adet', 20),
    ('Atıştırmalıklar', 'Patates Kızartması',  55.00,  'adet', 10),
    ('Atıştırmalıklar', 'Soğan Halkası',       65.00,  'adet', 20)
) AS v(category_name, name, price, unit, sort_order)
JOIN cat ON cat.name = v.category_name
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- COURIERS - Örnek Kuryeler
-- ---------------------------------------------------------------------
INSERT INTO public.couriers (name, phone, password, is_active) VALUES
    ('Ahmet Yılmaz', '05551112233', '1234', TRUE),
    ('Mehmet Demir', '05554445566', '1234', TRUE)
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- CUSTOMERS - Örnek Müşteriler
-- ---------------------------------------------------------------------
INSERT INTO public.customers (name, phone, email, notes) VALUES
    ('Ali Veli',    '05321234567', 'ali@example.com',   'Kapı zilini çalmasın'),
    ('Ayşe Fatma',  '05339876543', NULL,                 'Acılı sevmiyor'),
    ('Hasan Hüseyin','05447778899', 'hasan@example.com', NULL)
ON CONFLICT (phone) DO NOTHING;

-- Adres örnekleri (telefon üzerinden müşteri id'sini bularak)
INSERT INTO public.customer_addresses (customer_id, title, address_text, latitude, longitude, is_default)
SELECT c.id, v.title, v.address_text, v.latitude, v.longitude, v.is_default
FROM (VALUES
    ('05321234567', 'Ev', 'Atatürk Cad. No:10 D:5 Kadıköy/İstanbul', 40.9923, 29.0270, TRUE),
    ('05321234567', 'İş', 'Bağdat Cad. No:200 K:3 Kadıköy/İstanbul', 40.9700, 29.0500, FALSE),
    ('05339876543', 'Ev', 'Cumhuriyet Mah. 5. Sk. No:3 Şişli/İstanbul', 41.0600, 28.9870, TRUE),
    ('05447778899', 'Ev', 'Yeni Mah. 12. Cd. No:7 Beşiktaş/İstanbul',   41.0420, 29.0090, TRUE)
) AS v(phone, title, address_text, latitude, longitude, is_default)
JOIN public.customers c ON c.phone = v.phone
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------
-- PHONES - Bağlı örnek telefonlar
-- ---------------------------------------------------------------------
INSERT INTO public.phones (device_name, device_id, is_active) VALUES
    ('Kasa Telefonu',  'device-001', TRUE),
    ('Mutfak Telefonu','device-002', TRUE)
ON CONFLICT (device_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- ÖRNEK SİPARİŞ (test için)
-- Müşteri Ali Veli, varsayılan adresi, 2 ürün kalemi
-- ---------------------------------------------------------------------
DO $$
DECLARE
    v_customer_id UUID;
    v_address_id  UUID;
    v_order_id    UUID;
    v_pid_pide    UUID;
    v_pid_ayran   UUID;
BEGIN
    SELECT id INTO v_customer_id FROM public.customers WHERE phone = '05321234567';
    IF v_customer_id IS NULL THEN
        RETURN;
    END IF;

    SELECT id INTO v_address_id
    FROM public.customer_addresses
    WHERE customer_id = v_customer_id AND is_default = TRUE
    LIMIT 1;

    SELECT id INTO v_pid_pide  FROM public.products WHERE name = 'Pide'  LIMIT 1;
    SELECT id INTO v_pid_ayran FROM public.products WHERE name = 'Ayran' LIMIT 1;

    INSERT INTO public.orders (customer_id, address_id, status, payment_method, payment_status, notes)
    VALUES (v_customer_id, v_address_id, 'new', 'cash', 'pending', 'Ekstra peynirli olsun')
    RETURNING id INTO v_order_id;

    IF v_pid_pide IS NOT NULL THEN
        INSERT INTO public.order_items (order_id, product_id, quantity, unit, unit_price)
        VALUES (v_order_id, v_pid_pide, 2, 'adet', 120.00);
    END IF;

    IF v_pid_ayran IS NOT NULL THEN
        INSERT INTO public.order_items (order_id, product_id, quantity, unit, unit_price)
        VALUES (v_order_id, v_pid_ayran, 2, 'adet', 15.00);
    END IF;
END $$;
