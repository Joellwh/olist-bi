/*
    stg.products: tipos, nombres de columna corregidos (Q19) y peso 0 como
    NULL (Q17). Los productos sin categoría quedan con NULL; en dw pasan a
    "Sin categoría".
*/

USE [$(DB_NAME)];
GO

INSERT INTO stg.products (product_id, category_name_pt, name_length, description_length, photos_qty,
                          weight_g, length_cm, height_cm, width_cm)
SELECT product_id,
       product_category_name,
       CAST(product_name_lenght AS SMALLINT),
       CAST(product_description_lenght AS SMALLINT),
       CAST(product_photos_qty AS SMALLINT),
       NULLIF(CAST(product_weight_g AS INT), 0),
       CAST(product_length_cm AS SMALLINT),
       CAST(product_height_cm AS SMALLINT),
       CAST(product_width_cm AS SMALLINT)
FROM raw.products;
GO
