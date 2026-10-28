/*
    stg.orders: fechas tipadas. Se usa CAST y no TRY_CAST a propósito: si una
    fecha no se puede convertir, la carga tiene que fallar, no dejar un NULL
    silencioso que después cambia los KPIs de entrega.
*/

USE [$(DB_NAME)];
GO

INSERT INTO stg.orders (order_id, customer_id, order_status, purchase_ts, approved_ts,
                        delivered_carrier_ts, delivered_customer_ts, estimated_delivery_date)
SELECT order_id,
       customer_id,
       order_status,
       CAST(order_purchase_timestamp AS DATETIME2(0)),
       CAST(order_approved_at AS DATETIME2(0)),
       CAST(order_delivered_carrier_date AS DATETIME2(0)),
       CAST(order_delivered_customer_date AS DATETIME2(0)),
       CAST(CAST(order_estimated_delivery_date AS DATETIME2(0)) AS DATE)
FROM raw.orders;
GO
