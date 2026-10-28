# Calidad de datos

**Fase:** 2 · **Análisis completo:** [notebooks/02_perfilado.ipynb](../notebooks/02_perfilado.ipynb) · **Funciones de chequeo:** [src/profiling.py](../src/profiling.py)

Este documento lista cada problema encontrado en los datos de Olist, su tamaño, su impacto en los KPIs y qué se decidió hacer. Los números salen del notebook, que se puede volver a ejecutar.

## Resumen

El **núcleo transaccional está sano**: pedidos, ítems, pagos, clientes, vendedores y productos tienen claves únicas y relaciones completas, sin un solo huérfano. Los problemas están en tres lugares:

1. **Granularidad:** unir tablas sin cuidado infla las ventas un 4,5% sin dar ningún error (Q12).
2. **Tablas auxiliares:** geolocalización, traducción de categorías y nombres de ciudades.
3. **Inconsistencias puntuales:** fechas intermedias desordenadas, reseñas duplicadas, pagos raros. Afectan a menos del 2% de las filas.

## Cómo se clasifica cada problema

| Gravedad | Qué significa | Qué hace el ETL (Fase 3) |
|---|---|---|
| 🔴 **Crítica** | Si ocurre, los KPIs dan mal | **Corta la carga** y lo registra en `etl.log_ejecucion` |
| 🟡 **Advertencia** | Afecta a pocas filas o a algo secundario | Corrige o marca, registra cuántas filas, y sigue |
| ⚪ **Informativa** | Es una característica de los datos, no un error | Nada; queda documentada |

