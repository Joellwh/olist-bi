/*
    dw.fact_pedidos: un pedido por fila.

    Acá se calculan, una sola vez, las reglas de negocio de los requerimientos
    (D-016). El DAX de la Fase 7 las usa como columnas, sin repetir la lógica:

      es_valido        R1: no cancelado ni sin stock
      es_vendido       R1 + R8: además tiene al menos un ítem
      es_entregado     delivered y con fecha de entrega (Q06)
      a_tiempo         R3: fecha de entrega (sin hora) <= fecha estimada
      dias_entrega     K18: compra -> entrega, en días con decimales
      dias_vs_estimada K19: entrega - estimada en días; positivo = tarde
      puntaje_resena   R7: el de la última reseña respondida

    Los pagos se agregan por pedido ANTES de unirse (Q12): una fila de pago
    por pedido, nunca una por pago.
*/

USE [$(DB_NAME)];
GO

WITH pagos AS (
    SELECT order_id,
           SUM(payment_value) AS valor_pagado,
           MAX(payment_installments) AS cuotas,
           -- Medio principal: el de mayor monto; a igual monto, el primero
           (SELECT TOP 1 p2.payment_type FROM stg.order_payments AS p2
            WHERE p2.order_id = p.order_id
            ORDER BY p2.payment_value DESC, p2.payment_sequential) AS medio
    FROM stg.order_payments AS p
    GROUP BY order_id
),
items AS (
    SELECT order_id, COUNT(*) AS items FROM stg.order_items GROUP BY order_id
),
pedidos AS (
    SELECT o.*,
           CASE WHEN o.order_status NOT IN ('canceled', 'unavailable') THEN 1 ELSE 0 END AS es_valido,
           CASE WHEN o.order_status = 'delivered' AND o.delivered_customer_ts IS NOT NULL THEN 1 ELSE 0 END AS es_entregado
    FROM stg.orders AS o
)
INSERT INTO dw.fact_pedidos (pedido_id, cliente_key, geografia_key, fecha_compra_key, fecha_entrega_key,
                             fecha_estimada_key, estado_pedido, es_valido, es_vendido, es_entregado, a_tiempo,
                             dias_entrega, dias_vs_estimada, puntaje_resena, items, valor_pagado, medio_pago, cuotas)
SELECT o.order_id,
       COALESCE(dc.cliente_key, -1),
       COALESCE(dg.geografia_key, -1),
       CONVERT(INT, CONVERT(CHAR(8), o.purchase_ts, 112)),
       CONVERT(INT, CONVERT(CHAR(8), o.delivered_customer_ts, 112)),
       CONVERT(INT, CONVERT(CHAR(8), o.estimated_delivery_date, 112)),
       CASE o.order_status
           WHEN 'delivered'   THEN N'Entregado'
           WHEN 'shipped'     THEN N'En camino'
           WHEN 'canceled'    THEN N'Cancelado'
           WHEN 'unavailable' THEN N'Sin stock'
           WHEN 'invoiced'    THEN N'Facturado'
           WHEN 'processing'  THEN N'En preparación'
           WHEN 'created'     THEN N'Creado'
           WHEN 'approved'    THEN N'Aprobado'
           ELSE o.order_status
       END,
       o.es_valido,
       CASE WHEN o.es_valido = 1 AND i.items IS NOT NULL THEN 1 ELSE 0 END,
       o.es_entregado,
       CASE WHEN o.es_entregado = 1
            THEN CASE WHEN CAST(o.delivered_customer_ts AS DATE) <= o.estimated_delivery_date THEN 1 ELSE 0 END
       END,
       CASE WHEN o.es_entregado = 1
            THEN DATEDIFF(SECOND, o.purchase_ts, o.delivered_customer_ts) / 86400.0 END,
       CASE WHEN o.es_entregado = 1
            THEN DATEDIFF(DAY, o.estimated_delivery_date, CAST(o.delivered_customer_ts AS DATE)) END,
       r.review_score,
       COALESCE(i.items, 0),
       pg.valor_pagado,
       CASE pg.medio
           WHEN 'credit_card' THEN N'Tarjeta de crédito'
           WHEN 'debit_card'  THEN N'Tarjeta de débito'
           WHEN 'boleto'      THEN N'Boleto'
           WHEN 'voucher'     THEN N'Voucher'
           ELSE N'Desconocido'                       -- not_defined y el pedido sin pagos (Q15)
       END,
       pg.cuotas
FROM pedidos AS o
JOIN stg.customers AS c ON c.customer_id = o.customer_id
LEFT JOIN dw.dim_cliente AS dc ON dc.customer_unique_id = c.customer_unique_id
LEFT JOIN dw.dim_geografia AS dg ON dg.estado = c.state
LEFT JOIN items AS i ON i.order_id = o.order_id
LEFT JOIN pagos AS pg ON pg.order_id = o.order_id
LEFT JOIN stg.order_reviews AS r ON r.order_id = o.order_id AND r.es_ultima_del_pedido = 1;
GO
