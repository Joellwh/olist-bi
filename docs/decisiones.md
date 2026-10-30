# Registro de decisiones

Cada decisión importante del proyecto: qué se eligió, por qué y qué alternativas se descartaron. Las más nuevas van abajo.

---

## D-001 · SQL Server como base del proyecto

**Fecha:** 2026-09-26 · **Fase:** 0

**Decisión:** usar SQL Server 2022 Express local como base de datos.

**Por qué:** es el motor más común en empresas que trabajan con Power BI, se integra de forma nativa (conector, modo DirectQuery, autenticación de Windows) y las habilidades que se practican (T-SQL, planes de ejecución, índices columnstore) son las mismas que en un entorno productivo.

**Descartadas:**
- *PostgreSQL:* excelente, pero menos habitual en stacks Microsoft.
- *SQLite o DuckDB:* no permiten practicar seguridad, esquemas ni planes de ejecución como en un servidor real.

**Limitación conocida:** Express limita cada base a 10 GB. Olist ocupa bastante menos.

---

## D-002 · Una capa por esquema: raw → stg → dw → rpt

**Fecha:** 2026-09-26 · **Fase:** 0

**Decisión:** separar las capas del pipeline en esquemas de una misma base:

| Esquema | Contenido | Quién escribe |
|---|---|---|
| `raw` | CSV tal cual, sin transformar | ETL Python |
| `stg` | Datos limpios y tipados | ETL |
| `dw` | Modelo dimensional (dimensiones y hechos) | ETL |
| `rpt` | Vistas analíticas | Scripts SQL |
| `etl` | Log de ejecuciones y validaciones | ETL |

**Por qué:** cada capa tiene una responsabilidad clara. Si un número da mal en Power BI, se puede rastrear hacia atrás capa por capa hasta el CSV original. Los esquemas también permiten dar permisos por capa, por ejemplo que Power BI lea solo `dw` y `rpt`.

**Descartada:** *una base por capa.* Agrega complejidad (consultas entre bases, más backups) sin beneficio a esta escala.

---

## D-003 · Los CSV crudos no se versionan

**Fecha:** 2026-09-26 · **Fase:** 0

**Decisión:** `data/raw/` está en `.gitignore`. La reproducibilidad se garantiza con `src/setup/extract_data.py`, que verifica la cantidad de filas de cada archivo contra valores fijados en `src/paths.py`.

**Por qué:** 126 MB de datos con licencia de terceros no pertenecen a un repo de código. El conteo de filas detecta si alguien usa una versión distinta del dataset.

---

## D-004 · Conexión configurable por variables de entorno

**Fecha:** 2026-09-26 · **Fase:** 0

**Decisión:** servidor, base y driver se leen de variables de entorno (`OLIST_SQL_*`), con valores por defecto para el entorno local. Los scripts SQL usan `$(DB_NAME)` en vez de un nombre fijo.

**Por qué:** en la Fase 11 el mismo código tiene que poder apuntar a `OlistDW_dev` y a `OlistDW_prod` sin editar archivos. Es la base del circuito de despliegue.

---

## D-005 · Qué pedidos cuentan como venta

**Fecha:** 2026-10-23 · **Fase:** 1

**Decisión:** una venta es todo pedido salvo los de estado `canceled` y `unavailable`. Se agrega el KPI aparte *Ventas entregadas* (K13) para conciliar con Logística.

**Por qué:** en e-commerce la venta se reconoce al confirmar el pedido, no al entregarlo. Si se contaran solo los entregados, los 1.107 pedidos en camino de los últimos meses quedarían afuera y la tendencia final caería artificialmente. `unavailable` se excluye porque son pedidos sin stock que casi nunca tienen ítems (603 de 609).

**Descartadas:**
- *Solo entregados:* conservador, pero distorsiona el cierre del período.
- *Todos los pedidos:* infla las ventas con pedidos que nunca se cobraron.

**Impacto:** quedan 97.910 pedidos válidos de 99.092 en el período.

---

## D-006 · El flete no forma parte de la venta

