# SQL analítico y optimización

**Fase:** 5 · **Vistas:** [sql/04_views/](../sql/04_views/) · **Índices:** [sql/03_dw/90_indices.sql](../sql/03_dw/90_indices.sql) · **Benchmark:** [src/optimizacion.py](../src/optimizacion.py)

## Vistas analíticas (`rpt`)

Responden las preguntas que en SQL se resuelven mejor que en DAX: las que necesitan ordenar, numerar o comparar filas entre sí. El ETL las recrea en cada carga (paso 7).

| Vista | Pregunta | Técnica |
|---|---|---|
| `rpt.ventas_mensuales` | C1: evolución mensual, contra el mes y el año anterior | `LAG`, `SUM() OVER` (acumulado), `AVG() OVER ... ROWS 2 PRECEDING` (media móvil) |
| `rpt.cohortes` | X5: de los que compraron por primera vez en un mes, cuántos vuelven | CTEs encadenadas, `FIRST_VALUE` |
| `rpt.recompra_clientes` | X4: quién vuelve y cuánto tarda | `ROW_NUMBER`, `LEAD`, `COUNT() OVER` |
| `rpt.ranking_vendedores` | C4: los vendedores más importantes, en su región y en total | `RANK` con y sin `PARTITION BY`, `NTILE(4)`, `SUM() OVER ()` |
| `rpt.rfm_clientes` | Segmentación de clientes por recencia, frecuencia y monto | `NTILE(5)`, segmentos con `CASE` |

### Cómo se verifican

Cada vista tiene que cerrar con el diccionario de KPIs (`tests/test_integracion_sql.py`):

- La suma de `ventas_mensuales` en el período es K01, el acumulado a agosto de 2018 es K09 y la variación ene–ago es K08.
- Cada persona está en una sola cohorte, y el mes 0 tiene retención 100%.
- El ranking suma K01, tiene un vendedor por cada uno de K12, y las participaciones suman 1.
- La RFM tiene una fila por cada cliente de K06 y su monto suma K01.

### Tres decisiones de diseño dentro de las vistas

**1. La serie mensual parte del calendario, no de los hechos.** Noviembre de 2016 no tuvo ni un pedido. Si la serie saliera de los hechos, ese mes desaparecería, y `LAG(12)` compararía cada mes con el equivocado **sin dar error**. Partiendo de `dim_fecha`, el mes aparece con ventas en 0 y el año anterior se busca por `anio_mes - 100`. Un test verifica que la serie tenga los 26 meses.

**2. La frecuencia de la RFM usa umbrales fijos, no quintiles.** El 97% de los clientes compró una sola vez. Con `NTILE(5)` sobre la frecuencia, clientes idénticos terminarían en quintiles distintos según cómo se desempaten. Recencia y monto sí van por quintiles.

**3. La participación se calcula en `FLOAT`.** SQL Server trunca la división entre dos `DECIMAL` a 6 decimales. En 3.029 vendedores, las participaciones sumaban 0,9985 en lugar de 1, con todo el error hacia abajo. Lo detectó el test que verifica que sumen 1.

### Hallazgo: casi un tercio de la "recompra" es el mismo carrito

De los 2.875 clientes del período con más de un pedido, **821 (29%) hicieron el segundo el mismo día que el primero**. Lo más probable es que sea una compra partida en dos pedidos, por ejemplo por tener vendedores distintos. Contando días distintos de compra, la recompra baja de 3,0% (K25) a **2,2% (K28)**. K25 no se modifica, porque un KPI publicado no se redefine; se agregó K28 al diccionario para mostrar las dos lecturas.

## Optimización: cinco estrategias medidas

### Método

`python -m src.optimizacion` corre 7 consultas típicas contra cada estrategia de índices: agregaciones de tablero, búsquedas puntuales y las vistas de `rpt`. Para cada una registra:

- **Lecturas lógicas:** páginas de 8 KB leídas. Es la métrica principal porque no varía con la carga de la PC. Incluye las de las tablas de trabajo internas y las *lob logical reads*, que es donde el columnstore informa las suyas.
- **CPU:** mediana de 4 corridas con la caché caliente; la primera se descarta.
- **Plan de ejecución:** cómo se lee cada tabla de hechos y si hay operadores en modo batch.

