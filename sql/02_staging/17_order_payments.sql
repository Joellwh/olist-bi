/*
    stg.order_payments: tipos. Un pago en 0 cuotas se interpreta como pago en
    una cuota (Q15). "not_defined" se conserva; en dw se muestra como "Desconocido".
*/

USE [$(DB_NAME)];
GO

INSERT INTO stg.order_payments (order_id, payment_sequential, payment_type, payment_installments,
                                payment_value)
SELECT order_id,
       CAST(payment_sequential AS SMALLINT),
       payment_type,
       CASE WHEN CAST(payment_installments AS SMALLINT) = 0 THEN 1
            ELSE CAST(payment_installments AS SMALLINT) END,
       CAST(payment_value AS DECIMAL(10, 2))
FROM raw.order_payments;
GO
