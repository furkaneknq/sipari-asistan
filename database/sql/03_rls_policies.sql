-- =====================================================================
-- 03_RLS_POLICIES.SQL
-- Row Level Security (RLS) etkinleştirme ve politikalar
-- 02_triggers.sql çalıştırıldıktan SONRA çalıştırın
-- =====================================================================
--
-- NOT: Bu politika seti başlangıç (geliştirme) içindir.
--      - Authenticated kullanıcılar (Supabase Auth ile giriş yapmış)
--        tüm tablolara tam erişim alır.
--      - Anon (anahtarsız) erişim kapalıdır.
--      Üretime geçerken rol/cihaz bazlı daha sıkı politikalar yazılmalı.
-- =====================================================================

-- ---------------------------------------------------------------------
-- RLS aktif et
-- ---------------------------------------------------------------------
ALTER TABLE public.customers          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.couriers           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.order_items        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.phones             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.incoming_calls     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.settings           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.themes             ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------
-- Yardımcı: tek bir tablo için "authenticated full access" politikası kur
-- ---------------------------------------------------------------------
DO $$
DECLARE
    t TEXT;
    tables TEXT[] := ARRAY[
        'customers',
        'customer_addresses',
        'categories',
        'products',
        'couriers',
        'orders',
        'order_items',
        'phones',
        'incoming_calls',
        'settings',
        'themes'
    ];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        -- Eski politikalar varsa temizle
        EXECUTE format(
            'DROP POLICY IF EXISTS %I ON public.%I;',
            t || '_auth_select', t);
        EXECUTE format(
            'DROP POLICY IF EXISTS %I ON public.%I;',
            t || '_auth_insert', t);
        EXECUTE format(
            'DROP POLICY IF EXISTS %I ON public.%I;',
            t || '_auth_update', t);
        EXECUTE format(
            'DROP POLICY IF EXISTS %I ON public.%I;',
            t || '_auth_delete', t);

        -- SELECT
        EXECUTE format($f$
            CREATE POLICY %I ON public.%I
                FOR SELECT
                TO authenticated
                USING (true);
        $f$, t || '_auth_select', t);

        -- INSERT
        EXECUTE format($f$
            CREATE POLICY %I ON public.%I
                FOR INSERT
                TO authenticated
                WITH CHECK (true);
        $f$, t || '_auth_insert', t);

        -- UPDATE
        EXECUTE format($f$
            CREATE POLICY %I ON public.%I
                FOR UPDATE
                TO authenticated
                USING (true)
                WITH CHECK (true);
        $f$, t || '_auth_update', t);

        -- DELETE
        EXECUTE format($f$
            CREATE POLICY %I ON public.%I
                FOR DELETE
                TO authenticated
                USING (true);
        $f$, t || '_auth_delete', t);
    END LOOP;
END $$;

-- ---------------------------------------------------------------------
-- (OPSIYONEL) Geliştirme için anon (anahtarsız) okuma açmak isterseniz
-- aşağıdaki bloğun yorumunu kaldırın. Üretimde kapalı kalmalı!
-- ---------------------------------------------------------------------
-- DO $$
-- DECLARE
--     t TEXT;
--     tables TEXT[] := ARRAY[
--         'categories','products','themes','settings'
--     ];
-- BEGIN
--     FOREACH t IN ARRAY tables LOOP
--         EXECUTE format(
--             'DROP POLICY IF EXISTS %I ON public.%I;',
--             t || '_anon_select', t);
--         EXECUTE format($f$
--             CREATE POLICY %I ON public.%I
--                 FOR SELECT
--                 TO anon
--                 USING (true);
--         $f$, t || '_anon_select', t);
--     END LOOP;
-- END $$;
