-- =====================================================================
-- 15_FIX_TIMEZONE_RPC.SQL
-- Tüm CURRENT_DATE kullanımlarını Türkiye saatine düzelt.
-- Supabase UTC kullandığı için gece 00:00-03:00 arasında yanlış gün
-- hesaplanıyordu.
-- Supabase SQL Editor'da BİR KEZ çalıştırın.
-- =====================================================================

-- orders tablosundaki DEFAULT: sipariş oluşturulurken doğru tarih atsın
ALTER TABLE public.orders
    ALTER COLUMN order_date SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date;

-- courier_get_orders: Günün siparişlerini getir (Türkiye saati)
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

-- courier_save_address_location: Adrese konum kaydet (Türkiye saati)
CREATE OR REPLACE FUNCTION public.courier_save_address_location(
    p_address_id UUID,
    p_courier_id UUID,
    p_latitude DOUBLE PRECISION,
    p_longitude DOUBLE PRECISION
)
RETURNS JSON AS $$
DECLARE
    v_addr RECORD;
BEGIN
    SELECT ca.id INTO v_addr
    FROM public.customer_addresses ca
    JOIN public.orders o ON o.address_id = ca.id
    WHERE ca.id = p_address_id
      AND o.courier_id = p_courier_id
      AND o.order_date = (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date
    LIMIT 1;

    IF v_addr IS NULL THEN
        RETURN json_build_object('success', false, 'message', 'Adres bulunamadı veya yetkiniz yok');
    END IF;

    UPDATE public.customer_addresses
    SET latitude = p_latitude,
        longitude = p_longitude
    WHERE id = p_address_id;

    RETURN json_build_object('success', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.courier_save_address_location(UUID, UUID, DOUBLE PRECISION, DOUBLE PRECISION) TO anon;

-- courier_daily_summary: Günlük özet (Türkiye saati)
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