**Fecha:** 2026-10-23 · **Fase:** 1

**Decisión:** Ventas = suma del precio de los productos. El flete se mide en sus propios KPIs (K14 y K15).

**Por qué:** el flete es el 16,6% de la venta y lo cobra Olist para pagarle al transportista: mezclarlo con el precio haría que una suba de tarifas logísticas parezca crecimiento comercial. Separados, Comercial mira productos y Logística mira costos.

**Descartada:** *venta = precio + flete* (lo que pagó el cliente). Coincide con la tabla de pagos, pero mezcla ingreso con costo logístico.

---

## D-007 · "A tiempo" contra la fecha estimada, por día

**Fecha:** 2026-10-23 · **Fase:** 1

**Decisión:** un pedido llega a tiempo si la fecha de entrega, sin la hora, es menor o igual a la fecha estimada que se le informó al cliente. Resultado: 93,2% a tiempo.

**Por qué:** es la promesa que vio el cliente, y por eso es lo que se relaciona con la reseña (4,29 puntos a tiempo contra 2,27 tarde). La fecha estimada del dataset no tiene hora, así que comparar con hora marcaría como tardía una entrega del mismo día por la tarde.

**Descartadas:**
- *SLA fijo en días:* compara regiones con la misma vara, pero ignora lo prometido. Se puede agregar más adelante como KPI nuevo.
- *Comparación con hora:* 91,9% a tiempo, más estricto de lo que vive el cliente.

---

## D-008 · Período de análisis: ene-2017 a ago-2018

**Fecha:** 2026-10-23 · **Fase:** 1

**Decisión:** los tableros y KPIs usan compras entre el 2017-01-01 y el 2018-08-31. Los meses de los bordes se cargan igual en la base, pero no se muestran.

**Por qué:** 2016 tiene meses casi vacíos (4 pedidos en septiembre, 1 en diciembre, ninguno en noviembre) y septiembre y octubre de 2018 tienen 20 pedidos entre los dos. Incluirlos distorsiona tendencias, medias móviles y variaciones interanuales. Con 20 meses completos se puede comparar ene–ago 2018 contra ene–ago 2017.

**Descartada:** *todo el período.* No esconde nada, pero los primeros y últimos meses producen picos y caídas que no son reales.

**Implementación pendiente:** el filtro se aplica en el modelo (Fase 4 o 6), no borrando datos en el ETL, para que la base siga siendo una copia fiel del origen.

---

## D-009 · Los problemas de calidad se clasifican por gravedad

**Fecha:** 2026-10-27 · **Fase:** 2

**Decisión:** cada problema de calidad es crítico, advertencia o informativo ([02_calidad_datos.md](02_calidad_datos.md)). Una regla crítica que falla **corta la carga**; una advertencia se registra con la cantidad de filas afectadas y la carga sigue.

**Por qué:** si todo cortara la carga, el pipeline nunca terminaría por problemas que afectan a 8 filas de 99 mil. Si nada la cortara, un error que cambia los totales (como perder los ceros de los códigos postales) llegaría al tablero sin que nadie lo note. Las críticas son las que hacen que un KPI dé mal.

**Descartada:** *corregir todo en silencio.* Deja un dataset prolijo, pero nadie se entera de que el origen tiene problemas ni de si empeoran.

---

## D-010 · Geolocalización: una fila por código postal

**Fecha:** 2026-10-27 · **Fase:** 2

**Decisión:** `geolocation` se reduce de 1.000.163 filas a una por código postal (19.015). Coordenadas: mediana de latitud y longitud. Ciudad y estado: el valor más frecuente. Antes se descartan los 42 puntos fuera de Brasil.

**Por qué:** la tabla es una lista de puntos con muchas repeticiones (mediana de 29 por código postal), así que no se puede usar como dimensión: unirla con clientes multiplicaría filas igual que en Q12. La mediana no se deja arrastrar por los puntos mal cargados que queden; el promedio sí.

