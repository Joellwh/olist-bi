/*
    dw.fact_items: un ítem vendido por fila. Es la fuente de Ventas (K01) y
    Flete (K14).

    Cliente, geografía y fecha se toman de fact_pedidos para que los dos
    hechos clasifiquen igual a cada pedido. es_venta repite la regla R1 del
    pedido: así se filtra sin cruzar las dos tablas de hechos.
*/

USE [$(DB_NAME)];
GO

INSERT INTO dw.fact_items (pedido_id, item_nro, producto_key, vendedor_key, cliente_key, geografia_key,
                           fecha_compra_key, precio, flete, es_venta)
SELECT i.order_id,
       i.order_item_id,
       COALESCE(dp.producto_key, -1),
       COALESCE(dv.vendedor_key, -1),
       fp.cliente_key,
       fp.geografia_key,
       fp.fecha_compra_key,
       i.price,
       i.freight_value,
       fp.es_valido
FROM stg.order_items AS i
JOIN dw.fact_pedidos AS fp ON fp.pedido_id = i.order_id
LEFT JOIN dw.dim_producto AS dp ON dp.product_id = i.product_id
LEFT JOIN dw.dim_vendedor AS dv ON dv.seller_id = i.seller_id;
GO
