-- =====================================================
-- 09 - Telefon eşleştirme düzeltmesi (incoming_calls)
-- =====================================================
-- Amaç:
--   1. Trigger gerçek müşteri (is_guest = false) tercihli eşleştirsin.
--   2. customer_id IS NULL kalmış eski incoming_calls kayıtlarını,
--      kayıtlı müşterilerle son 10 hane bazında geri-doldur (backfill).
-- =====================================================

-- A) Eşleştirme trigger fonksiyonunu güncelle
CREATE OR REPLACE FUNCTION public.match_incoming_call_customer()
RETURNS TRIGGER AS $$
DECLARE
    v_customer_id UUID;
    v_normalized  TEXT;
BEGIN
    -- Açıkça customer_id verilmişse dokunma
    IF NEW.customer_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    v_normalized := public.normalize_phone(NEW.phone_number);

    IF v_normalized IS NULL OR length(v_normalized) = 0 THEN
        RETURN NEW;
    END IF;

    -- Önce gerçek müşterilerle dene (misafir kayıtlarını yok say)
    SELECT id INTO v_customer_id
    FROM public.customers
    WHERE public.normalize_phone(phone) = v_normalized
      AND (is_guest IS NULL OR is_guest = false)
    ORDER BY created_at ASC
    LIMIT 1;

    -- Gerçek müşteri yoksa misafir kayıtları da dene
    IF v_customer_id IS NULL THEN
        SELECT id INTO v_customer_id
        FROM public.customers
        WHERE public.normalize_phone(phone) = v_normalized
        ORDER BY created_at ASC
        LIMIT 1;
    END IF;

    IF v_customer_id IS NOT NULL THEN
        NEW.customer_id := v_customer_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger'ı yeniden bağla (idempotent)
DROP TRIGGER IF EXISTS trg_incoming_calls_match ON public.incoming_calls;
CREATE TRIGGER trg_incoming_calls_match
    BEFORE INSERT ON public.incoming_calls
    FOR EACH ROW
    EXECUTE FUNCTION public.match_incoming_call_customer();

-- B) Backfill: customer_id IS NULL olan kayıtları güncelle
--    Önce gerçek müşterileri eşleştir.
WITH match_real AS (
    SELECT DISTINCT ON (ic.id) ic.id AS call_id, c.id AS customer_id
    FROM public.incoming_calls ic
    JOIN public.customers c
      ON public.normalize_phone(c.phone) = public.normalize_phone(ic.phone_number)
    WHERE ic.customer_id IS NULL
      AND public.normalize_phone(ic.phone_number) <> ''
      AND (c.is_guest IS NULL OR c.is_guest = false)
    ORDER BY ic.id, c.created_at ASC
)
UPDATE public.incoming_calls ic
SET customer_id = m.customer_id
FROM match_real m
WHERE ic.id = m.call_id;

-- Sonra hâlâ NULL kalanları misafir kayıtlarla eşleştir
WITH match_guest AS (
    SELECT DISTINCT ON (ic.id) ic.id AS call_id, c.id AS customer_id
    FROM public.incoming_calls ic
    JOIN public.customers c
      ON public.normalize_phone(c.phone) = public.normalize_phone(ic.phone_number)
    WHERE ic.customer_id IS NULL
      AND public.normalize_phone(ic.phone_number) <> ''
    ORDER BY ic.id, c.created_at ASC
)
UPDATE public.incoming_calls ic
SET customer_id = m.customer_id
FROM match_guest m
WHERE ic.id = m.call_id;

-- Bilgi: kaç kayıt güncellendi diye görmek için
-- SELECT COUNT(*) FROM public.incoming_calls WHERE customer_id IS NOT NULL;
