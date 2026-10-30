/*
    rpt.ranking_vendedores: una fila por vendedor con ventas en el período de
    análisis (C4, X3), con su posición en la región y en el marketplace.

      ventas, pedidos                desde fact_items (el vendedor es por ítem)
      pct_a_tiempo, puntaje_resena   desde fact_pedidos, para los pedidos en los que
                                     participó el vendedor: el mismo cruce que TREATAS
                                     hace en DAX (D-014). Un pedido con dos vendedores
                                     cuenta para cada uno (Q13).
      ranking_region                 RANK por ventas dentro de la región del vendedor
      ranking_total                  RANK por ventas en todo el marketplace
      cuartil                        NTILE(4): 1 = el 25% que más vende
      participacion                  ventas / ventas totales del período (K11)

    RANK y no ROW_NUMBER: dos vendedores con las mismas ventas comparten puesto.
*/

USE [$(DB_NAME)];
GO

CREATE OR ALTER VIEW rpt.ranking_vendedores AS
WITH items_periodo AS (
    SELECT i.vendedor_key, i.pedido_id, i.precio
    FROM dw.fact_items AS i
    JOIN dw.dim_fecha AS f ON f.fecha_key = i.fecha_compra_key
    WHERE i.es_venta = 1 AND f.en_periodo_analisis = 1
),
ventas AS (
    SELECT vendedor_key, SUM(precio) AS ventas, COUNT(DISTINCT pedido_id) AS pedidos
    FROM items_periodo
    GROUP BY vendedor_key
),
pedidos_del_vendedor AS (
    SELECT DISTINCT vendedor_key, pedido_id FROM items_periodo
),
entregas AS (
    SELECT pv.vendedor_key,
           AVG(CAST(p.a_tiempo AS FLOAT)) AS pct_a_tiempo,          -- solo entregados: a_tiempo es NULL si no
           AVG(CAST(p.puntaje_resena AS FLOAT)) AS puntaje_resena
    FROM pedidos_del_vendedor AS pv
    JOIN dw.fact_pedidos AS p ON p.pedido_id = pv.pedido_id
    GROUP BY pv.vendedor_key
)
SELECT v.vendedor_key,
       d.vendedor,
       d.estado,
       d.region,
       v.ventas,
       v.pedidos,
       CAST(e.pct_a_tiempo AS DECIMAL(9, 4)) AS pct_a_tiempo,
       CAST(e.puntaje_resena AS DECIMAL(4, 2)) AS puntaje_resena,
       RANK() OVER (PARTITION BY d.region ORDER BY v.ventas DESC) AS ranking_region,
       RANK() OVER (ORDER BY v.ventas DESC) AS ranking_total,
       NTILE(4) OVER (ORDER BY v.ventas DESC) AS cuartil,
       -- En FLOAT: dividir dos DECIMAL trunca a 6 decimales, y en 3 mil vendedores
       -- la suma de las participaciones daba 0,9985 en vez de 1 (lo detectó un test)
       CAST(v.ventas AS FLOAT) / SUM(v.ventas) OVER () AS participacion
FROM ventas AS v
JOIN dw.dim_vendedor AS d ON d.vendedor_key = v.vendedor_key
LEFT JOIN entregas AS e ON e.vendedor_key = v.vendedor_key;
GO
