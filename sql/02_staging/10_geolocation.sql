/*
    stg.geolocation: de 1.000.163 puntos a una fila por código postal (Q01, D-010).

    1. Se descartan los puntos fuera del rectángulo de Brasil (validación V14).
    2. Coordenadas: mediana de latitud y longitud. No se deja arrastrar por
       los puntos mal cargados que queden dentro del rectángulo.
    3. Ciudad y estado: la combinación más frecuente del código postal.

    La ciudad se normaliza sobre los ~8 mil nombres distintos y no sobre el
    millón de filas: la función es escalar y no conviene llamarla un millón
    de veces para obtener el mismo resultado.
*/

USE [$(DB_NAME)];
GO

DROP TABLE IF EXISTS #ciudades;

SELECT ciudad_original, stg.fn_normalizar_texto(ciudad_original) AS ciudad
INTO #ciudades
FROM (SELECT DISTINCT geolocation_city AS ciudad_original FROM raw.geolocation) AS d;

WITH puntos AS (
    SELECT g.geolocation_zip_code_prefix AS zip,
           CAST(g.geolocation_lat AS FLOAT) AS lat,
           CAST(g.geolocation_lng AS FLOAT) AS lng,
           c.ciudad,
           UPPER(g.geolocation_state) AS estado
    FROM raw.geolocation AS g
    JOIN #ciudades AS c ON c.ciudad_original = g.geolocation_city
),
validos AS (
    SELECT * FROM puntos
    WHERE lat BETWEEN -33.8 AND 5.3 AND lng BETWEEN -74.0 AND -34.7
),
medianas AS (
    SELECT DISTINCT zip,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lat) OVER (PARTITION BY zip) AS lat,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY lng) OVER (PARTITION BY zip) AS lng,
           COUNT(*) OVER (PARTITION BY zip) AS puntos
    FROM validos
),
ciudad_mas_frecuente AS (
    SELECT zip, ciudad, estado,
           ROW_NUMBER() OVER (PARTITION BY zip ORDER BY COUNT(*) DESC, ciudad, estado) AS orden
    FROM validos
    GROUP BY zip, ciudad, estado
)
INSERT INTO stg.geolocation (zip_code_prefix, lat, lng, city, state, puntos)
SELECT m.zip, CAST(m.lat AS DECIMAL(9, 6)), CAST(m.lng AS DECIMAL(9, 6)), c.ciudad, c.estado, m.puntos
FROM medianas AS m
JOIN ciudad_mas_frecuente AS c ON c.zip = m.zip AND c.orden = 1;

DROP TABLE #ciudades;
GO
