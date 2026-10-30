/*
    rpt.cohortes: retención de clientes por mes de primera compra (X5, K27).

    Una fila por cohorte y por mes transcurrido desde la primera compra:

      cohorte           AAAAMM de la primera compra válida (dim_cliente)
      meses_desde       0 = el mes de la primera compra, 1 = el siguiente...
      clientes          personas de la cohorte que compraron en ese mes
      tamanio_cohorte   personas de la cohorte (las que compraron en el mes 0)
      retencion         clientes / tamanio_cohorte

    El mes 0 tiene siempre retención 1 (100%): es la definición de la cohorte.
    Se cuentan personas (customer_unique_id), no pedidos, y solo pedidos válidos (R1).
*/

USE [$(DB_NAME)];
GO

CREATE OR ALTER VIEW rpt.cohortes AS
WITH actividad AS (
    -- Meses en los que compró cada persona (una fila por persona y mes)
    SELECT DISTINCT p.cliente_key, f.anio_mes
    FROM dw.fact_pedidos AS p
    JOIN dw.dim_fecha AS f ON f.fecha_key = p.fecha_compra_key
    WHERE p.es_valido = 1
),
con_cohorte AS (
    SELECT a.cliente_key,
           c.cohorte,
           c.cohorte_nombre,
           (a.anio_mes / 100 - c.cohorte / 100) * 12 + (a.anio_mes % 100 - c.cohorte % 100) AS meses_desde
    FROM actividad AS a
    JOIN dw.dim_cliente AS c ON c.cliente_key = a.cliente_key
    WHERE c.cohorte IS NOT NULL
),
conteo AS (
    SELECT cohorte, cohorte_nombre, meses_desde, COUNT(*) AS clientes
    FROM con_cohorte
    GROUP BY cohorte, cohorte_nombre, meses_desde
)
SELECT cohorte,
       cohorte_nombre,
       meses_desde,
       clientes,
       FIRST_VALUE(clientes) OVER (PARTITION BY cohorte ORDER BY meses_desde) AS tamanio_cohorte,
       CAST(clientes * 1.0 / FIRST_VALUE(clientes) OVER (PARTITION BY cohorte ORDER BY meses_desde)
            AS DECIMAL(9, 6)) AS retencion
FROM conteo;
GO