### Resultados

Lecturas lógicas / milisegundos de CPU. Menos es mejor.

| Consulta | A. Solo PK | B. Rowstore en FK | C. Columnstore | D. B + C | **E. Columnstore + 2 puntuales** |
|---|---:|---:|---:|---:|---:|
| Ventas por categoría (2018) | 1.636 / 70 | 1.278 / 86 | 792 / 8 | 792 / 16 | **792 / 16** |
| % a tiempo por estado | 1.841 / 40 | 715 / 16 | 261 / 0 | 261 / 0 | **261 / 0** |
| Pedidos de un cliente | 1.776 / 8 | 57 / 0 | 1.776 / 16 | 57 / 0 | **57 / 0** |
| Ventas mensuales de un vendedor | 3.488 / 0 | 2.325 / 0 | 344 / 0 | 29 / 0 | **29 / 0** |
| `rpt.cohortes` | 3.968 / 250 | 2.842 / 235 | 2.466 / 118 | 2.466 / 149 | **2.466 / 141** |
| `rpt.ranking_vendedores` | 7.420 / 55 | 7.119 / 63 | 391 / 16 | 391 / 0 | **391 / 16** |
| `rpt.rfm_clientes` | 403.266 / 727 | 402.141 / 750 | 566 / 204 | 566 / 195 | **566 / 196** |
| **Espacio extra** | 0 MB | 29,3 MB | 6,0 MB | 35,2 MB | **16,9 MB** |
| **Tiempo de creación** | — | 0,7 s | 1,3 s | 2,0 s | **1,5 s** |

Medido el 2026-10-30 en SQL Server 2022 Express. Los milisegundos de CPU varían unos 15 ms entre corridas (es la resolución del reloj): las diferencias chicas de CPU no son significativas, las de lecturas sí.

### Lectura de los resultados

- **El columnstore (C) gana en todo lo que agrega**, con entre 2 y 19 veces menos lecturas, porque lee solo las columnas que usa la consulta, y comprimidas.
- **El columnstore pierde en las búsquedas puntuales.** Para traer los pedidos de un cliente recorre la tabla entera (1.776 lecturas). Un índice común en `cliente_key` va directo a las filas (57 lecturas).
- **E iguala a D en todas las consultas con 3 índices menos:** la mitad de espacio y menos tiempo de creación. Los índices comunes sobre fecha y producto de B quedan de más cuando hay columnstore, porque las consultas que los usarían son agregaciones, y esas ya las resuelve el columnstore.

### Estrategia elegida: E

Columnstore no agrupado en las dos tablas de hechos, más dos índices comunes para las páginas de detalle (`fact_pedidos.cliente_key` y `fact_items.vendedor_key`). La crea el ETL en cada carga, después de insertar los hechos ([D-017](decisiones.md#d-017--índices-columnstore-más-dos-índices-puntuales)).

### Lo que no era obvio

**1. En la RFM, el índice no era el problema.** De sus 403.266 lecturas, 400.303 son de una tabla de trabajo que SQL Server arma para calcular `NTILE` fila por fila; las tablas de hechos aportan 1.800. Los índices comunes (B) no cambian nada. El columnstore sí, y no por leer más rápido, sino porque **habilita el modo batch**: los operadores procesan miles de filas por vez y la función de ventana ya no necesita la tabla de trabajo. Resultado: de 403.266 a 566 lecturas y de 727 a 196 ms de CPU.

**2. La primera medición del columnstore estaba mal.** El columnstore informa sus lecturas en un campo aparte (*lob logical reads*), y la primera versión del benchmark no lo sumaba: mostraba 14 lecturas para la RFM, un número irrealmente bajo. Antes de sacar conclusiones, revisé por qué un resultado era tan bueno.

**3. La primera ejecución engaña.** Después de cada carga, `rpt.ventas_mensuales` tardó 13 segundos la primera vez y 0,17 s las siguientes: la diferencia está en compilar el plan y traer los datos a memoria. Por eso el benchmark descarta la primera corrida.

## Cómo se reproduce

```bash
python -m src.etl.run          # carga todo, con la estrategia E
python -m src.optimizacion     # mide las 5 estrategias (~1 minuto) y deja la base en E
```
