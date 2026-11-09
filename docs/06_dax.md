# Medidas DAX

**Fase:** 7 · **Medidas:** [powerbi/olist.SemanticModel/definition/tables/_Medidas.tmdl](../powerbi/olist.SemanticModel/definition/tables/_Medidas.tmdl) · **Control:** [DAXQueries/Control KPIs.dax](../powerbi/olist.SemanticModel/DAXQueries/Control%20KPIs.dax)

41 medidas en la tabla `_Medidas`, organizadas en carpetas. Cada una implementa un KPI del [diccionario](kpi_diccionario.md), y su descripción empieza con el código (K01, K02…), así que se puede rastrear desde el tablero hasta la definición de negocio.

| Carpeta | Medidas | Ejemplos |
|---|---:|---|
| 1. Comercial | 13 | Ventas, Pedidos, Ticket, Ventas año anterior, Var. interanual, Acumulado del año, Media móvil, Participación |
| 2. Logística | 9 | Flete, % a tiempo, Días de entrega (promedio y mediana), Demora, Cancelación |
| 3. Cliente | 7 | Puntaje, % reseñas negativas y positivas, Recompra (K25 y K28), Brecha por demora, Retención de cohorte |
| 4. Variación interanual | 4 | De Pedidos, Ticket, % a tiempo y Puntaje |
| 5. Cruce con vendedor y producto | 5 | % a tiempo, días, puntaje y reseñas negativas por vendedor o categoría; demora por ruta |
| 6. Interactivas | 3 | Top N dinámico de vendedores, Selector de métrica |

Además hay tres tablas sin relaciones que alimentan los controles del tablero: `Top N` (1 a 50), `Selector de métrica` y `Meses desde cohorte` (0 a 25).

## Patrones usados

- **Variables (`VAR`) en las medidas con más de un paso:** se leen como una receta, y cada parte se calcula una sola vez.
- **`DIVIDE` en lugar de `/`:** devuelve vacío en vez de error cuando el denominador es 0.
- **Las reglas de negocio vienen de SQL:** las medidas filtran por `es_venta`, `es_valido`, `es_entregado` y `a_tiempo`, que se calcularon una sola vez en la base (D-016). Ninguna medida repite la lógica de qué es una venta.
- **Inteligencia de tiempo con `dim_fecha` marcada como tabla de fechas:** `SAMEPERIODLASTYEAR`, `TOTALYTD`, `DATESINPERIOD`.
- **`TREATAS` para cruzar los dos hechos sin relación física** (D-014): el % a tiempo de un vendedor toma sus pedidos desde `fact_items` y los aplica sobre `fact_pedidos`.
- **`ALLSELECTED`** para la participación sobre el total visible, y **`RANKX`** para el Top N.

## Cómo se verificó

La consulta `Control KPIs.dax`, guardada en el proyecto, calcula 34 valores y los compara con su referencia. Muestra **OK** o **REVISAR** en cada fila:

- Los KPIs del diccionario, contra `src/kpi_reference.py`, que los calcula con pandas sobre los CSV.
- La media móvil, la retención de cohortes y el vendedor con más ventas, contra las vistas `rpt` de SQL. Esto prueba que `TREATAS` en DAX da lo mismo que el cruce equivalente en SQL.

Resultado: **34 de 34 en OK.** Lo que el control no cubre (Top N, Selector de métrica, variaciones interanuales de Pedidos, Ticket, % a tiempo y Puntaje, y el cruce por categoría) se verifica en los visuales de la Fase 8.

Además, [tests/test_modelo_semantico.py](../tests/test_modelo_semantico.py) revisa en cada push que cada KPI del diccionario tenga su medida, y que ninguna medida caiga en las trampas de abajo.

## Trampas de los vacíos

DAX trata un valor vacío (`BLANK`) como 0 o como falso cuando lo compara, y **no da error**: el número simplemente sale distinto. El proyecto tiene tres casos, y los tres aparecieron trabajando:

| Comparación | Resultado en DAX | Dónde aparece | Protección |
|---|---|---|---|
| vacío `= FALSE()` | verdadero | `a_tiempo` es vacía en los pedidos no entregados. K20 dio **8.238 en lugar de 6.531** en la primera verificación (Fase 6) | Toda medida con `a_tiempo` filtra además `es_entregado`. Lo controla un test. |
| vacío `<= 2` | verdadero | `puntaje_resena` es vacía en los pedidos sin reseña: se contarían como negativos | Rango explícito `>= 1 && <= 2`. Lo controla un test. |
| vacío `= 0` | verdadero | `meses_desde_primera_compra` es vacía en los pedidos no válidos: el tamaño de cada cohorte incluiría clientes que solo cancelaron | La medida filtra `es_valido`. |

## Dependencia circular: el caso reproducido

