# Rendimiento del modelo

**Fase:** 10 · **Decisión:** [D-023](decisiones.md#d-023--clave-numérica-de-pedido-y-modelo-sin-columnas-que-nada-usa)

El criterio de aceptación de la Fase 1 pedía que cada visual tardara menos de 2 segundos en Performance Analyzer. Antes de esta fase no se cumplía: 9 de 64 visuales pasaban los 2 s y el peor tardaba 3,1 s. Después, ninguno llega a 2 s, y el modelo pesa un 70% menos.

| | Antes | Después |
|---|---:|---:|
| Tamaño del modelo en memoria (VertiPaq) | 33,7 MB | **9,9 MB** |
| Visuales de más de 2 s (Performance Analyzer) | 9 de 64 | **0 de 64** |
| Visual más lento (Performance Analyzer) | 3.077 ms | **1.495 ms** |
| Consulta DAX más lenta, con la caché vacía | 2.212 ms | **230 ms** |
| Suma de las 46 consultas del reporte, con la caché vacía | 4.320 ms | **2.231 ms** |
| Avisos del Best Practice Analyzer | 126 | **72**, ninguno de rendimiento que aplique |

Los 43 controles de `Control KPIs.dax` siguen en OK: los cambios no movieron ningún resultado. Al cierre se sumaron 4 controles para las medidas nuevas de §3.4: 47 de 47.

## 1. Cómo se midió

Tres herramientas, cada una para una pregunta distinta:

| Herramienta | Qué responde | Cómo se usó |
|---|---|---|
| **Performance Analyzer** (Power BI Desktop) | ¿Cuánto tarda cada visual, de punta a punta? Es la medida del criterio. | Grabación de las 5 páginas (cada una se abre y se actualiza; el detalle de vendedor, por obtención de detalles desde Comercial) y exportación a JSON. Por visual se toma la peor de sus mediciones. |
| **VertiPaq Analyzer** (DAX Studio) | ¿Qué ocupa la memoria? | `dscmd vpax` contra el modelo abierto en Power BI Desktop. |
| **Best Practice Analyzer** (Tabular Editor 2) | ¿Qué no sigue las buenas prácticas? | Las reglas publicadas por Microsoft (`BPARules.json`), por línea de comandos contra el modelo abierto. |

Además, para separar el tiempo del motor del tiempo de dibujo: las 46 consultas DAX que Performance Analyzer registró se corrieron de nuevo una por una, **vaciando la caché antes de cada ejecución**, y se tomó la mediana de tres.

Dos cuidados para que el antes y el después sean comparables:

- **El tamaño se mide con el modelo abierto desde su archivo, no recién actualizado.** Justo después de una actualización, cada columna de texto reserva alrededor de 1 MB de diccionario aunque tenga 8 valores (una categoría pasaba de 0,1 a 1 MB). Medido así, el modelo "después" parecía pesar 23,9 MB; guardado y vuelto a abrir, pesaba 16,9. Todas las cifras de este documento son con el modelo abierto desde el archivo.
- **Performance Analyzer mide el tiempo total, que incluye esperar a los demás visuales.** Por eso varía entre corridas aunque el DAX no cambie: la página de detalle tardó 0,9 s en una corrida y 1,5 s en otra con el mismo DAX de 48 ms. Las conclusiones sobre el motor salen de las consultas con la caché vacía, que son estables.

## 2. Qué se encontró

**Memoria.** Tres textos de 32 caracteres, todos distintos, ocupaban el 47% del modelo:

| Columna | Tamaño | Para qué estaba |
|---|---:|---|
| `fact_items[pedido_id]` | 5,3 MB | Cruzar ítems con pedidos (`TREATAS`, D-014) |
| `fact_pedidos[pedido_id]` | 5,3 MB | El otro lado del mismo cruce |
| `dim_cliente[customer_unique_id]` | 5,2 MB | Nada: ninguna medida ni visual la usaba |

Un texto así no se puede comprimir: VertiPaq guarda cada valor en un diccionario y ninguno se repite.

**Tiempo.** Un visual explicaba casi todo el problema: *Categorías con más reseñas negativas* (Cliente), con 2,2 s de DAX. Separando su consulta en partes:

| Consulta (caché vacía) | Antes |
|---|---:|
| El visual completo | 2.212 ms |
| Solo las barras | 1.900 ms |
| Solo el título dinámico | 1.601 ms |
| Lo mínimo: reseñas por categoría, sin nada más | 682 ms |

Hasta la consulta más simple tardaba casi 0,7 s. El problema no era cómo estaban escritas las medidas, sino el cruce: por cada una de las 75 categorías, `TREATAS` trasladaba la lista de pedidos de `fact_items` a `fact_pedidos` comparando textos de 32 caracteres. Es lo que ya había señalado la Fase 7 en la matriz de rutas ([06_dax.md](06_dax.md)).

## 3. Qué se cambió

Tres cambios de rendimiento, medidos cada uno, y uno de mantenimiento que pidió el Best Practice Analyzer (§3.4):

| Cambio | Tamaño del modelo |
|---|---:|
| Punto de partida | 33,7 MB |
| 1 + 2. Clave numérica de pedido y columnas sin uso fuera del modelo | 16,9 MB |
| 3. Sin jerarquías de atributos en las columnas ocultas de los hechos | **9,9 MB** |

### 1. Clave numérica de pedido

- **En SQL:** `dw.fact_pedidos` tiene una columna nueva, `pedido_key` (entero, única, numerada en la carga). `dw.fact_items` la toma del pedido, con una clave foránea que garantiza que cada ítem apunte a un pedido existente. `pedido_id` sigue en SQL para trazar contra el origen.
- **En el modelo:** los dos hechos cargan `pedido_key` en lugar de `pedido_id`, las 7 medidas con `TREATAS` cruzan por esa columna, y `Pedidos` (K02) cuenta los `pedido_key` distintos en lugar de los `pedido_id`. El DAX no cambió en nada más.
- **Resultado:** las dos columnas pasan de 10,6 MB a 1,3 MB (un entero consecutivo se guarda por valor, sin diccionario), y la consulta lenta de 2.212 a 246 ms. La matriz de rutas, de 355 a 235 ms.

### 2. Columnas que nada usa, fuera del modelo

Se quitaron en Power Query (`Table.RemoveColumns`), no en SQL: siguen disponibles para otros usos de la base.

| Columna | Por qué estaba | Por qué se quitó |
|---|---|---|
| `dim_cliente[customer_unique_id]`, `dim_producto[product_id]`, `dim_vendedor[seller_id]` | Identificadores del origen | Ocultos y sin uso; para trazar ya están en SQL. Eran 7 MB. |
| `dim_producto[categoria_pt]` | Categoría en portugués | Oculta; el reporte usa la categoría en español. |
| `fact_items[item_nro]` | Número de ítem dentro del pedido | Solo servía de clave junto con `pedido_id`. |
| `fact_pedidos[es_vendido]`, `[items]`, `[valor_pagado]`, `[cuotas]` | Reglas y datos de pago calculados en la Fase 4 | Ninguna medida ni visual los usa. Siguen en `dw.fact_pedidos`. |

Antes de quitar cada una se verificó que no apareciera en ninguna medida, rol ni visual. El Best Practice Analyzer solo revisa el DAX; las columnas que usa el reporte se buscaron en sus archivos.

En el mismo paso:

- `fact_pedidos[dias_entrega]` pasó de decimal con coma flotante a **decimal fijo**, como los montos: es exacto al sumar y coincide con el `DECIMAL(9,4)` de SQL.
- Se **marcaron las claves** de las cuatro dimensiones (`isKey`).

### 3. Sin jerarquías de atributos en las columnas ocultas de los hechos

Para cada columna, el modelo arma una *jerarquía de atributos* que solo usan los clientes MDX, como Excel con "Analizar en Excel". En columnas ocultas que nadie va a usar para agrupar (claves, banderas, montos que solo suman las medidas) es memoria desperdiciada: 3,9 MB, el 24% de lo que quedaba.

Se desactivó (`isAvailableInMdx: false`) en las 26 columnas ocultas que marca el Best Practice Analyzer: todas las de los dos hechos, las claves de las dimensiones y `dim_fecha[fecha_key]`. El DAX no usa estas jerarquías: los 43 controles dieron igual y los tiempos no cambiaron (2.200 ms antes del cambio, 2.231 después, dentro del ruido). Se dejaron afuera la tabla de seguridad `Gerentes` y `_Medidas`, que pesan 0,05 MB entre las dos.

### 4. Las relaciones inactivas, en uso

El Best Practice Analyzer marcó que las relaciones de las fechas de entrega y estimada con `dim_fecha` nunca se activan. Se dejaron inactivas en la Fase 6 para usarlas con `USERELATIONSHIP`, pero ninguna medida lo hacía. En lugar de borrarlas, se agregaron las dos medidas que justifican tenerlas:

| Medida | Qué cuenta | Período completo | Agosto de 2018 |
|---|---|---:|---:|
| `Pedidos entregados` (ya existía) | Entregados, ubicados por **fecha de compra** (R6) | 96.203 | 6.351 |
| `Entregas del período` | Entregados, ubicados por **fecha de entrega** | 96.144 | 8.314 |
| `Entregas previstas` | Pedidos válidos, ubicados por **fecha estimada de entrega** | 95.912 | 9.306 |

La diferencia en agosto de 2018 es el motivo de tenerlas: de lo comprado ese mes, se entregaron 6.351 pedidos, pero Logística entregó 8.314 en el mes, porque muchos se habían comprado en julio. Para dimensionar la operación, la fecha que importa es la de entrega.

Se muestran en el gráfico mensual de Logística, en la información sobre herramientas, sin cambiar el diseño de la página. Los valores coinciden con SQL, también con la seguridad por fila activa: con el rol `Región Sur`, 13.762 entregas y 13.626 previstas, iguales a la consulta en SQL. Un test controla que cada relación inactiva la active una medida.

## 4. Resultados por página

**Performance Analyzer:** visual más lento de cada página, en tiempo total.

| Página | Antes | Después | Visual más lento después |
|---|---:|---:|---|
| Resumen | 691 ms | 684 ms | Top categorías |
| Comercial | 2.189 ms | 808 ms | Métrica elegida por estado |
| Logística | 1.945 ms | 1.251 ms | Matriz de rutas |
| Cliente | **3.077 ms** | 916 ms | Categorías con más reseñas negativas |
| Detalle de vendedor | 935 ms | 1.495 ms | Distribución de puntajes |

- **Cliente** es la mejora del cambio 1: su visual lento pasó de 2,5 s de DAX a 0,2 s.
- **Comercial:** antes, sus diez visuales tardaban todos alrededor de 2,1 s, aunque su DAX tardaba menos de 0,2 s. Era la primera página después de abrir el archivo, y los visuales esperaban su turno. En la medición de después también fue la primera, y tardó 0,8 s. Parte de la mejora es el modelo más chico, pero no se puede separar del arranque.
- **Detalle de vendedor** empeoró en tiempo total, pero su DAX tarda 48 ms. Es la variación entre corridas que se explica en §1.

**Consultas DAX con la caché vacía:** las 46 del reporte, mediana de tres.

| Consulta | Antes | Después |
|---|---:|---:|
| Categorías con más reseñas negativas | 2.212 ms | 230 ms |
| Matriz de rutas | 355 ms | 214 ms |
| Tarjeta de recompra | 118 ms | 140 ms |
| Tabla de cohortes | 114 ms | 121 ms |
| Ventas por mes (Comercial) | 107 ms | 90 ms |
| **Las 46** | **4.320 ms** | **2.231 ms** |

Las que no usan el cruce quedan igual, dentro del ruido de la medición (±20 ms).

## 5. Best Practice Analyzer: lo que queda

De 126 avisos quedan 72. Los 54 que bajaron son las columnas quitadas, las claves marcadas, el decimal con coma flotante, las jerarquías de atributos, las dos relaciones inactivas (§3.4) y tres descripciones que faltaban en las columnas de los controles. Los que quedan no aplican a este modelo o son decisiones tomadas:

| Regla | Avisos | Por qué no se cambia |
|---|---:|---|
| Formato de enteros con separador de miles y sin decimales | 18 | La regla deduce el tipo por el nombre o el formato. Las marcadas son puntajes, días promedio o variaciones, que necesitan decimales. |
| Formato de porcentajes con separador de miles | 15 | Ya tienen un decimal; el separador de miles no aparece en un porcentaje. |
| Roles sin miembros | 7 | Los miembros se asignan en el servicio de Power BI, al publicar (Fase 11). |
| Nombres con mayúscula inicial | 7 | `dim_` y `fact_` son la convención del modelo dimensional desde la Fase 4. |
| Columnas sin el nombre de la tabla | 7 | Son los filtros de los roles (`[Región] = "Sur"`): es la sintaxis que genera el editor de roles de Power BI, y la tabla es implícita. |
| Tablas sin relaciones | 5 | Los tres controles y `_Medidas` no se relacionan por diseño, y `Gerentes` tampoco (D-022). |
| Tablas calculadas | 4 | Las mismas: tablas de 1 a 50 filas para los controles. |
| Jerarquías de atributos | 4 | `Gerentes` y `_Medidas`: 0,05 MB entre las dos. |
| Columnas sin uso | 2 | `Gerentes[Nombre]` identifica a cada gerente cuando se audita la seguridad, y `_Medidas[Oculta]` existe porque una tabla necesita al menos una columna. |
| Medidas sin formato | 2 | Devuelven texto (el título dinámico y el vendedor elegido). |
| Columna visible en un hecho | 1 | `Puntaje de reseña` es el eje del gráfico de puntajes: visible a propósito. |

## 6. Lo que no se hizo

- **Quitar `cliente_key` de `fact_items`.** Hoy es la columna más pesada (3,4 MB de 9,9), y ninguna página cruza las ventas con la cohorte del cliente. Pero quitarla rompe la dimensión compartida: `Clientes únicos` por categoría o vendedor dejaría de funcionar. La memoria que se ahorra no justifica perder esa capacidad.
- **Agregaciones o tablas resumidas.** Con 112 mil filas y el peor visual en 1,5 s, no hace falta.

## 7. Qué protege que no se rompa

Tests en [tests/test_modelo_semantico.py](../tests/test_modelo_semantico.py), que corren en el CI:

- Ningún hecho ni dimensión carga `pedido_id`, `customer_unique_id`, `product_id` ni `seller_id`.
- Las dos `pedido_key` son enteras, y todos los `TREATAS` cruzan por ellas.
- Las columnas ocultas de los hechos no tienen jerarquía de atributos (Power BI podría volver a activarlas al guardar).
- Las claves de las dimensiones están marcadas y `dias_entrega` es decimal fijo.
- Cada relación inactiva la activa alguna medida con `USERELATIONSHIP`.

La clave foránea `fact_items(pedido_key) → fact_pedidos(pedido_key)` hace fallar la carga si un ítem apunta a un pedido que no existe.

Desde la Fase 11, el **Best Practice Analyzer también corre en el CI**, en cada pull request: Tabular Editor 2 revisa los archivos TMDL, sin Power BI ni datos, y [src/bpa.py](../src/bpa.py) compara el resultado con [powerbi/bpa_excepciones.json](../powerbi/bpa_excepciones.json), los avisos de §5 con su motivo. Un aviso nuevo hace fallar el CI, y también una excepción que ya no aparece, para que la lista no quede vieja.
