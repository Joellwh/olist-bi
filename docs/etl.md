# ETL: de los CSV al modelo dimensional

**Fase:** 3 (y 4 para la capa dw) · **Código:** [src/etl/](../src/etl/) · **SQL:** [sql/01_raw/](../sql/01_raw/), [sql/02_staging/](../sql/02_staging/), [sql/03_dw/](../sql/03_dw/)

## Cómo se corre

```bash
python -m src.setup.create_database   # una vez: base, esquemas y tablas de log
python -m src.etl.run                 # el pipeline completo (~2 minutos)
pytest                                # incluye los tests contra SQL Server si está disponible
```

El comando termina con código 0 si la carga salió bien y con 1 si falló, así lo puede usar un programador de tareas.

## Qué hace, paso a paso

```
CSV (data/raw) ─┐
seeds ──────────┴─► 1. raw.*  ──► 2. validaciones raw ──► 3. stg.*  ──► 4. validaciones stg ──► 5. dw.*  ──► 6. validaciones dw
                      texto,        V01 V02 V07             tipos,         V03 V04 V05 V06 V08      estrella      V08
                      tal cual      (+ V12 V14 avisos)      limpieza       (+ V09 V10 V11 V13)                    (+ V15)
                                                     │
                     todo queda en etl.log_ejecucion / log_paso / log_validacion
```

1. **raw:** recrea las tablas (`sql/01_raw/`) y carga cada CSV entero como texto, en una transacción por tabla. Antes de cargar verifica que el CSV tenga las mismas columnas que la tabla.
2. **Validaciones sobre raw:** cantidad de filas, claves únicas y formato de los códigos postales. Van antes de `stg` porque `stg` tiene claves primarias, y un duplicado haría fallar el INSERT con un error poco claro.
3. **stg:** ejecuta en orden los scripts de `sql/02_staging/`: primero la función de normalización y las tablas, después una carga por tabla.
4. **Validaciones sobre stg:** integridad referencial, rangos, fechas y conciliación de filas y montos contra `raw`.
5. **dw:** construye el modelo en estrella (`sql/03_dw/`): dimensiones primero, hechos después. Ver [03_modelo_dimensional.md](03_modelo_dimensional.md).
6. **Validaciones sobre dw:** un hecho por pedido y por ítem, ventas y flete iguales a `raw`, y ningún hecho en el miembro Desconocido.

Si una validación **crítica** falla, la ejecución se corta y queda como `FALLA`. Las **advertencias** se registran con la cantidad de filas y la carga sigue ([D-009](decisiones.md#d-009--los-problemas-de-calidad-se-clasifican-por-gravedad)).

## Qué se limpia en stg

| Tabla | Limpieza | Problema |
|---|---|---|
| `stg.geolocation` | De 1.000.163 puntos a una fila por código postal (19.010): mediana de coordenadas, ciudad más frecuente, sin puntos fuera de Brasil | Q01, D-010 |
| `stg.customers`, `stg.sellers` | Código postal como `CHAR(5)`; ciudad normalizada; las 28 ciudades de vendedores inválidas se reemplazan por la de su código postal | Q20, Q03 |
| `stg.categorias` | Nombres en español desde `data/seeds/categorias.csv` | Q18, D-011 |
| `stg.products` | Columnas `lenght` corregidas; peso 0 pasa a nulo | Q19, Q17 |
| `stg.orders`, `stg.order_items`, `stg.order_payments` | Tipos (`DATETIME2`, `DECIMAL` para montos); 0 cuotas pasa a 1 | Q15 |
| `stg.order_reviews` | Clave `review_id + order_id`; marca de la última reseña de cada pedido y de las creadas antes de la compra | Q04, Q05, R7 |

## Revisar una ejecución

```sql
-- Últimas ejecuciones
SELECT ejecucion_id, inicio, estado, DATEDIFF(SECOND, inicio, fin) AS segundos, mensaje
FROM etl.log_ejecucion ORDER BY ejecucion_id DESC;

-- Advertencias de la última ejecución
SELECT codigo, descripcion, filas_afectadas
FROM etl.log_validacion
WHERE ejecucion_id = (SELECT MAX(ejecucion_id) FROM etl.log_ejecucion) AND resultado <> 'OK';
```

Con la versión actual del dataset, una ejecución normal da estas advertencias (las mismas cantidades que encontró el perfilado de la Fase 2):

| Código | Advertencia | Filas |
|---|---|---|
| V09 | Fechas intermedias desordenadas | 1.382 |
| V13 | Productos sin categoría | 610 |
| V11 | Reseñas creadas antes de la compra | 64 |
| V14 | Puntos de geolocalización fuera de Brasil | 42 |
| V12 | Pagos raros (not_defined, valor 0, 0 cuotas) | 11 |
| V10 | Pedidos entregados sin fecha de entrega | 8 |

Si alguno de esos números cambia sin que haya cambiado el dataset, algo se rompió en el camino.

## Cómo se verifica que la limpieza no cambió los números

`tests/test_integracion_sql.py` corre contra SQL Server y compara dos implementaciones independientes:

- **KPIs:** calcula 7 KPIs en SQL sobre `stg` y los compara con [`src/kpi_reference.py`](../src/kpi_reference.py), que los calcula con pandas directamente sobre los CSV. Coinciden al centavo.
- **Normalización de texto:** compara la función T-SQL con la de Python sobre todas las ciudades del dataset.

## Dos hallazgos de esta fase

**1. La carga era 12 veces más lenta de lo necesario.** La primera versión tardaba 7 minutos en cargar `raw`, 4,5 de ellos en la geolocalización. Medido sobre 20 mil filas:

| Estrategia | Filas por segundo |
|---|---|
| Confirmar cada lote (autocommit) | 1.810 |
| Una transacción por tabla | 25.114 |
| Transacción + tipos declarados (`setinputsizes`) | 49.944 |

Con los dos cambios, `raw` carga en 36 segundos. La transacción por tabla además mejora el diseño: si algo falla a mitad de camino, la tabla queda como estaba, no cargada a medias.

**2. Un bug de T-SQL que solo un test podía encontrar.** La función de normalización usaba el patrón `[^a-z0-9 '-]` para encontrar caracteres no permitidos. En Python el guion al final de la clase es literal; en T-SQL se interpreta como un rango y el patrón deja de encontrar nada, **sin dar error**: `"sbc/sp"` pasaba sin limpiar. El test que compara SQL con Python lo detectó en 41 ciudades. Solución: el guion va primero, `[^-a-z0-9 ']`. El mismo test encontró después tres diferencias menores (tildes escritas como carácter aparte, `³` y `´`), que también se corrigieron.
