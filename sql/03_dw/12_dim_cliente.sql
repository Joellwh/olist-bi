/*
    dw.dim_cliente: una fila por persona (customer_unique_id, regla R5).

    La fecha de primera compra considera solo pedidos válidos (R1) y TODO el
    historial, no solo el período de análisis: un cliente que compró por
    primera vez en 2016 no es "nuevo" en 2017. Es la base de las cohortes (X5).

    La ubicación no va acá: una persona puede comprar desde distintos
    domicilios, y lo que se analiza es dónde estaba en cada pedido
    (geografia_key de los hechos, D-015).
*/

USE [$(DB_NAME)];
GO

SET IDENTITY_INSERT dw.dim_cliente ON;
INSERT INTO dw.dim_cliente (cliente_key, customer_unique_id, fecha_primera_compra, cohorte, cohorte_nombre)
VALUES (-1, REPLICATE('0', 32), NULL, NULL, NULL);
SET IDENTITY_INSERT dw.dim_cliente OFF;

WITH primera AS (
    SELECT c.customer_unique_id,
           MIN(CASE WHEN o.order_status NOT IN ('canceled', 'unavailable')
                    THEN CAST(o.purchase_ts AS DATE) END) AS fecha_primera_compra
    FROM stg.customers AS c
    JOIN stg.orders AS o ON o.customer_id = c.customer_id
    GROUP BY c.customer_unique_id
)
INSERT INTO dw.dim_cliente (customer_unique_id, fecha_primera_compra, cohorte, cohorte_nombre)
SELECT p.customer_unique_id,
       p.fecha_primera_compra,
       f.anio_mes,
       f.anio_mes_nombre
FROM primera AS p
LEFT JOIN dw.dim_fecha AS f ON f.fecha = p.fecha_primera_compra
ORDER BY p.fecha_primera_compra, p.customer_unique_id;
GO
