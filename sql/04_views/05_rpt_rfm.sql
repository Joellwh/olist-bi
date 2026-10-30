/*
    rpt.rfm_clientes: segmentación RFM de las personas que compraron en el
    período de análisis (ene-2017 a ago-2018, D-008).

      recencia_dias  días desde la última compra hasta el 2018-09-01 (fin del período)
      frecuencia     pedidos válidos en el período
      monto          ventas (precio, sin flete: D-006) en el período

    Puntajes de 1 a 5 (5 = mejor):
      R y M: NTILE(5), quintiles. R se ordena de más vieja a más reciente.
      F: umbrales fijos (1 pedido = 1, 2 = 3, 3 o más = 5). El 97% de los
         clientes compró una sola vez: con NTILE(5), clientes idénticos
         terminarían en quintiles distintos según el orden de desempate.

    Segmentos, en orden de prioridad (gana la primera regla que se cumple):
      Campeones       compró hace poco y más de una vez
      Leales          más de una vez, no tan reciente
      Nuevos valiosos una vez, hace poco y con monto alto
      Nuevos          una vez y hace poco
      En riesgo       una vez, hace tiempo, con monto alto
      Hibernando      una vez, hace tiempo
      Perdidos        una vez y hace mucho
*/

USE [$(DB_NAME)];
GO

CREATE OR ALTER VIEW rpt.rfm_clientes AS
WITH pedidos AS (
    SELECT p.cliente_key, p.pedido_id, f.fecha
    FROM dw.fact_pedidos AS p
    JOIN dw.dim_fecha AS f ON f.fecha_key = p.fecha_compra_key
    WHERE p.es_valido = 1 AND f.en_periodo_analisis = 1
),
montos AS (
    SELECT i.pedido_id, SUM(i.precio) AS monto
    FROM dw.fact_items AS i
    WHERE i.es_venta = 1
    GROUP BY i.pedido_id
),
rfm AS (
    SELECT p.cliente_key,
           DATEDIFF(DAY, MAX(p.fecha), '2018-09-01') AS recencia_dias,
           COUNT(*) AS frecuencia,
           COALESCE(SUM(m.monto), 0) AS monto
    FROM pedidos AS p
    LEFT JOIN montos AS m ON m.pedido_id = p.pedido_id
    GROUP BY p.cliente_key
),
puntajes AS (
    SELECT rfm.*,
           NTILE(5) OVER (ORDER BY recencia_dias DESC) AS r,
           CASE WHEN frecuencia >= 3 THEN 5 WHEN frecuencia = 2 THEN 3 ELSE 1 END AS f,
           NTILE(5) OVER (ORDER BY monto) AS m
    FROM rfm
)
SELECT cliente_key,
       recencia_dias,
       frecuencia,
       monto,
       r, f, m,
       CONCAT(r, f, m) AS rfm,
       CASE
           WHEN r >= 4 AND f >= 3 THEN N'Campeones'
           WHEN f >= 3            THEN N'Leales'
           WHEN r >= 4 AND m >= 4 THEN N'Nuevos valiosos'
           WHEN r >= 4            THEN N'Nuevos'
           WHEN r >= 2 AND m >= 4 THEN N'En riesgo'
           WHEN r >= 2            THEN N'Hibernando'
           ELSE N'Perdidos'
       END AS segmento
FROM puntajes;
GO
