-- =====================================================================
-- 06_ADD_PAID_AMOUNT.SQL
-- orders tablosuna paid_amount kolonu ekler.
-- "Ödenen tutar" artık ayrı bir alanda tutulur (kısmi ödeme için).
-- Supabase SQL Editor'da bir kez çalıştırın (idempotent).
-- =====================================================================

-- 1) Kolonu ekle
ALTER TABLE public.orders
    ADD COLUMN IF NOT EXISTS paid_amount DECIMAL(10,2) NOT NULL DEFAULT 0;

-- 2) Geriye dönük: payment_status='paid' olan siparişlerde paid_amount = total_amount
UPDATE public.orders
SET paid_amount = total_amount
WHERE payment_status = 'paid'
  AND paid_amount = 0;

-- 3) İndex (raporlama hızı için)
CREATE INDEX IF NOT EXISTS idx_orders_paid_amount
    ON public.orders (paid_amount);

COMMENT ON COLUMN public.orders.paid_amount IS
    'Müşteriden tahsil edilen tutar. total_amount = toplam, paid_amount = ödenen.';
