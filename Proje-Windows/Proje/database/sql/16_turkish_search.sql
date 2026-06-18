-- =====================================================================
-- 16_TURKISH_SEARCH.SQL
-- Türkçe karakterlere uyumlu case-insensitive arama fonksiyonu.
-- Supabase SQL Editor'da bir kez çalıştırın.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) turkish_normalize: Türkçe noktalı/noktasız harf farkını yok sayar.
--    i, ı, İ, I → hepsi 'i' olur
--    ö, Ö → 'o'   ü, Ü → 'u'   ç, Ç → 'c'   ş, Ş → 's'   ğ, Ğ → 'g'
--    Böylece kullanıcı hangi varyantı yazarsa yazsın eşleşir.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.turkish_normalize(input TEXT)
RETURNS TEXT AS $$
DECLARE
    result TEXT;
BEGIN
    result := input;
    -- Büyük Türkçe harfleri ASCII karşılıklarına çevir
    result := replace(result, 'İ', 'i');
    result := replace(result, 'I', 'i');
    result := replace(result, 'Ş', 's');
    result := replace(result, 'Ç', 'c');
    result := replace(result, 'Ğ', 'g');
    result := replace(result, 'Ö', 'o');
    result := replace(result, 'Ü', 'u');
    -- Küçük Türkçe harfleri ASCII karşılıklarına çevir
    result := replace(result, 'ı', 'i');
    result := replace(result, 'ş', 's');
    result := replace(result, 'ç', 'c');
    result := replace(result, 'ğ', 'g');
    result := replace(result, 'ö', 'o');
    result := replace(result, 'ü', 'u');
    -- Geri kalan büyük harfleri küçült (A-Z → a-z)
    result := lower(result);
    RETURN result;
END;
$$ LANGUAGE plpgsql IMMUTABLE STRICT;

-- ---------------------------------------------------------------------
-- 2) Müşteri arama RPC — Türkçe uyumlu, case-insensitive.
--    Desktop uygulamasından çağrılır.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.search_customers(
    p_search TEXT,
    p_limit INT DEFAULT 50,
    p_include_guests BOOL DEFAULT FALSE
)
RETURNS SETOF customers AS $$
DECLARE
    v_search TEXT;
BEGIN
    v_search := '%' || public.turkish_normalize(p_search) || '%';

    RETURN QUERY
    SELECT *
    FROM public.customers c
    WHERE (p_include_guests OR c.is_guest = false)
      AND (
          public.turkish_normalize(c.name) LIKE v_search
          OR c.phone LIKE '%' || p_search || '%'
      )
    ORDER BY c.name
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION public.search_customers(TEXT, INT, BOOL) TO anon;
