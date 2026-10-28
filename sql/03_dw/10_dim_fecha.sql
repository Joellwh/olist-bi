/*
    dw.dim_fecha: un día por fila, del 2016-01-01 al 2018-12-31.

    El rango cubre todas las fechas de los hechos, incluidas las entregas
    estimadas que llegan a noviembre de 2018. Power BI necesita una tabla de
    fechas continua (sin huecos) para la inteligencia de tiempo de la Fase 7.

    Los nombres de meses y días se escriben a mano y no con DATENAME, que
    depende del idioma configurado en el servidor. El día de la semana se
    calcula para que 1 sea lunes sin importar @@DATEFIRST.
*/

USE [$(DB_NAME)];
GO

WITH numeros AS (
    SELECT TOP (DATEDIFF(DAY, '2016-01-01', '2018-12-31') + 1)
           ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
    FROM sys.all_objects AS a CROSS JOIN sys.all_objects AS b
),
fechas AS (
    SELECT DATEADD(DAY, n, CAST('2016-01-01' AS DATE)) AS fecha FROM numeros
),
partes AS (
    SELECT fecha,
           YEAR(fecha) AS anio,
           MONTH(fecha) AS mes,
           (DATEPART(WEEKDAY, fecha) + @@DATEFIRST - 2) % 7 + 1 AS dia_semana
    FROM fechas
)
INSERT INTO dw.dim_fecha (fecha_key, fecha, anio, trimestre, trimestre_nombre, mes, mes_nombre, mes_corto,
                          anio_mes, anio_mes_nombre, dia, dia_semana, dia_semana_nombre,
                          es_fin_de_semana, en_periodo_analisis)
SELECT CONVERT(INT, CONVERT(CHAR(8), fecha, 112)),
       fecha,
       anio,
       (mes - 1) / 3 + 1,
       CONCAT('T', (mes - 1) / 3 + 1),
       mes,
       CHOOSE(mes, N'Enero', N'Febrero', N'Marzo', N'Abril', N'Mayo', N'Junio', N'Julio',
                   N'Agosto', N'Septiembre', N'Octubre', N'Noviembre', N'Diciembre'),
       CHOOSE(mes, N'Ene', N'Feb', N'Mar', N'Abr', N'May', N'Jun', N'Jul', N'Ago', N'Sep', N'Oct', N'Nov', N'Dic'),
       anio * 100 + mes,
       CONCAT(CHOOSE(mes, N'Ene', N'Feb', N'Mar', N'Abr', N'May', N'Jun', N'Jul', N'Ago', N'Sep', N'Oct', N'Nov', N'Dic'),
              N' ', anio),
       DAY(fecha),
       dia_semana,
       CHOOSE(dia_semana, N'Lunes', N'Martes', N'Miércoles', N'Jueves', N'Viernes', N'Sábado', N'Domingo'),
       CASE WHEN dia_semana >= 6 THEN 1 ELSE 0 END,
       CASE WHEN fecha BETWEEN '2017-01-01' AND '2018-08-31' THEN 1 ELSE 0 END    -- D-008
FROM partes;
GO
