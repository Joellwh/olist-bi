/*
    Capa raw: una tabla por CSV, con las mismas columnas y todo como texto.

    raw es una copia fiel del origen. No se tipa ni se limpia nada acá, a
    propósito: si un valor viene mal, la carga no falla en esta capa, y el
    problema se ve (y se valida) al pasarlo a stg. Los largos tienen margen
    de sobra sobre lo medido en la Fase 2.

    Se recrea en cada ejecución (carga completa, D-012): así la estructura
    siempre coincide con este script.
*/

USE [$(DB_NAME)];
GO

DROP TABLE IF EXISTS raw.orders, raw.order_items, raw.order_payments, raw.order_reviews,
                     raw.customers, raw.sellers, raw.products, raw.category_translation,
                     raw.geolocation, raw.categorias_es;
GO

CREATE TABLE raw.orders (
    order_id                      NVARCHAR(100),
    customer_id                   NVARCHAR(100),
    order_status                  NVARCHAR(50),
    order_purchase_timestamp      NVARCHAR(50),
    order_approved_at             NVARCHAR(50),
    order_delivered_carrier_date  NVARCHAR(50),
    order_delivered_customer_date NVARCHAR(50),
    order_estimated_delivery_date NVARCHAR(50)
);

CREATE TABLE raw.order_items (
    order_id            NVARCHAR(100),
    order_item_id       NVARCHAR(20),
    product_id          NVARCHAR(100),
    seller_id           NVARCHAR(100),
    shipping_limit_date NVARCHAR(50),
    price               NVARCHAR(30),
    freight_value       NVARCHAR(30)
);

CREATE TABLE raw.order_payments (
    order_id             NVARCHAR(100),
    payment_sequential   NVARCHAR(20),
    payment_type         NVARCHAR(50),
    payment_installments NVARCHAR(20),
    payment_value        NVARCHAR(30)
);

CREATE TABLE raw.order_reviews (
    review_id               NVARCHAR(100),
    order_id                NVARCHAR(100),
    review_score            NVARCHAR(20),
    review_comment_title    NVARCHAR(200),
    review_comment_message  NVARCHAR(1000),
    review_creation_date    NVARCHAR(50),
    review_answer_timestamp NVARCHAR(50)
);

CREATE TABLE raw.customers (
    customer_id              NVARCHAR(100),
    customer_unique_id       NVARCHAR(100),
    customer_zip_code_prefix NVARCHAR(20),
    customer_city            NVARCHAR(200),
    customer_state           NVARCHAR(20)
);

CREATE TABLE raw.sellers (
    seller_id              NVARCHAR(100),
    seller_zip_code_prefix NVARCHAR(20),
    seller_city            NVARCHAR(200),
    seller_state           NVARCHAR(20)
);

CREATE TABLE raw.products (
    product_id                 NVARCHAR(100),
    product_category_name      NVARCHAR(200),
    product_name_lenght        NVARCHAR(20),   -- así viene escrito en el origen (Q19)
    product_description_lenght NVARCHAR(20),
    product_photos_qty         NVARCHAR(20),
    product_weight_g           NVARCHAR(20),
    product_length_cm          NVARCHAR(20),
    product_height_cm          NVARCHAR(20),
    product_width_cm           NVARCHAR(20)
);

CREATE TABLE raw.category_translation (
    product_category_name         NVARCHAR(200),
    product_category_name_english NVARCHAR(200)
);

CREATE TABLE raw.geolocation (
    geolocation_zip_code_prefix NVARCHAR(20),
    geolocation_lat             NVARCHAR(50),
    geolocation_lng             NVARCHAR(50),
    geolocation_city            NVARCHAR(200),
    geolocation_state           NVARCHAR(20)
);

-- Tabla propia del proyecto (data/seeds/categorias.csv, D-011).
CREATE TABLE raw.categorias_es (
    category_name_pt NVARCHAR(200),
    category_es      NVARCHAR(200)
);
GO
