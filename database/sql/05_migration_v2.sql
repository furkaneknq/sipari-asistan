-- =====================================================================
-- 05_MIGRATION_V2.SQL
-- "Tek Seferlik Müşteri" özelliği için sütun ekler.
-- Supabase SQL Editor'da bir kez çalıştırın (idempotent).
-- =====================================================================

-- customers tablosuna is_guest kolonu ekle
ALTER TABLE public.customers
    ADD COLUMN IF NOT EXISTS is_guest BOOLEAN NOT NULL DEFAULT FALSE;

-- Hızlı arama için index
CREATE INDEX IF NOT EXISTS idx_customers_is_guest
    ON public.customers (is_guest);

-- Mevcut müşterilerde değer FALSE kalır (default)
COMMENT ON COLUMN public.customers.is_guest IS
    'TRUE ise: tek seferlik (kayıtsız) müşteri. UI listesinde gösterilmez.';
