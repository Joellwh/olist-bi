/*
    stg.sellers: ciudad normalizada. Las 28 ciudades cargadas con formato
    inválido ("sao paulo - sp", "sbc/sp", "04482255", Q03) se reemplazan por la
    ciudad de su código postal en stg.geolocation; si el código no está, se
    usa la versión normalizada. La original queda en city_original.

    Un formato es inválido si tiene dígitos, barras, comas o arrobas, si tiene
    " - " (ciudad y estado juntos), o si tiene 2 letras o menos (solo el estado).
*/

USE [$(DB_NAME)];
GO

INSERT INTO stg.sellers (seller_id, zip_code_prefix, city, city_original, state)
SELECT s.seller_id,
       s.seller_zip_code_prefix,
       CASE
           WHEN s.seller_city LIKE N'%[0-9/\,@]%'
             OR s.seller_city LIKE N'% - %'
             OR LEN(LTRIM(RTRIM(s.seller_city))) <= 2
           THEN COALESCE(g.city, stg.fn_normalizar_texto(s.seller_city))
           ELSE stg.fn_normalizar_texto(s.seller_city)
       END,
       s.seller_city,
       UPPER(s.seller_state)
FROM raw.sellers AS s
LEFT JOIN stg.geolocation AS g ON g.zip_code_prefix = s.seller_zip_code_prefix;
GO
