/*
    dw.dim_vendedor: una fila por vendedor, con su estado y región
    desnormalizados (modelo en estrella, no copo de nieve): la matriz de rutas
    (L3) cruza el estado del vendedor con el del cliente sin otra tabla.

    El seller_id es un hash ilegible; para mostrar se arma un nombre corto.
*/

USE [$(DB_NAME)];
GO

SET IDENTITY_INSERT dw.dim_vendedor ON;
INSERT INTO dw.dim_vendedor (vendedor_key, seller_id, vendedor, ciudad, estado, region)
VALUES (-1, REPLICATE('0', 32), N'Desconocido', NULL, '--', N'Desconocida');
SET IDENTITY_INSERT dw.dim_vendedor OFF;

INSERT INTO dw.dim_vendedor (seller_id, vendedor, ciudad, estado, region)
SELECT s.seller_id,
       CONCAT(N'Vendedor ', LEFT(s.seller_id, 4), N'…', RIGHT(s.seller_id, 3)),
       s.city,
       s.state,
       COALESCE(g.region, N'Desconocida')
FROM stg.sellers AS s
LEFT JOIN dw.dim_geografia AS g ON g.estado = s.state
ORDER BY s.seller_id;
GO
