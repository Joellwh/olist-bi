# Olist BI: del dato crudo al tablero

Solución de Business Intelligence completa sobre el e-commerce brasileño Olist: unos 100 mil pedidos reales en 9 tablas relacionadas.

**Stack:** Python (ETL y validación) · SQL Server (modelo dimensional) · Power BI (modelo semántico, DAX, RLS) · GitHub Actions (CI)

En construcción. Estado actual: **Fase 5, SQL analítico y optimización**. Ver el [roadmap](docs/roadmap.md).

## Arquitectura

```
CSV (Kaggle) ──► Python ETL ──► SQL Server ─────────────────────────► Power BI
                   │              raw ► stg ► dw (estrella) ► rpt       modelo semántico
                   └─ validaciones y log (etl)                          DAX · RLS · reportes
```

## Cómo ejecutarlo

Requisitos: Python 3.12, SQL Server (Express alcanza), ODBC Driver 18 for SQL Server y Power BI Desktop.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

python -m src.setup.extract_data "ruta/al/archive.zip"   # datos: ver data/README.md
python -m src.setup.create_database                      # base OlistDW, esquemas y tablas de log
python -m src.setup.check_environment                    # verifica que todo esté listo
python -m src.etl.run                                    # ETL: CSV -> raw -> stg -> dw -> rpt, con validaciones
pytest
```

Para usar otro servidor u otra base: variables de entorno `OLIST_SQL_SERVER`, `OLIST_SQL_DATABASE` y `OLIST_SQL_DRIVER` (ver `src/config.py`).

## Estructura

```
data/raw/        CSV de Olist (no versionados)
src/setup/       preparación del entorno
src/etl/         pipeline de extracción, limpieza y carga
sql/00_setup/    creación de la base y esquemas
sql/01_raw ...   un directorio por capa: raw, staging, dw, vistas
powerbi/         proyecto Power BI (formato PBIP, versionable)
docs/            requerimientos, KPIs, modelo y registro de decisiones
tests/           tests (corren en el CI)
```

## Documentación

- [Roadmap](docs/roadmap.md)
- [Requerimientos de negocio](docs/01_requerimientos.md)
- [Diccionario de KPIs](docs/kpi_diccionario.md)
- [Calidad de datos](docs/02_calidad_datos.md)
- [ETL](docs/etl.md)
- [Modelo dimensional](docs/03_modelo_dimensional.md)
- [SQL analítico y optimización](docs/04_optimizacion_sql.md)
- [Registro de decisiones](docs/decisiones.md)
- [Datos: origen y tablas](data/README.md)
