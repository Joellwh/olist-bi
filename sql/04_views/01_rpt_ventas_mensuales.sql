/*
    rpt.ventas_mensuales: un mes por fila, con su evolución (C1).

      ventas_mes_anterior / variacion_mensual      LAG(1): contra el mes anterior
      ventas_anio_anterior / variacion_interanual  el mismo mes del año anterior (K07, K08)
      acumulado_anio                               SUM() OVER por año (K09)
      media_movil_3m                               AVG() OVER las 3 filas hasta el mes (K10)

    Se parte de dim_fecha y no de los hechos: un mes sin ventas aparece con 0
    en vez de desaparecer, y LAG siempre compara meses consecutivos. Por eso
    el año anterior se busca por anio_mes - 100 y no con LAG(12): con un hueco
    en la serie, LAG(12) caería en el mes equivocado sin dar error.

    Incluye todos los meses con datos; en_periodo_analisis marca los de D-008.
*/

USE [$(DB_NAME)];
GO

CREATE OR ALTER VIEW rpt.ventas_mensuales AS
WITH meses AS (
    SELECT DISTINCT anio, mes, anio_mes, anio_mes_nombre, en_periodo_analisis
    FROM dw.dim_fecha
    WHERE anio_mes BETWEEN 201609 AND 201810           -- meses con pedidos
),
ventas AS (
    SELECT f.anio_mes,
           SUM(i.precio) AS ventas,
           COUNT(DISTINCT i.pedido_id) AS pedidos
    FROM dw.fact_items AS i
    JOIN dw.dim_fecha AS f ON f.fecha_key = i.fecha_compra_key
    WHERE i.es_venta = 1
    GROUP BY f.anio_mes
),
serie AS (
    SELECT m.anio, m.mes, m.anio_mes, m.anio_mes_nombre, m.en_periodo_analisis,
           COALESCE(v.ventas, 0) AS ventas,
           COALESCE(v.pedidos, 0) AS pedidos
    FROM meses AS m
    LEFT JOIN ventas AS v ON v.anio_mes = m.anio_mes
)
SELECT s.anio,
       s.mes,
       s.anio_mes,
       s.anio_mes_nombre,
       s.en_periodo_analisis,
       s.ventas,
       s.pedidos,
       CAST(s.ventas / NULLIF(s.pedidos, 0) AS DECIMAL(10, 2)) AS ticket_promedio,
       LAG(s.ventas) OVER (ORDER BY s.anio_mes) AS ventas_mes_anterior,
       CAST(s.ventas / NULLIF(LAG(s.ventas) OVER (ORDER BY s.anio_mes), 0) - 1 AS DECIMAL(9, 4)) AS variacion_mensual,
       a.ventas AS ventas_anio_anterior,
       CAST(s.ventas / NULLIF(a.ventas, 0) - 1 AS DECIMAL(9, 4)) AS variacion_interanual,
       SUM(s.ventas) OVER (PARTITION BY s.anio ORDER BY s.anio_mes ROWS UNBOUNDED PRECEDING) AS acumulado_anio,
       CASE WHEN COUNT(*) OVER (ORDER BY s.anio_mes ROWS 2 PRECEDING) = 3     -- K10: vacío sin 3 meses
            THEN CAST(AVG(s.ventas) OVER (ORDER BY s.anio_mes ROWS 2 PRECEDING) AS DECIMAL(12, 2))
       END AS media_movil_3m
FROM serie AS s
LEFT JOIN serie AS a ON a.anio_mes = s.anio_mes - 100;
GO
