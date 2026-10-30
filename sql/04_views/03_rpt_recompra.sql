/*
    rpt.recompra_clientes: una fila por persona con al menos un pedido válido (X4, K25).

      pedidos                 pedidos válidos de la persona (R1)
      primera_compra          fecha del primer pedido válido
      segunda_compra          fecha del segundo, si existe (LEAD)
      dias_hasta_segunda      cuánto tardó en volver
      es_recompra             1 si tiene dos pedidos válidos o más

    Considera todo el historial. Para la tasa del diccionario (K25), que se
    calcula dentro del período de análisis, se filtra por fecha de compra en
    la consulta o en Power BI.

    Dos pedidos con el mismo instante de compra cuentan como dos (son pedidos
    distintos), pero dias_hasta_segunda queda en 0.
*/

USE [$(DB_NAME)];
GO

CREATE OR ALTER VIEW rpt.recompra_clientes AS
WITH pedidos AS (
    SELECT p.cliente_key,
           f.fecha,
           ROW_NUMBER() OVER (PARTITION BY p.cliente_key ORDER BY f.fecha, p.pedido_id) AS nro,
           LEAD(f.fecha) OVER (PARTITION BY p.cliente_key ORDER BY f.fecha, p.pedido_id) AS siguiente,
           COUNT(*) OVER (PARTITION BY p.cliente_key) AS pedidos
    FROM dw.fact_pedidos AS p
    JOIN dw.dim_fecha AS f ON f.fecha_key = p.fecha_compra_key
    WHERE p.es_valido = 1
)
SELECT cliente_key,
       pedidos,
       fecha AS primera_compra,
       siguiente AS segunda_compra,
       DATEDIFF(DAY, fecha, siguiente) AS dias_hasta_segunda,
       CASE WHEN pedidos > 1 THEN 1 ELSE 0 END AS es_recompra
FROM pedidos
WHERE nro = 1;
GO
