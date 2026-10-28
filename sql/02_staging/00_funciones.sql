/*
    Funciones de apoyo para la capa stg.

    stg.fn_normalizar_texto replica en T-SQL a src.profiling.normalizar_texto
    (Python), con las mismas reglas, para que una ciudad quede igual se
    normalice donde se normalice:

      1. Sin tildes: "São Paulo" -> "Sao Paulo". Truco: convertir a VARCHAR con
         una intercalación griega (CP1253), que no tiene letras latinas con
         tilde y las reemplaza por la letra base.
      2. Minúsculas.
      3. Caracteres no ASCII que sobrevivieron (texto corrupto, como el "£" de
         "sa£o paulo"): se borran.
      4. ´, ` y ’ pasan a apóstrofo; el resto de la puntuación ASCII que no sea
         apóstrofo o guion ("sbc/sp") pasa a espacio.
      5. Un solo espacio entre palabras, sin espacios ni apóstrofos en los extremos.

    tests/test_integracion_sql.py compara las dos versiones sobre todas las
    ciudades del dataset.
*/

USE [$(DB_NAME)];
GO

CREATE OR ALTER FUNCTION stg.fn_normalizar_texto (@texto NVARCHAR(400))
RETURNS NVARCHAR(400)
AS
BEGIN
    IF @texto IS NULL RETURN NULL;

    -- Tildes escritas como carácter aparte ("a" + U+0303 en vez de "ã"): se
    -- borran antes de convertir, porque la conversión las cambiaría por "?".
    DECLARE @combinables NVARCHAR(10) = N'%[' + NCHAR(768) + N'-' + NCHAR(879) + N']%';
    DECLARE @pos INT = PATINDEX(@combinables, @texto COLLATE Latin1_General_BIN);
    WHILE @pos > 0
    BEGIN
        SET @texto = STUFF(@texto, @pos, 1, N'');
        SET @pos = PATINDEX(@combinables, @texto COLLATE Latin1_General_BIN);
    END;

    -- Signos que en los datos se usan como apóstrofo ("santa barbara d´oeste")
    SET @texto = REPLACE(REPLACE(REPLACE(@texto, NCHAR(180), N''''), N'`', N''''), NCHAR(8217), N'''');

    DECLARE @s NVARCHAR(400) =
        LOWER(CAST(CAST(@texto COLLATE SQL_Latin1_General_CP1253_CI_AI AS VARCHAR(400)) AS NVARCHAR(400)));

    -- Pasos 3 y 4: recorrer cada carácter fuera de [a-z0-9 '-]. El guion va
    -- PRIMERO en la clase: al final ('-]), T-SQL lo toma como parte de un
    -- rango y el patrón deja de encontrar nada (bug detectado por el test de
    -- integración que compara esta función con la de Python).
    SET @pos = PATINDEX(N'%[^-a-z0-9 '']%', @s COLLATE Latin1_General_BIN);
    WHILE @pos > 0
    BEGIN
        SET @s = STUFF(@s, @pos, 1, CASE WHEN UNICODE(SUBSTRING(@s, @pos, 1)) > 127 THEN N'' ELSE N' ' END);
        SET @pos = PATINDEX(N'%[^-a-z0-9 '']%', @s COLLATE Latin1_General_BIN);
    END;

    WHILE CHARINDEX(N'  ', @s) > 0
        SET @s = REPLACE(@s, N'  ', N' ');

    SET @s = TRIM(N' ''' FROM @s);   -- espacios y apóstrofos de los extremos
    RETURN NULLIF(@s, N'');
END;
GO
