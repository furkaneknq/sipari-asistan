-- =====================================================================
-- 02_TRIGGERS.SQL
-- Trigger'lar ve fonksiyonlar
-- 01_tables.sql çalıştırıldıktan SONRA çalıştırın
-- =====================================================================

-- ---------------------------------------------------------------------
-- A) updated_at otomatik güncelleme fonksiyonu
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- customers tablosu için
DROP TRIGGER IF EXISTS trg_customers_updated_at ON public.customers;
CREATE TRIGGER trg_customers_updated_at
    BEFORE UPDATE ON public.customers
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- orders tablosu için
DROP TRIGGER IF EXISTS trg_orders_updated_at ON public.orders;
CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON public.orders
    FOR EACH ROW
    EXECUTE FUNCTION public.set_updated_at();

-- ---------------------------------------------------------------------
-- B) Telefon numarası normalleştirme yardımcı fonksiyonu
-- (Boşluk, tire, parantez vs. temizler; sadece son 10 haneyi alır)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.normalize_phone(p_phone TEXT)
RETURNS TEXT AS $$
DECLARE
    v_clean TEXT;
BEGIN
    IF p_phone IS NULL THEN
        RETURN NULL;
    END IF;
    v_clean := regexp_replace(p_phone, '[^0-9]', '', 'g');
    IF length(v_clean) >= 10 THEN
        v_clean := right(v_clean, 10);
    END IF;
    RETURN v_clean;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ---------------------------------------------------------------------
-- C) Gelen aramaları otomatik müşteri ile eşleştiren trigger
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.match_incoming_call_customer()
RETURNS TRIGGER AS $$
DECLARE
    v_customer_id UUID;
    v_normalized  TEXT;
BEGIN
    -- Eğer customer_id zaten verilmişse dokunma
    IF NEW.customer_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    v_normalized := public.normalize_phone(NEW.phone_number);

    IF v_normalized IS NULL OR length(v_normalized) = 0 THEN
        RETURN NEW;
    END IF;

    -- Müşteri tablosunda son 10 haneye göre eşleştirme yap
    SELECT id INTO v_customer_id
    FROM public.customers
    WHERE public.normalize_phone(phone) = v_normalized
    LIMIT 1;

    IF v_customer_id IS NOT NULL THEN
        NEW.customer_id := v_customer_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_incoming_calls_match ON public.incoming_calls;
CREATE TRIGGER trg_incoming_calls_match
    BEFORE INSERT ON public.incoming_calls
    FOR EACH ROW
    EXECUTE FUNCTION public.match_incoming_call_customer();

-- ---------------------------------------------------------------------
-- D) Order_items eklenince/güncellenince total_price otomatik hesapla
--    ve orders.total_amount güncelle (kullanışlı bonus)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.calc_order_item_total()
RETURNS TRIGGER AS $$
BEGIN
    NEW.total_price := COALESCE(NEW.quantity, 0) * COALESCE(NEW.unit_price, 0);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_order_items_calc ON public.order_items;
CREATE TRIGGER trg_order_items_calc
    BEFORE INSERT OR UPDATE ON public.order_items
    FOR EACH ROW
    EXECUTE FUNCTION public.calc_order_item_total();

CREATE OR REPLACE FUNCTION public.refresh_order_total()
RETURNS TRIGGER AS $$
DECLARE
    v_order_id UUID;
BEGIN
    v_order_id := COALESCE(NEW.order_id, OLD.order_id);

    UPDATE public.orders
    SET total_amount = COALESCE((
        SELECT SUM(total_price)
        FROM public.order_items
        WHERE order_id = v_order_id
    ), 0)
    WHERE id = v_order_id;

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_order_items_refresh_total ON public.order_items;
CREATE TRIGGER trg_order_items_refresh_total
    AFTER INSERT OR UPDATE OR DELETE ON public.order_items
    FOR EACH ROW
    EXECUTE FUNCTION public.refresh_order_total();

-- ---------------------------------------------------------------------
-- E) Real-time subscription: tüm önemli tabloları publication'a ekle
-- ---------------------------------------------------------------------
DO $$
DECLARE
    t TEXT;
    tables TEXT[] := ARRAY[
        'customers',
        'customer_addresses',
        'categories',
        'products',
        'couriers',
        'orders',
        'order_items',
        'phones',
        'incoming_calls',
        'settings',
        'themes'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        BEGIN
            EXECUTE format(
                'ALTER PUBLICATION supabase_realtime ADD TABLE public.%I;', t
            );
        EXCEPTION WHEN duplicate_object THEN
            -- Zaten eklenmişse görmezden gel
            NULL;
        WHEN undefined_object THEN
            -- supabase_realtime publication yoksa görmezden gel
            NULL;
        END;
    END LOOP;
END $$;
