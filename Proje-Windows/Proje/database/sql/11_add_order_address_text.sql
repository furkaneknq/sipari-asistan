-- Sipariş oluşturulurken seçilen adresin metnini sabit saklar.
-- Müşteri adresi değişse bile eski siparişin adresi değişmez.
ALTER TABLE public.orders ADD COLUMN IF NOT EXISTS address_text TEXT;

COMMENT ON COLUMN public.orders.address_text IS
  'Sipariş oluşturulurken seçilen adresin snapshot metni. Müşteri adresi sonradan değişse bile siparişteki adres korunur.';

-- Mevcut siparişleri (address_id üzerinden) backfill et
UPDATE public.orders o
SET address_text = ca.address_text
FROM public.customer_addresses ca
WHERE o.address_id = ca.id
  AND o.address_text IS NULL;
