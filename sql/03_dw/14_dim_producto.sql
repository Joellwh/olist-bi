/*
    dw.dim_producto: una fila por producto, con la categoría en español
    (D-011). Los productos sin categoría van a "Sin categoría" (Q17), que
    aparece como un valor más en los filtros.
*/

USE [$(DB_NAME)];
GO

SET IDENTITY_INSERT dw.dim_producto ON;
INSERT INTO dw.dim_producto (producto_key, product_id, categoria, categoria_pt, peso_g, volumen_cm3, fotos)
VALUES (-1, REPLICATE('0', 32), N'Desconocida', NULL, NULL, NULL, NULL);
SET IDENTITY_INSERT dw.dim_producto OFF;

INSERT INTO dw.dim_producto (product_id, categoria, categoria_pt, peso_g, volumen_cm3, fotos)
SELECT p.product_id,
       CASE WHEN p.category_name_pt IS NULL THEN N'Sin categoría'
            ELSE COALESCE(c.category_es, p.category_name_pt) END,
       p.category_name_pt,
       p.weight_g,
       CAST(p.length_cm AS INT) * p.height_cm * p.width_cm,   -- en INT: 105 x 105 x 118 no entra en SMALLINT
       p.photos_qty
FROM stg.products AS p
LEFT JOIN stg.categorias AS c ON c.category_name_pt = p.category_name_pt
ORDER BY p.product_id;
GO
