-- =====================================================================
-- 12_PHONES_ANON_UPSERT.SQL
-- Android uygulamasının anon key ile phones tablosuna cihaz kaydı
-- yapabilmesi (upsert) için RLS policy.
-- =====================================================================

-- Mevcut policy varsa düşür (idempotent)
DROP POLICY IF EXISTS "phones_anon_select" ON public.phones;
DROP POLICY IF EXISTS "phones_anon_insert" ON public.phones;
DROP POLICY IF EXISTS "phones_anon_update" ON public.phones;

-- SELECT: PostgREST upsert sırasında mevcut satırı kontrol etmesi için gerekli
CREATE POLICY "phones_anon_select"
    ON public.phones
    FOR SELECT
    TO anon
    USING (true);

CREATE POLICY "phones_anon_insert"
    ON public.phones
    FOR INSERT
    TO anon
    WITH CHECK (true);

CREATE POLICY "phones_anon_update"
    ON public.phones
    FOR UPDATE
    TO anon
    USING (true)
    WITH CHECK (true);

COMMENT ON POLICY "phones_anon_select" ON public.phones IS
    'Upsert için anon SELECT izni.';
COMMENT ON POLICY "phones_anon_insert" ON public.phones IS
    'Mobil uygulamanın anon key ile cihaz kaydı eklemesine izin verir.';
COMMENT ON POLICY "phones_anon_update" ON public.phones IS
    'Mobil uygulamanın anon key ile cihaz bilgisini güncellemesine izin verir (upsert).';
