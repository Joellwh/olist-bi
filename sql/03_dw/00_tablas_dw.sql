/*
    Capa dw: modelo dimensional en estrella (docs/03_modelo_dimensional.md).

      Dimensiones: dim_fecha, dim_geografia, dim_cliente, dim_vendedor, dim_producto
      Hechos:      fact_items   (un ítem vendido)
                   fact_pedidos (un pedido)

    Las dos tablas de hechos comparten dimensiones pero NO se relacionan entre
    sí: tienen distinta granularidad, y unirlas directamente infla los totales
    (Q12). Para cruzar el vendedor (ítem) con la entrega (pedido) se usa
    TREATAS en DAX (D-014).

    Claves subrogadas INT en las dimensiones, con un miembro "Desconocido"
    (-1) para que un hecho nunca quede sin dimensión. dim_fecha usa la fecha
    como número AAAAMMDD, que es legible y ordena igual que la fecha.

    A diferencia de stg, acá sí hay claves foráneas: dw es lo que lee Power BI
    y tiene que ser consistente por construcción.

    Se recrea en cada ejecución (carga completa, D-012).
*/

USE [$(DB_NAME)];
GO

DROP TABLE IF EXISTS dw.fact_items, dw.fact_pedidos;
DROP TABLE IF EXISTS dw.dim_fecha, dw.dim_geografia, dw.dim_cliente, dw.dim_vendedor, dw.dim_producto;
GO

CREATE TABLE dw.dim_fecha (
    fecha_key           INT          NOT NULL CONSTRAINT pk_dim_fecha PRIMARY KEY,   -- AAAAMMDD
    fecha               DATE         NOT NULL CONSTRAINT uq_dim_fecha_fecha UNIQUE,
    anio                SMALLINT     NOT NULL,
    trimestre           TINYINT      NOT NULL,
    trimestre_nombre    CHAR(2)      NOT NULL,     -- T1..T4
    mes                 TINYINT      NOT NULL,
    mes_nombre          NVARCHAR(12) NOT NULL,     -- Enero
    mes_corto           NCHAR(3)     NOT NULL,     -- Ene
    anio_mes            INT          NOT NULL,     -- 201701, para ordenar
    anio_mes_nombre     NVARCHAR(10) NOT NULL,     -- Ene 2017
    dia                 TINYINT      NOT NULL,
    dia_semana          TINYINT      NOT NULL,     -- 1 = lunes
    dia_semana_nombre   NVARCHAR(10) NOT NULL,
    es_fin_de_semana    BIT          NOT NULL,
    en_periodo_analisis BIT          NOT NULL      -- D-008: ene-2017 a ago-2018
);

CREATE TABLE dw.dim_geografia (
    geografia_key INT           NOT NULL CONSTRAINT pk_dim_geografia PRIMARY KEY,
    estado        CHAR(2)       NOT NULL CONSTRAINT uq_dim_geografia_estado UNIQUE,  -- SP, RJ...
    estado_nombre NVARCHAR(30)  NOT NULL,
    region        NVARCHAR(15)  NOT NULL
);

CREATE TABLE dw.dim_cliente (
    cliente_key           INT IDENTITY(1, 1) NOT NULL CONSTRAINT pk_dim_cliente PRIMARY KEY,
    customer_unique_id    CHAR(32)     NOT NULL CONSTRAINT uq_dim_cliente UNIQUE,  -- la persona (R5)
    fecha_primera_compra  DATE         NULL,     -- primer pedido válido (R1)
    cohorte               INT          NULL,     -- AAAAMM de la primera compra (X5)
    cohorte_nombre        NVARCHAR(10) NULL
);

CREATE TABLE dw.dim_vendedor (
    vendedor_key  INT IDENTITY(1, 1) NOT NULL CONSTRAINT pk_dim_vendedor PRIMARY KEY,
    seller_id     CHAR(32)      NOT NULL CONSTRAINT uq_dim_vendedor UNIQUE,
    -- Nombre corto para mostrar ("Vendedor 4a3c…f21"). Único: si dos vendedores
    -- quedaran con el mismo nombre, Power BI los sumaría como si fueran uno.
    vendedor      NVARCHAR(20)  NOT NULL CONSTRAINT uq_dim_vendedor_nombre UNIQUE,
    ciudad        NVARCHAR(100) NULL,
    estado        CHAR(2)       NOT NULL,
    region        NVARCHAR(15)  NOT NULL
);

