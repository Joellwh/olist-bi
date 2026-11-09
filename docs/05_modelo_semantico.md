# Modelo semántico en Power BI

**Fase:** 6 · **Proyecto:** [powerbi/olist.pbip](../powerbi/olist.pbip) · **Modelo como texto:** [powerbi/olist.SemanticModel/definition/](../powerbi/olist.SemanticModel/definition/)

El modelo semántico es la capa que usa el usuario del tablero: traduce el modelo estrella de SQL Server (`dw`, ver [03_modelo_dimensional.md](03_modelo_dimensional.md)) a tablas, relaciones y nombres de negocio. Está guardado en formato **PBIP con TMDL**: cada tabla es un archivo de texto, y el historial de git muestra qué cambió en el modelo.

## Conexión

Modo **Importar**, desde las 7 tablas de `dw` ([D-018](decisiones.md#d-018--power-bi-en-modo-importar)). El servidor y la base son **parámetros** de Power Query (`Servidor` y `BaseDatos`), así que pasar de `OlistDW` a otra base no exige editar ninguna tabla (Fase 11).

## Relaciones

Son 10, todas de uno a muchos, de una dimensión a un hecho, con filtro en una sola dirección.

| Dimensión | `fact_items` | `fact_pedidos` |
|---|---|---|
| `dim_fecha` | `fecha_compra_key` | `fecha_compra_key` (activa), `fecha_entrega_key` y `fecha_estimada_key` (inactivas) |
| `dim_geografia` | `geografia_key` | `geografia_key` |
| `dim_cliente` | `cliente_key` | `cliente_key` |
| `dim_vendedor` | `vendedor_key` | — |
| `dim_producto` | `producto_key` | — |

- **Los hechos no se relacionan entre sí.** Para cruzar vendedor con entrega se usa `TREATAS` ([D-014](decisiones.md#d-014--dos-tablas-de-hechos-y-treatas-para-cruzarlas)).
- **Por qué una sola dirección:** un filtro bidireccional entre dimensión y hecho abre caminos ambiguos (por ejemplo, de `dim_producto` a `dim_geografia` pasando por `fact_items`) y es más lento. Acá ninguna pregunta de negocio lo necesita.
- **Las dos relaciones inactivas** existen porque entre dos tablas solo puede haber un camino activo. La de compra queda activa (regla R6: todo se ubica por fecha de compra), y las otras se activan en una medida con `USERELATIONSHIP`.
- **Las importó Power BI** desde las claves foráneas de `dw`. Es una ventaja concreta de haber declarado esas claves en SQL Server.

## Fechas

- `dim_fecha` está **marcada como tabla de fechas**, con `Fecha` como clave. Es lo que necesitan las funciones de inteligencia de tiempo de la Fase 7.
- **La opción de fecha y hora automáticas está desactivada.** Power BI había creado una tabla de fechas oculta por cada columna de fecha, que ocupan memoria y compiten con `dim_fecha`.
- **Orden:** `Mes`, `Mes corto`, `Trimestre`, `Año-mes`, `Día de la semana` y `Cohorte` se ordenan por una columna numérica oculta. Sin eso, Abril aparecería antes que Enero.
- **El período de análisis** (ene-2017 a ago-2018, [D-008](decisiones.md#d-008--período-de-análisis-ene-2017-a-ago-2018)) es la columna `En período de análisis`. El filtro se aplica en los reportes (Fase 8).

## Qué ve el usuario

| Decisión | Detalle |
|---|---|
| **Nombres de negocio** | `Año`, `Región`, `Categoría`, en lugar de `anio`, `region`, `categoria`. En las columnas ocultas se mantiene el nombre técnico. |
| **Claves e identificadores ocultos** | Todas las `*_key` y los hash de origen. |
| **Valores de los hechos ocultos** | Se usan a través de medidas (Fase 7), y las medidas implícitas están desactivadas ([D-019](decisiones.md#d-019--todo-cálculo-pasa-por-una-medida)). |
| **Jerarquías** | `Calendario` (Año → Trimestre → Mes → Fecha) y `Geografía` (Región → Estado). |
| **Carpetas** | `Período` y `Día` en `dim_fecha`; `Características` en `dim_producto`. |
| **Descripciones** | Cada columna y tabla explica qué es y qué regla o KPI aplica; se ven al pasar el mouse en el panel de datos. |
| **Categorías de datos** | Estados y ciudades marcados como geografía, para que los mapas los reconozcan. |
| **Montos** | `precio`, `flete` y `valor_pagado` en decimal fijo y formato R$. Power BI los había importado como decimales flotantes, que pueden acumular errores de redondeo al sumar. |
| **Tabla `_Medidas`** | Contiene las 41 medidas de la Fase 7 ([06_dax.md](06_dax.md)), así ninguna depende de una tabla de hechos para encontrarse. |
| **Tablas sin relaciones** | `Top N`, `Selector de métrica` y `Meses desde cohorte` alimentan los controles del tablero (agregadas en la Fase 7). |

## Cómo se verificó

**Números:** con una consulta en la vista de consultas DAX, filtrando solo `dim_fecha` por el período. Coinciden con los valores de referencia del [diccionario de KPIs](kpi_diccionario.md). El filtro llega a los dos hechos únicamente a través de las relaciones, así que la consulta también las prueba.

| KPI | Modelo | Diccionario |
|---|---|---|
| K01 Ventas | 13.449.529,68 | 13.449.529,68 |
| K14 Flete | 2.234.177,06 | 2.234.177,06 |
| K02 Pedidos | 97.905 | 97.905 |
| K06 Clientes | 94.707 | 94.707 |
| K16 Entregados | 96.203 | 96.203 |
| K20 Con demora | 6.531 | 6.531 |

**Diseño:** [tests/test_modelo_semantico.py](../tests/test_modelo_semantico.py) lee los archivos TMDL en cada push y falla si aparece un filtro bidireccional, una relación entre hechos, una clave visible o un servidor escrito a mano.

## La trampa que encontró la verificación

La primera consulta de K20 dio **8.238** en lugar de 6.531. La causa fue el filtro `fact_pedidos[a_tiempo] = FALSE()`:

- `a_tiempo` queda vacía en los pedidos que no se entregaron.
- **En DAX, un valor vacío comparado con `=` contra `FALSE` da verdadero.** Se contaron también los 1.707 pedidos válidos sin entregar.

No da ningún error: el número simplemente sale más grande. **Regla para la Fase 7:** toda medida que use `a_tiempo` filtra además por `es_entregado = TRUE()`.

## Cómo se abre

1. Correr el ETL si la base está vacía: `python -m src.etl.run`.
2. Abrir `powerbi/olist.pbip` en Power BI Desktop.
3. **Inicio → Actualizar.** Los datos no se versionan: `.pbi/cache.abf` está en `.gitignore`, y se regenera al actualizar.