**El error.** Se creó en el modelo real, en la tabla `Selector de métrica`, y no se guardó. Dos columnas calculadas, idénticas y que no se mencionan entre sí:

```dax
Prueba A = CALCULATE ( SUM ( 'Selector de métrica'[Orden] ) )
Prueba B = CALCULATE ( SUM ( 'Selector de métrica'[Orden] ) )
```

La primera funciona. La segunda da este error:

> A circular dependency was detected: Selector de métrica[Columna], Selector de métrica[Prueba A], Selector de métrica[Columna].

**Por qué ocurre.** En una columna calculada, `CALCULATE` convierte la fila actual en un filtro sobre **todas** las columnas de la tabla. Esto se llama transición de contexto. Por eso `Prueba B` depende de `Prueba A`, y `Prueba A` depende de `Prueba B`. La dependencia no se ve al leer las fórmulas, y por eso el error confunde. Pasa en tablas sin clave: si la tabla tuviera una columna marcada como clave única, la transición de contexto filtraría solo por esa columna.

**La solución que se probó.** Limitar el filtro de `CALCULATE` a la columna que importa:

```dax
Prueba B = CALCULATE ( SUM ( 'Selector de métrica'[Orden] ), ALLEXCEPT ( 'Selector de métrica', 'Selector de métrica'[Orden] ) )
```

`ALLEXCEPT` saca el filtro de todas las columnas salvo `Orden`, incluida `Prueba A`, y se corta el círculo. Las dos columnas mostraron 1, 2, 3 y 4.

**Por qué el modelo no tiene este problema.** No tiene columnas calculadas en las tablas de datos: las reglas de negocio se calculan en SQL (D-016) y todo lo demás son medidas, que no tienen transición de contexto al cargar. La prevención está en el diseño, no en acordarse de usar `ALLEXCEPT`.

## Optimización con DAX Studio

**Método.** Se midieron 4 consultas que simulan visuales del tablero, con **Server Timings** y la caché borrada antes de cada corrida (**Clear on Run**). El motor de fórmulas (FE) procesa con un solo hilo; el de almacenamiento (SE) lee los datos comprimidos y es rápido. Cuando el FE domina, la medida es candidata a reescribirse.

| Consulta | Total | FE | SE | Consultas al SE |
|---|---:|---:|---:|---:|
| Tabla de cohortes (`Retención de cohorte`) | 1.170 ms | 892 ms (76%) | 278 ms | 31 |
| Matriz de rutas (`Días de demora por ruta`) | 584 ms | 497 ms (85%) | 87 ms | 6 |
| Recompra por estado (`Tasa de recompra`) | 80 ms | 22 ms (28%) | 58 ms | 3 |
| Top N vendedores (`Ventas Top N vendedores`) | 63 ms | 42 ms (67%) | 21 ms | 3 |

Se optimizaron las dos primeras. Recompra y Top N tardan menos de 100 ms, y en la recompra la mayor parte del tiempo es del motor de almacenamiento: reescribirlas no ganaría nada perceptible.

### Cohortes: de 1.170 a 105 ms

- **Antes:** por cada una de las 220 celdas (cohorte × mes), la medida calculaba el mes objetivo con aritmética de fechas y filtraba `dim_fecha` dos veces.
- **Cambio:** los meses desde la primera compra se calculan **una vez, en SQL**, como columna de `fact_pedidos` (`meses_desde_primera_compra`). La medida quedó en un filtro simple sobre esa columna.
- **Por qué es correcto:** es el mismo criterio de D-016, porque es una regla del pedido, no un cálculo de visualización. Antes de tocar la medida, se verificó en SQL que la columna nueva reproduce exactamente las 220 celdas de `rpt.cohortes`.

### Rutas: de 584 a 407 ms

- **Antes:** la medida armaba dos veces la lista de pedidos de la ruta (unos 96.000 identificadores de texto): una para contar los pedidos y otra para promediar la demora.
- **Cambio:** la lista se arma una vez en una variable y se reutiliza.
- **Lo que queda:** el FE sigue siendo el 79% del tiempo, porque el cruce es por `pedido_id`, un texto de 32 caracteres. El paso siguiente sería una clave numérica de pedido en SQL; queda para la Fase 10.

### Resultado

| Consulta | Antes | Después | FE antes → después | Filas |
|---|---:|---:|---:|---|
| Cohortes | 1.170 ms | **105 ms** | 892 → 38 ms | 220 en las dos |
| Rutas | 584 ms | **407 ms** | 497 → 321 ms | 116 en las dos |

Una medición por consulta en cada caso, en la PC de desarrollo. La mejora de cohortes es de un orden de magnitud. La de rutas (30%) puede variar algunos milisegundos entre corridas. En las dos, la cantidad de filas no cambió, y el control de 34 KPIs siguió en OK.