CREATE TABLE dw.dim_producto (
    producto_key  INT IDENTITY(1, 1) NOT NULL CONSTRAINT pk_dim_producto PRIMARY KEY,
    product_id    CHAR(32)      NOT NULL CONSTRAINT uq_dim_producto UNIQUE,
    categoria     NVARCHAR(100) NOT NULL,    -- en español; "Sin categoría" (Q17)
    categoria_pt  VARCHAR(100)  NULL,
    peso_g        INT           NULL,
    volumen_cm3   INT           NULL,
    fotos         SMALLINT      NULL
);

CREATE TABLE dw.fact_pedidos (
    pedido_id              CHAR(32)      NOT NULL CONSTRAINT pk_fact_pedidos PRIMARY KEY,
    cliente_key            INT           NOT NULL CONSTRAINT fk_fact_pedidos_cliente   REFERENCES dw.dim_cliente,
    geografia_key          INT           NOT NULL CONSTRAINT fk_fact_pedidos_geografia REFERENCES dw.dim_geografia,
    fecha_compra_key       INT           NOT NULL CONSTRAINT fk_fact_pedidos_compra    REFERENCES dw.dim_fecha,
    fecha_entrega_key      INT           NULL     CONSTRAINT fk_fact_pedidos_entrega   REFERENCES dw.dim_fecha,
    fecha_estimada_key     INT           NOT NULL CONSTRAINT fk_fact_pedidos_estimada  REFERENCES dw.dim_fecha,
    estado_pedido          NVARCHAR(20)  NOT NULL,   -- en español
    -- Reglas de negocio, calculadas una sola vez acá (D-016)
    es_valido              BIT           NOT NULL,   -- R1: no cancelado ni sin stock
    es_vendido             BIT           NOT NULL,   -- R1 + R8: válido y con ítems
    es_entregado           BIT           NOT NULL,   -- delivered con fecha de entrega
    a_tiempo               BIT           NULL,       -- R3; NULL si no se entregó
    dias_entrega           DECIMAL(9, 4) NULL,       -- K18: compra -> entrega, con decimales
    dias_vs_estimada       INT           NULL,       -- entrega - estimada, en días; > 0 = tarde (K19)
    puntaje_resena         TINYINT       NULL,       -- R7: última reseña; NULL sin reseña
    items                  SMALLINT      NOT NULL,
    valor_pagado           DECIMAL(10, 2) NULL,      -- NULL: el pedido sin pagos (Q15)
    medio_pago             NVARCHAR(20)  NOT NULL,   -- el de mayor monto
    cuotas                 SMALLINT      NULL
);

CREATE TABLE dw.fact_items (
    pedido_id         CHAR(32)       NOT NULL,      -- dimensión degenerada
    item_nro          SMALLINT       NOT NULL,
    producto_key      INT            NOT NULL CONSTRAINT fk_fact_items_producto  REFERENCES dw.dim_producto,
    vendedor_key      INT            NOT NULL CONSTRAINT fk_fact_items_vendedor  REFERENCES dw.dim_vendedor,
    cliente_key       INT            NOT NULL CONSTRAINT fk_fact_items_cliente   REFERENCES dw.dim_cliente,
    geografia_key     INT            NOT NULL CONSTRAINT fk_fact_items_geografia REFERENCES dw.dim_geografia,
    fecha_compra_key  INT            NOT NULL CONSTRAINT fk_fact_items_compra    REFERENCES dw.dim_fecha,
    precio            DECIMAL(10, 2) NOT NULL,
    flete             DECIMAL(10, 2) NOT NULL,
    es_venta          BIT            NOT NULL,      -- R1 del pedido: para filtrar sin cruzar hechos
    CONSTRAINT pk_fact_items PRIMARY KEY (pedido_id, item_nro)
);
GO
