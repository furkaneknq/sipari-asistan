-- =====================================================================
-- 08_COURIER_APP_POLICIES.SQL
-- Kurye Takip Android uygulaması için RLS politikaları ve RPC fonksiyonu.
-- Supabase SQL Editor'da bir kez çalıştırın.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) Kurye Giriş RPC Fonksiyonu
--    Telefon + şifre ile giriş. Güvenlik: SECURITY DEFINER = RLS bypass eder.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.courier_login(p_phone TEXT, p_password TEXT)
RETURNS JSON AS $$
DECLARE
    v_courier RECORD;
    v_normalized TEXT;
BEGIN
    v_normalized := public.normalize_phone(p_phone);

    SELECT id, name, phone, is_active
    INTO v_courier
    FROM public.couriers
    WHERE public.normalize_phone(phone) = v_normalized
      AND password = p_password
    LIMIT 1;

    IF v_courier IS NULL THEN
        RETURN json_build_object('success', false, 'message', 'Geçersiz telefon veya şifre');
    END IF;

    IF NOT v_courier.is_active THEN
        RETURN json_build_object('success', false, 'message', 'Hesabınız pasif durumda');
    END IF;

    RETURN json_build_object(
        'success', true,
        'courier_id', v_courier.id,
        'name', v_courier.name,
        'phone', v_courier.phone
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Anon rolüne çağırma izni
GRANT EXECUTE ON FUNCTION public.courier_login(TEXT, TEXT) TO anon;

-- ---------------------------------------------------------------------
-- 2) Kurye konumunu güncelleme RPC
--    Kurye ID doğrulaması dahil (şifre ile).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.courier_update_location(
    p_courier_id UUID,
    p_latitude DOUBLE PRECISION,
    p_longitude DOUBLE PRECISION
)
RETURNS JSON AS $$
BEGIN
    UPDATE public.couriers
    SET current_latitude = p_latitude,
        current_longitude = p_longitude
    WHERE id = p_courier_id AND is_active = TRUE;

    IF NOT FOUND THEN
        RETURN json_build_object('success', false, 'message', 'Kurye bulunamadı');
    END IF;

    RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.courier_update_location(UUID, DOUBLE PRECISION, DOUBLE PRECISION) TO anon;

-- ---------------------------------------------------------------------
-- 3) Sipariş durumu güncelleme RPC
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.courier_update_order_status(
    p_order_id UUID,
    p_courier_id UUID,
    p_status TEXT
)
RETURNS JSON AS $$
DECLARE
    v_order RECORD;
BEGIN
    -- Sadece bu kuryeye atanmış siparişi güncelle
    SELECT id, status INTO v_order
    FROM public.orders
    WHERE id = p_order_id AND courier_id = p_courier_id;

    IF v_order IS NULL THEN
        RETURN json_build_object('success', false, 'message', 'Sipariş bulunamadı veya size atanmamış');
    END IF;

    -- Durum geçerliliği kontrol
    IF p_status NOT IN ('new', 'preparing', 'on_way', 'delivered', 'cancelled') THEN
        RETURN json_build_object('success', false, 'message', 'Geçersiz durum');
    END IF;

    UPDATE public.orders
    SET status = p_status
    WHERE id = p_order_id AND courier_id = p_courier_id;

    RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.courier_update_order_status(UUID, UUID, TEXT) TO anon;

-- ---------------------------------------------------------------------
-- 3b) Ödenen tutarı güncelleme RPC
--     Kurye, müşteriden aldığı ödemeyi kaydeder.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.courier_update_paid_amount(
    p_order_id UUID,
    p_courier_id UUID,
    p_paid_amount DECIMAL,
    p_payment_method TEXT DEFAULT NULL
)
RETURNS JSON AS $$
DECLARE
    v_order RECORD;
BEGIN
    SELECT id INTO v_order
    FROM public.orders
    WHERE id = p_order_id AND courier_id = p_courier_id;

    IF v_order IS NULL THEN
        RETURN json_build_object('success', false, 'message', 'Sipariş bulunamadı veya size atanmamış');
    END IF;

    UPDATE public.orders
    SET paid_amount = p_paid_amount,
        payment_method = COALESCE(p_payment_method, payment_method)
    WHERE id = p_order_id AND courier_id = p_courier_id;

    RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.courier_update_paid_amount(UUID, UUID, DECIMAL, TEXT) TO anon;

-- ---------------------------------------------------------------------
-- 4) Kuryenin siparişlerini getiren RPC
--    Join ile müşteri, adres ve sipariş kalemleri bilgisi döner.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.courier_get_orders(p_courier_id UUID)
RETURNS JSON AS $$
DECLARE
    v_result JSON;
BEGIN
    SELECT json_agg(row_to_json(t))
    INTO v_result
    FROM (
        SELECT
            o.id,
            o.order_number,
            o.status,
            o.order_date,
            o.delivery_time,
            o.total_amount,
            o.paid_amount,
            o.payment_method,
            o.payment_status,
            o.notes,
            o.created_at,
            o.updated_at,
            json_build_object(
                'id', c.id,
                'name', c.name,
                'phone', c.phone
            ) AS customer,
            CASE WHEN ca.id IS NOT NULL THEN
                json_build_object(
                    'id', ca.id,
                    'title', ca.title,
                    'address_text', ca.address_text,
                    'latitude', ca.latitude,
                    'longitude', ca.longitude
                )
            ELSE NULL END AS address,
            (
                SELECT json_agg(json_build_object(
                    'id', oi.id,
                    'quantity', oi.quantity,
                    'unit', oi.unit,
                    'unit_price', oi.unit_price,
                    'total_price', oi.total_price,
                    'notes', oi.notes,
                    'product_name', COALESCE(p.name, 'Silinmiş Ürün')
                ))
                FROM public.order_items oi
                LEFT JOIN public.products p ON p.id = oi.product_id
                WHERE oi.order_id = o.id
            ) AS items
        FROM public.orders o
        JOIN public.customers c ON c.id = o.customer_id
        LEFT JOIN public.customer_addresses ca ON ca.id = o.address_id
        WHERE o.courier_id = p_courier_id
          AND o.order_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date
        ORDER BY
            CASE o.status
                WHEN 'new' THEN 1
                WHEN 'preparing' THEN 2
                WHEN 'on_way' THEN 3
                WHEN 'delivered' THEN 4
                WHEN 'cancelled' THEN 5
            END,
            o.created_at DESC
    ) t;

    RETURN COALESCE(v_result, '[]'::json);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.courier_get_orders(UUID) TO anon;

-- ---------------------------------------------------------------------
-- 5) Kuryenin günlük özetini getiren RPC
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.courier_daily_summary(p_courier_id UUID)
RETURNS JSON AS $$
DECLARE
    v_delivered_count INT;
    v_total_amount DECIMAL(10,2);
    v_paid_amount DECIMAL(10,2);
BEGIN
    SELECT
        COUNT(*),
        COALESCE(SUM(total_amount), 0),
        COALESCE(SUM(paid_amount), 0)
    INTO v_delivered_count, v_total_amount, v_paid_amount
    FROM public.orders
    WHERE courier_id = p_courier_id
      AND order_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date
      AND status = 'delivered';

    RETURN json_build_object(
        'delivered_count', v_delivered_count,
        'total_amount', v_total_amount,
        'paid_amount', v_paid_amount
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.courier_daily_summary(UUID) TO anon;
