-- =====================================================================
-- 01_TABLES.SQL
-- Sipariş Takip Sistemi - Tablo Oluşturma
-- Supabase SQL Editor üzerinde çalıştırın
-- =====================================================================

-- Gerekli eklentiler (UUID üretimi için)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------
-- 1) CUSTOMERS - Müşteriler
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.customers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    phone       TEXT NOT NULL UNIQUE,
    email       TEXT,
    notes       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON public.customers (phone);
CREATE INDEX IF NOT EXISTS idx_customers_name  ON public.customers (name);

-- ---------------------------------------------------------------------
-- 2) CUSTOMER_ADDRESSES - Müşteri Adresleri
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.customer_addresses (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id   UUID NOT NULL REFERENCES public.customers(id) ON DELETE CASCADE,
    title         TEXT,
    address_text  TEXT NOT NULL,
    latitude      DOUBLE PRECISION,
    longitude     DOUBLE PRECISION,
    is_default    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_customer_addresses_customer
    ON public.customer_addresses (customer_id);

-- ---------------------------------------------------------------------
-- 3) CATEGORIES - Ürün Kategorileri
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    color       TEXT
);

CREATE INDEX IF NOT EXISTS idx_categories_sort ON public.categories (sort_order);

-- ---------------------------------------------------------------------
-- 4) PRODUCTS - Ürünler
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.products (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id  UUID REFERENCES public.categories(id) ON DELETE SET NULL,
    name         TEXT NOT NULL,
    price        DECIMAL(10,2) NOT NULL DEFAULT 0,
    unit         TEXT NOT NULL DEFAULT 'adet',
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON public.products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_active   ON public.products (is_active);

-- ---------------------------------------------------------------------
-- 5) COURIERS - Kuryeler
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.couriers (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name               TEXT NOT NULL,
    phone              TEXT NOT NULL,
    password           TEXT,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    current_latitude   DOUBLE PRECISION,
    current_longitude  DOUBLE PRECISION,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_couriers_active ON public.couriers (is_active);

-- ---------------------------------------------------------------------
-- 6) ORDERS - Siparişler
-- order_number 1001'den başlayan otomatik artan numara
-- ---------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS public.orders_order_number_seq
    START WITH 1001
    INCREMENT BY 1
    MINVALUE 1001
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.orders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_number    INTEGER NOT NULL UNIQUE
                    DEFAULT nextval('public.orders_order_number_seq'),
    customer_id     UUID NOT NULL REFERENCES public.customers(id) ON DELETE RESTRICT,
    address_id      UUID REFERENCES public.customer_addresses(id) ON DELETE SET NULL,
    courier_id      UUID REFERENCES public.couriers(id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'new'
                    CHECK (status IN ('new','preparing','on_way','delivered','cancelled')),
    order_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    delivery_date   DATE,
    delivery_time   TIME,
    total_amount    DECIMAL(10,2) NOT NULL DEFAULT 0,
    payment_method  TEXT CHECK (payment_method IN ('cash','credit_card','iban')),
    payment_status  TEXT NOT NULL DEFAULT 'pending'
                    CHECK (payment_status IN ('pending','paid','partial')),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER SEQUENCE public.orders_order_number_seq OWNED BY public.orders.order_number;

CREATE INDEX IF NOT EXISTS idx_orders_customer       ON public.orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_courier        ON public.orders (courier_id);
CREATE INDEX IF NOT EXISTS idx_orders_status         ON public.orders (status);
CREATE INDEX IF NOT EXISTS idx_orders_order_date     ON public.orders (order_date);
CREATE INDEX IF NOT EXISTS idx_orders_delivery_date  ON public.orders (delivery_date);

-- ---------------------------------------------------------------------
-- 7) ORDER_ITEMS - Sipariş Kalemleri
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.order_items (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id     UUID NOT NULL REFERENCES public.orders(id) ON DELETE CASCADE,
    product_id   UUID REFERENCES public.products(id) ON DELETE SET NULL,
    quantity     DECIMAL(10,3) NOT NULL DEFAULT 1,
    unit         TEXT NOT NULL DEFAULT 'adet',
    unit_price   DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_price  DECIMAL(10,2) NOT NULL DEFAULT 0,
    notes        TEXT
);

CREATE INDEX IF NOT EXISTS idx_order_items_order   ON public.order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product ON public.order_items (product_id);

-- ---------------------------------------------------------------------
-- 8) PHONES - Bağlı Telefonlar
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.phones (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_name  TEXT,
    device_id    TEXT NOT NULL UNIQUE,
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_phones_device_id ON public.phones (device_id);

-- ---------------------------------------------------------------------
-- 9) INCOMING_CALLS - Gelen Aramalar
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.incoming_calls (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number  TEXT NOT NULL,
    device_id     TEXT,
    customer_id   UUID REFERENCES public.customers(id) ON DELETE SET NULL,
    is_processed  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incoming_calls_phone     ON public.incoming_calls (phone_number);
CREATE INDEX IF NOT EXISTS idx_incoming_calls_processed ON public.incoming_calls (is_processed);
CREATE INDEX IF NOT EXISTS idx_incoming_calls_created   ON public.incoming_calls (created_at DESC);

-- ---------------------------------------------------------------------
-- 10) SETTINGS - Uygulama Ayarları
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.settings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key          TEXT NOT NULL UNIQUE,
    value        TEXT,
    description  TEXT
);

-- ---------------------------------------------------------------------
-- 11) THEMES - Temalar
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.themes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              TEXT NOT NULL,
    primary_color     TEXT,
    secondary_color   TEXT,
    background_color  TEXT,
    text_color        TEXT,
    is_active         BOOLEAN NOT NULL DEFAULT FALSE
);
