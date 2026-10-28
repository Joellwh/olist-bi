/*
    stg.order_reviews: tipos y dos marcas.

      es_ultima_del_pedido    regla R7: si un pedido tiene varias reseñas, vale
                              la última respondida (Q04). Desempate por review_id
                              para que el resultado no dependa del orden de lectura.
      creada_antes_de_compra  Q05: error de datos que se marca, no se descarta.
*/

USE [$(DB_NAME)];
GO

WITH tipadas AS (
    SELECT review_id,
           order_id,
           CAST(review_score AS TINYINT) AS review_score,
           review_comment_title,
           review_comment_message,
           CAST(CAST(review_creation_date AS DATETIME2(0)) AS DATE) AS creation_date,
           CAST(review_answer_timestamp AS DATETIME2(0)) AS answer_ts
    FROM raw.order_reviews
)
INSERT INTO stg.order_reviews (review_id, order_id, review_score, comment_title, comment_message,
                               creation_date, answer_ts, es_ultima_del_pedido, creada_antes_de_compra)
SELECT r.review_id,
       r.order_id,
       r.review_score,
       r.review_comment_title,
       r.review_comment_message,
       r.creation_date,
       r.answer_ts,
       CASE WHEN ROW_NUMBER() OVER (PARTITION BY r.order_id
                                    ORDER BY r.answer_ts DESC, r.review_id DESC) = 1
            THEN 1 ELSE 0 END,
       CASE WHEN r.creation_date < CAST(CAST(o.order_purchase_timestamp AS DATETIME2(0)) AS DATE)
            THEN 1 ELSE 0 END
FROM tipadas AS r
LEFT JOIN raw.orders AS o ON o.order_id = r.order_id;
GO
