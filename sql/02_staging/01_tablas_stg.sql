/*
    Capa stg: los datos de raw con tipos correctos, nombres corregidos y las
    limpiezas decididas en docs/02_calidad_datos.md.

    Cada tabla tiene clave primaria, pero no claves foráneas entre sí: la
    integridad referencial se verifica con las validaciones V03 (src/etl/
    validaciones.py), que registran cuántas filas fallan en vez de cortar el
    INSERT con un error genérico. Las claves foráneas llegan en dw (Fase 4).

    Se recrea en cada ejecución (carga completa, D-012).
*/

USE [$(DB_NAME)];
GO

DROP TABLE IF EXISTS stg.orders, stg.order_items, stg.order_payments, stg.order_reviews,
                     stg.customers, stg.sellers, stg.products, stg.categorias, stg.geolocation;
GO

CREATE TABLE stg.geolocation (                      -- Q01, D-010: una fila por código postal
    zip_code_prefix CHAR(5)       NOT NULL CONSTRAINT pk_stg_geolocation PRIMARY KEY,
    lat             DECIMAL(9, 6) NOT NULL,
    lng             DECIMAL(9, 6) NOT NULL,
    city            NVARCHAR(100) NULL,
    state           CHAR(2)       NOT NULL,
    puntos          INT           NOT NULL          -- cuántos puntos válidos se resumieron
);

CREATE TABLE stg.customers (
    customer_id        CHAR(32)      NOT NULL CONSTRAINT pk_stg_customers PRIMARY KEY,
    customer_unique_id CHAR(32)      NOT NULL,     -- la persona (regla R5)
    zip_code_prefix    CHAR(5)       NOT NULL,     -- Q20: texto, conserva el cero inicial
    city               NVARCHAR(100) NULL,
    state              CHAR(2)       NOT NULL
);

CREATE TABLE stg.sellers (
    seller_id        CHAR(32)      NOT NULL CONSTRAINT pk_stg_sellers PRIMARY KEY,
    zip_code_prefix  CHAR(5)       NOT NULL,
    city             NVARCHAR(100) NULL,
    city_original    NVARCHAR(200) NOT NULL,       -- Q03: se conserva para auditar el reemplazo
    state            CHAR(2)       NOT NULL
);

CREATE TABLE stg.categorias (                       -- D-011
    category_name_pt VARCHAR(100)  NOT NULL CONSTRAINT pk_stg_categorias PRIMARY KEY,
    category_es      NVARCHAR(100) NOT NULL,
    category_en      VARCHAR(100)  NULL            -- NULL en las 2 que Olist no traduce (Q18)
);

CREATE TABLE stg.products (
    product_id          CHAR(32)     NOT NULL CONSTRAINT pk_stg_products PRIMARY KEY,
    category_name_pt    VARCHAR(100) NULL,          -- NULL = sin categoría (Q17)
    name_length         SMALLINT     NULL,          -- Q19: "lenght" corregido
    description_length  SMALLINT     NULL,
    photos_qty          SMALLINT     NULL,
    weight_g            INT          NULL,          -- Q17: 0 pasa a NULL
    length_cm           SMALLINT     NULL,
    height_cm           SMALLINT     NULL,
    width_cm            SMALLINT     NULL
);

CREATE TABLE stg.orders (
    order_id               CHAR(32)     NOT NULL CONSTRAINT pk_stg_orders PRIMARY KEY,
    customer_id            CHAR(32)     NOT NULL,
    order_status           VARCHAR(20)  NOT NULL,
    purchase_ts            DATETIME2(0) NOT NULL,
    approved_ts            DATETIME2(0) NULL,
    delivered_carrier_ts   DATETIME2(0) NULL,
    delivered_customer_ts  DATETIME2(0) NULL,
    estimated_delivery_date DATE        NOT NULL
);

CREATE TABLE stg.order_items (
    order_id            CHAR(32)       NOT NULL,
    order_item_id       SMALLINT       NOT NULL,
    product_id          CHAR(32)       NOT NULL,
    seller_id           CHAR(32)       NOT NULL,
    shipping_limit_ts   DATETIME2(0)   NOT NULL,
    price               DECIMAL(10, 2) NOT NULL,
    freight_value       DECIMAL(10, 2) NOT NULL,
    CONSTRAINT pk_stg_order_items PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE stg.order_payments (
    order_id             CHAR(32)       NOT NULL,
    payment_sequential   SMALLINT       NOT NULL,
    payment_type         VARCHAR(20)    NOT NULL,
    payment_installments SMALLINT       NOT NULL,   -- Q15: 0 cuotas pasa a 1
    payment_value        DECIMAL(10, 2) NOT NULL,
    CONSTRAINT pk_stg_order_payments PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE stg.order_reviews (
    review_id               CHAR(32)       NOT NULL,
    order_id                CHAR(32)       NOT NULL,
    review_score            TINYINT        NOT NULL,
    comment_title           NVARCHAR(200)  NULL,
    comment_message         NVARCHAR(1000) NULL,
    creation_date           DATE           NOT NULL,
    answer_ts               DATETIME2(0)   NOT NULL,
    es_ultima_del_pedido    BIT            NOT NULL,  -- R7: la que cuenta para los KPIs
    creada_antes_de_compra  BIT            NOT NULL,  -- Q05: marcada, no descartada
    CONSTRAINT pk_stg_order_reviews PRIMARY KEY (review_id, order_id)   -- Q04
);
GO
