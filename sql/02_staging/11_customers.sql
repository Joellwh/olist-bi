/*
    stg.customers: tipos, código postal como texto (Q20) y ciudad normalizada (Q03).
*/

USE [$(DB_NAME)];
GO

INSERT INTO stg.customers (customer_id, customer_unique_id, zip_code_prefix, city, state)
SELECT customer_id,
       customer_unique_id,
       customer_zip_code_prefix,
       stg.fn_normalizar_texto(customer_city),
       UPPER(customer_state)
FROM raw.customers;
GO
