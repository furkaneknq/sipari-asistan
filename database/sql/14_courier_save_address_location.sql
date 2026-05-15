-- =====================================================================
-- 14_COURIER_SAVE_ADDRESS_LOCATION.SQL
-- Kurye uygulamasından müşteri adresine anlık konum kaydetme.
-- Supabase SQL Editor'da bir kez çalıştırın.
-- =====================================================================

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
    -- Adresin, bu kuryeye atanmış bir siparişe ait olduğunu doğrula
    SELECT ca.id INTO v_addr
    FROM public.customer_addresses ca
    JOIN public.orders o ON o.address_id = ca.id
    WHERE ca.id = p_address_id
      AND o.courier_id = p_courier_id
      AND o.order_date = CURRENT_DATE
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