**Descartadas:**
- *Tomar el primer punto de cada código:* arbitrario; depende del orden del archivo.
- *No usar la tabla:* los mapas por estado no la necesitan, pero tenerla permite un mapa por ciudad más adelante, y cuesta poco.

---

## D-011 · Categorías en español con una tabla propia

**Fecha:** 2026-10-27 · **Fase:** 2

**Decisión:** las categorías se muestran en español, con una tabla propia (`data/seeds/categorias.csv`, versionada en el repo) que traduce las 73 categorías del portugués. Los productos sin categoría van a "Sin categoría".

**Por qué:** el tablero es para usuarios de habla hispana. La tabla de traducción de Olist está en inglés y le faltan 2 categorías (Q18). Una tabla propia resuelve las dos cosas, y al ser un archivo chico y nuestro, se versiona con el código.

**Descartada:** *usar la traducción al inglés de Olist.* Mezcla idiomas en el tablero y deja 13 productos sin nombre de categoría.

---

## D-012 · Carga completa en cada ejecución

**Fecha:** 2026-10-27 · **Fase:** 3

**Decisión:** cada ejecución del ETL vacía las tablas de `raw` y `stg` y las vuelve a llenar desde los CSV. No hay carga incremental.

**Por qué:** el dataset es estático (no llegan pedidos nuevos) y la carga completa tarda alrededor de un minuto y medio. Es la forma más simple de que el pipeline sea **idempotente**: correrlo dos veces deja exactamente el mismo resultado, verificado comparando dos ejecuciones seguidas.

**Descartada:** *carga incremental* (solo lo nuevo o modificado). Es lo que haría falta con datos que crecen todos los días, pero exige detectar cambios y borrados, y acá no hay ninguno. Si el proyecto pasara a un origen vivo, la clave para hacerla sería la fecha de compra de los pedidos.

---

## D-013 · raw como texto, limpieza en T-SQL, orquestación en Python

**Fecha:** 2026-10-27 · **Fase:** 3

**Decisión:**
- `raw` guarda todo como texto, tal cual viene del CSV.
- `stg` se construye con scripts **T-SQL** (`sql/02_staging/`): tipos, deduplicación, normalización.
- **Python** lee los CSV, los inserta en `raw`, ejecuta los scripts en orden, corre las validaciones y registra todo.

**Por qué:**
- Con `raw` como texto, la carga nunca falla por un valor mal formado: el problema aparece al tiparlo en `stg`, con un error claro y en el lugar donde se decide qué hacer.
- La limpieza en SQL es visible y se puede revisar desde SSMS, opera sobre conjuntos completos (no fila por fila) y es la habilidad de SQL que pide el puesto.
- Python hace lo que SQL Server no puede hacer bien solo: leer archivos, orquestar pasos y testear.

**Descartada:** *limpiar todo con pandas y cargar directo a `stg`.* Es más rápido de escribir, pero la lógica queda fuera de la base: quien abra SSMS ve tablas limpias sin saber cómo llegaron ahí.

**Consecuencia:** la normalización de texto existe dos veces, en Python (para el perfilado) y en T-SQL (para `stg`). Un test de integración compara las dos sobre todas las ciudades del dataset. Ese test encontró un bug real en la versión SQL (ver [docs/etl.md](etl.md)).

---

## D-014 · Dos tablas de hechos y TREATAS para cruzarlas

**Fecha:** 2026-10-27 · **Fase:** 4

**Decisión:** el modelo tiene dos tablas de hechos, `fact_items` (ítem) y `fact_pedidos` (pedido), que comparten dimensiones pero no se relacionan entre sí. Cuando hace falta cruzar algo del ítem (el vendedor) con algo del pedido (la entrega), se usa `TREATAS` en DAX.

**Por qué:** cada métrica vive en su granularidad natural, así que ningún promedio queda sesgado por pedidos con muchos ítems. `TREATAS` aplica los pedidos de un vendedor como filtro sobre `fact_pedidos` sin una relación física: un pedido con dos vendedores cuenta para cada uno (Q13) y el total sigue contando cada pedido una vez.

