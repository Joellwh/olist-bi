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
