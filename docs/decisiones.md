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