La política está registrada como [D-009](decisiones.md#d-009--los-problemas-de-calidad-se-clasifican-por-gravedad).

---

## Catálogo de problemas

### Estructura y tipos

| Código | Problema | Tamaño | Gravedad | Decisión |
|---|---|---|---|---|
| **Q20** | El código postal leído como número **pierde el cero inicial** (`09790` → `9790`) y deja de coincidir con otras tablas, sin dar error. | 24% de los clientes | 🔴 | Se lee siempre como texto y se guarda como `CHAR(5)`. Validación: todos los códigos postales tienen 5 dígitos. |
| **Q12** | Un pedido tiene varios ítems y varios pagos. Unir ítems con pagos multiplica filas: las ventas pasan de R$ 13,59 M a R$ 14,21 M. | +4,5% en ventas | 🔴 | Dos tablas de hechos con distinta granularidad (ítem y pedido). Los pagos se agregan por pedido antes de unirse. Validación: las ventas en `dw` son iguales a las de `raw`. |
| **Q19** | Dos columnas vienen mal escritas en el origen: `product_name_lenght` y `product_description_lenght`. | 2 columnas | ⚪ | Se renombran en `stg` (`length`). |
| **Q23** | `customer_id` cambia en cada pedido: la persona es `customer_unique_id`. | Todos los pedidos | ⚪ | Regla R5 de los requerimientos. |

### Pedidos y fechas

| Código | Problema | Tamaño | Gravedad | Decisión |
|---|---|---|---|---|
| **Q09** | Fechas intermedias desordenadas: despacho antes de la compra (166), despacho antes de la aprobación (1.359, en general por 17 horas) y entrega antes del despacho (23). | 1.382 pedidos (1,4%) | 🟡 | No se corrigen: no hay forma de saber cuál de las dos fechas está mal. Se registran. **Las fechas que usan los KPIs (compra, entrega y estimada) están siempre en orden**: si eso se rompe, es 🔴. |
| **Q06** | Pedidos `delivered` sin fecha de entrega. | 8 | 🟡 | Cuentan como venta pero quedan fuera de los KPIs de entrega (ya contemplado en el diccionario). |
| **Q07** | Pedidos `delivered` sin fecha de aprobación. | 14 | ⚪ | Ningún KPI usa la aprobación. |
| **Q08** | Pedidos `canceled` con fecha de entrega. | 6 | ⚪ | Manda el estado: no son venta. |
| **Q10** | `shipping_limit_date` (fecha límite de despacho del vendedor) llega hasta 2020, aunque los pedidos terminan en 2018. | 4 ítems | ⚪ | La columna no se usa en ningún KPI. |
| **Q11** | Entregas extremas: 13 en menos de un día, 288 en más de 60 días, la más larga de 209 días. | 0,3% | ⚪ | Son posibles. Por eso K18 se muestra con su mediana (10,2 días) además del promedio (12,5). |
| **Q21** | Meses casi vacíos al principio (2016) y al final (sep–oct 2018). | 349 pedidos | ⚪ | Decisión [D-008](decisiones.md#d-008--período-de-análisis-ene-2017-a-ago-2018): se cargan, pero no se muestran. |

### Ítems, vendedores y pagos

| Código | Problema | Tamaño | Gravedad | Decisión |
|---|---|---|---|---|
| **Q13** | Pedidos con ítems de **más de un vendedor**. Los KPIs de entrega son por pedido, pero el vendedor es por ítem. | 1.278 (1,3%) | ⚪ | En el análisis por vendedor, un pedido cuenta para cada vendedor que participó. Se documenta en el modelo (Fase 4). |
| **Q16** | Ítems con flete en 0. | 383 | ⚪ | Válido: envío gratis. |
| **Q14** | Lo pagado no coincide con productos + flete. En 232 pedidos se pagó de más (posiblemente intereses por cuotas) y en 17 de menos. | 249 pedidos | ⚪ | Las ventas salen de los ítems ([D-006](decisiones.md#d-006--el-flete-no-forma-parte-de-la-venta)). Los pagos solo se usan para analizar medios de pago. |
| **Q15** | Pagos raros: 9 con valor 0 (6 vouchers y 3 `not_defined`), 3 de tipo `not_defined` (todos de pedidos cancelados), 2 con 0 cuotas, y 1 pedido entregado sin ningún pago. | 11 pagos y 1 pedido | 🟡 | `not_defined` pasa a "Desconocido"; 0 cuotas se interpreta como pago en una cuota. Se registran. |

### Reseñas

| Código | Problema | Tamaño | Gravedad | Decisión |
|---|---|---|---|---|
| **Q04** | `review_id` no es único: una misma reseña aparece en hasta 3 pedidos. Además, 547 pedidos tienen más de una reseña, y 202 de ellos con puntajes distintos. | 814 ids repetidos | 🟡 | En `stg` la clave es `review_id` + `order_id`. Para los KPIs vale la última reseña respondida de cada pedido (regla R7). |
| **Q05** | Reseñas creadas **antes de la compra**. | 64 | 🟡 | Error de datos. Se conservan y se marcan. Las 5.127 creadas antes de la entrega son normales: Olist envía la encuesta en la fecha estimada, llegue o no el pedido. |
| **Q22** | Comentarios vacíos: 88% sin título y 59% sin mensaje. | — | ⚪ | Fuera de alcance (requerimientos, sección 2). |

### Productos y categorías

| Código | Problema | Tamaño | Gravedad | Decisión |
|---|---|---|---|---|
| **Q17** | Productos sin categoría (y sin nombre, descripción ni fotos). Además, 2 sin dimensiones y 4 con peso 0. | 610 productos | 🟡 | Categoría "Sin categoría", que aparece como un valor más en los filtros. Peso 0 pasa a nulo. |
| **Q18** | Categorías sin traducción en la tabla de Olist: `pc_gamer` y `portateis_cozinha_e_preparadores_de_alimentos`. | 2 categorías, 13 productos | 🟡 | Tabla propia de categorías **en español** con las 73 categorías ([D-011](decisiones.md#d-011--categorías-en-español-con-una-tabla-propia)). |

### Geografía

| Código | Problema | Tamaño | Gravedad | Decisión |
|---|---|---|---|---|
| **Q01** | `geolocation` no es un catálogo de códigos postales sino una lista de puntos: 1.000.163 filas para 19.015 códigos (mediana de 29 por código, máximo 1.146), 261.831 copias exactas, 8 códigos en más de un estado y 42 puntos fuera de Brasil. | Toda la tabla | 🟡 | Una fila por código postal: mediana de latitud y longitud, ciudad y estado más frecuentes, descartando antes los puntos fuera de Brasil ([D-010](decisiones.md#d-010--geolocalización-una-fila-por-código-postal)). |
| **Q02** | Códigos postales que no están en `geolocation`. | 278 clientes, 7 vendedores | ⚪ | Quedan sin coordenadas. No afecta ningún KPI: el estado viene de la tabla de clientes o vendedores. |
| **Q03** | Ciudades escritas de varias formas: con y sin tilde ("são paulo" / "sao paulo"), con caracteres corruptos ("sa£o paulo") y 28 ciudades de vendedores inválidas ("sao paulo - sp", "sbc/sp", "04482255"). | 8.011 nombres que son 5.966 ciudades | ⚪ | Se normalizan (minúsculas, sin tildes). Las ciudades inválidas de vendedores se reemplazan por la del código postal. La ciudad no se usa en KPIs (la región es el estado, regla R9). |

---

## Reglas de validación para la Fase 3

Cada regla sale de un problema de arriba. El ETL las corre en cada carga, y el resultado queda en la tabla de log.

### 🔴 Críticas: cortan la carga

| Regla | Qué verifica | Origen |
|---|---|---|
| V01 | Cada CSV tiene la cantidad de filas esperada | Fase 0 |
| V02 | Claves únicas en pedidos, ítems, pagos, clientes, vendedores y productos | Sección 2 del notebook |
| V03 | Sin huérfanos entre pedidos, ítems, pagos, reseñas, clientes, vendedores y productos | Sección 4 |
| V04 | Precio mayor a 0; flete y valor de pago mayores o iguales a 0 | Sección 3 |
| V05 | Entrega y entrega estimada nunca anteriores a la compra | Q09 |
| V06 | Puntaje de reseña entre 1 y 5 | Sección 3 |
| V07 | Todos los códigos postales tienen 5 dígitos | Q20 |
| V08 | Las ventas y el flete en `dw` son iguales a los de `raw` (conciliación) | Q12 |

### 🟡 Advertencias: se registran y la carga sigue

| Regla | Qué verifica | Origen |
|---|---|---|
| V09 | Fechas intermedias desordenadas | Q09 |
| V10 | Pedidos entregados sin fecha de entrega | Q06 |
| V11 | Reseñas creadas antes de la compra | Q05 |
| V12 | Pagos `not_defined`, en 0 o con 0 cuotas | Q15 |
| V13 | Productos sin categoría y categorías sin nombre en español | Q17, Q18 |
| V14 | Coordenadas fuera de Brasil descartadas | Q01 |
| V15 | Hechos asignados al miembro "Desconocido" de una dimensión (un pedido o ítem sin cliente, producto, vendedor o estado conocido) | Fase 4 |

Para cada advertencia, el log guarda cuántas filas la cumplieron. Si un número cambia mucho de una carga a otra, es una señal para revisar el origen.
