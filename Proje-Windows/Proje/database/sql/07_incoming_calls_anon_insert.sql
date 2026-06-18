-- =====================================================================
-- 07_INCOMING_CALLS_ANON_INSERT.SQL
-- Android "Arama Aktarım" uygulamasının publishable (anon) key ile
-- incoming_calls tablosuna kayıt INSERT'leyebilmesi için minimum yetki.
--
-- Güvenlik notu:
--   - anon rolüne sadece INSERT verilir (SELECT/UPDATE/DELETE yok).
--   - Yani APK ele geçse bile geçmiş aramalar okunamaz veya silinemez.
--   - Masaüstü uygulaması service_role key ile her şeyi yapmaya devam eder.
--
-- Supabase SQL Editor'da bir kez çalıştır.
-- =====================================================================

-- Mevcut anon insert policy'si varsa düşür (idempotent)
DROP POLICY IF EXISTS "incoming_calls_anon_insert" ON public.incoming_calls;

CREATE POLICY "incoming_calls_anon_insert"
    ON public.incoming_calls
    FOR INSERT
    TO anon
    WITH CHECK (true);

COMMENT ON POLICY "incoming_calls_anon_insert" ON public.incoming_calls IS
    'Mobil aktarım uygulamasının publishable/anon key ile arama kaydı eklemesine izin verir. Sadece INSERT.';
