/*
    stg.order_items: tipos. Precio y flete como DECIMAL, nunca FLOAT: son montos
    y tienen que sumar exacto (la validación V08 concilia el total con raw).
*/

USE [$(DB_NAME)];
GO

INSERT INTO stg.order_items (order_id, order_item_id, product_id, seller_id, shipping_limit_ts,
                             price, freight_value)
SELECT order_id,
       CAST(order_item_id AS SMALLINT),
       product_id,
       seller_id,
       CAST(shipping_limit_date AS DATETIME2(0)),
       CAST(price AS DECIMAL(10, 2)),
       CAST(freight_value AS DECIMAL(10, 2))
FROM raw.order_items;
GO
