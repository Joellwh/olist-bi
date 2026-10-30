/*
    Índices de las tablas de hechos: la estrategia E de docs/04_optimizacion_sql.md,
    elegida midiendo 5 estrategias con python -m src.optimizacion.

      Columnstore no agrupado en cada hecho: resuelve las agregaciones y las
      funciones de ventana (habilita el modo batch, que en la vista RFM baja
      las lecturas de 403.266 a 566).

      Dos índices rowstore para búsquedas puntuales, que el columnstore hace
      mal (recorre la tabla entera): los pedidos de un cliente y las ventas
      de un vendedor (páginas de detalle).

    Se crean después de cargar los hechos: insertar en una tabla sin índices
    secundarios y crearlos al final es más rápido que mantenerlos fila a fila.
*/

USE [$(DB_NAME)];
GO

-- Se puede volver a correr solo (src.optimizacion lo usa para dejar la base
-- en esta estrategia), así que primero se borran los que existan.
DROP INDEX IF EXISTS ncci_fact_items ON dw.fact_items;
DROP INDEX IF EXISTS ncci_fact_pedidos ON dw.fact_pedidos;
DROP INDEX IF EXISTS ix_fact_items_vendedor ON dw.fact_items;
DROP INDEX IF EXISTS ix_fact_pedidos_cliente ON dw.fact_pedidos;

CREATE NONCLUSTERED COLUMNSTORE INDEX ncci_fact_items ON dw.fact_items
    (pedido_id, item_nro, producto_key, vendedor_key, cliente_key, geografia_key,
     fecha_compra_key, precio, flete, es_venta);

CREATE NONCLUSTERED COLUMNSTORE INDEX ncci_fact_pedidos ON dw.fact_pedidos
    (pedido_id, cliente_key, geografia_key, fecha_compra_key, fecha_entrega_key, fecha_estimada_key,
     es_valido, es_vendido, es_entregado, a_tiempo, dias_entrega, dias_vs_estimada, puntaje_resena, items);

CREATE INDEX ix_fact_items_vendedor ON dw.fact_items (vendedor_key)
    INCLUDE (fecha_compra_key, precio, es_venta);

CREATE INDEX ix_fact_pedidos_cliente ON dw.fact_pedidos (cliente_key)
    INCLUDE (fecha_compra_key, es_valido);
GO