**Descartadas:**
- *Un tercer hecho a nivel pedido × vendedor:* resuelve el cruce, pero es otra tabla que cargar, validar y mantener sincronizada para un caso que afecta al 1,3% de los pedidos.
- *Una tabla puente con filtro bidireccional:* es la solución "de manual" para muchos a muchos, pero el filtro bidireccional crea caminos ambiguos y es más lento. El roadmap lo descarta desde el principio.
- *Repetir los datos de entrega en cada ítem:* sesga los promedios hacia los pedidos con más ítems.

---

## D-015 · El cliente es la persona y la ubicación es la del pedido

**Fecha:** 2026-10-27 · **Fase:** 4

**Decisión:** `dim_cliente` tiene una fila por persona (`customer_unique_id`) y no guarda ubicación. El estado del cliente va en `dim_geografia`, apuntada desde cada hecho con el estado **de ese pedido**.

**Por qué:** una persona puede comprar desde distintos domicilios. Si la ubicación estuviera en `dim_cliente`, habría que elegir una (la última, la primera) y los pedidos viejos quedarían asignados a un estado donde no ocurrieron. Con la geografía en el hecho, cada pedido queda en su lugar, y la seguridad por fila de la Fase 9 filtra por el estado real de cada venta.

**Descartada:** *`dim_cliente` a nivel `customer_id`* (una fila por pedido, como viene en el origen). Conserva la ubicación de cada pedido, pero la dimensión deja de representar a la persona: contar clientes o calcular la recompra exigiría un conteo distinto sobre otra columna en cada medida.

---

## D-016 · Las reglas de negocio se calculan una vez, en SQL

**Fecha:** 2026-10-27 · **Fase:** 4

**Decisión:** las reglas del diccionario de KPIs (es venta, a tiempo, días de demora, última reseña) se calculan al construir `fact_pedidos` y quedan como columnas. Las medidas DAX las usan en vez de recalcularlas.

**Por qué:** una regla escrita en un solo lugar no puede divergir. Además queda disponible para cualquier herramienta que lea la base, no solo para Power BI, y se puede testear con SQL: los 13 KPIs calculados sobre `dw` coinciden con los valores de referencia.

**Descartada:** *calcular las reglas en DAX con columnas calculadas o dentro de cada medida.* Funciona, pero la regla quedaría repetida en varias medidas, y las columnas calculadas ocupan memoria en el modelo y son una fuente típica de dependencias circulares (justamente el tema de la Fase 7).

---

## D-017 · Índices: columnstore más dos índices puntuales

**Fecha:** 2026-10-30 · **Fase:** 5

**Decisión:** las tablas de hechos tienen un índice columnstore no agrupado cada una, más dos índices comunes: `fact_pedidos (cliente_key)` y `fact_items (vendedor_key)`. Se crean al final de la carga (`sql/03_dw/90_indices.sql`).

**Por qué:** se midieron 5 estrategias con 7 consultas representativas ([04_optimizacion_sql.md](04_optimizacion_sql.md)). El columnstore reduce entre 2 y 19 veces las lecturas de las agregaciones y, al habilitar el modo batch, baja la vista RFM de 403.266 a 566 lecturas. Pero recorre la tabla entera en las búsquedas puntuales, y para eso están los dos índices comunes. Esta combinación iguala en todas las consultas a la que agrega cinco índices comunes, con la mitad de espacio.

**Descartadas:**
- *Solo índices comunes en todas las claves foráneas:* mejoran las búsquedas puntuales, pero casi no ayudan a las agregaciones y no tocan el problema de la RFM.
- *Columnstore agrupado* (reemplazando la clave primaria agrupada): ahorra más espacio, pero el modelo necesita la clave primaria para las relaciones y para garantizar unicidad. Con 100 mil filas, la diferencia no lo justifica.

**Contexto:** Power BI va a usar el modo Import (Fase 6), que lee las tablas enteras una vez por actualización. Estos índices sirven a las vistas `rpt`, a consultas directas desde SSMS y a un eventual DirectQuery.
