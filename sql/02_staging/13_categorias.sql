/*
    stg.categorias: nombres en español de la tabla propia (data/seeds/categorias.csv,
    D-011), con la traducción al inglés de Olist como referencia.
*/

USE [$(DB_NAME)];
GO

INSERT INTO stg.categorias (category_name_pt, category_es, category_en)
SELECT c.category_name_pt, c.category_es, t.product_category_name_english
FROM raw.categorias_es AS c
LEFT JOIN raw.category_translation AS t ON t.product_category_name = c.category_name_pt;
GO
