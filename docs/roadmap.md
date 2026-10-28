# Roadmap: Olist, de los datos al tablero

**Duración estimada:** 7 a 9 semanas, 1 a 2 horas por día. Cada fase termina en un entregable que queda en el repo.

**Stack:** Python (ETL y validación), SQL Server (base y modelo dimensional), Power BI Desktop (modelo semántico, DAX, RLS y reportes) y Git/GitHub (versionado, CI y gestión).

**Orden y dependencias**

```
0 → 1 → 2 → 3 → 4 → 5 ─┐
                  └──→ 6 → 7 → 8 → 9 → 10 → 11
```

La Fase 5 puede avanzar en paralelo con la 6 una vez terminada la 4.

---

## Fase 0: Preparación — ✅ hecha (2026-09-26)

- [x] Dataset de Kaggle descargado y extraído en `data/raw/` (9 CSV, conteo de filas verificado).
- [x] Repo local `olist-bi` con la estructura de carpetas.
- [x] Base `OlistDW` en `.\SQLEXPRESS` con esquemas `raw`, `stg`, `dw`, `rpt` y `etl` (script idempotente).
- [x] Entorno `.venv` (pandas, pyodbc, sqlalchemy, pytest), verificador de entorno (21/21 OK), 8 tests y workflow de CI.
- [x] README, `data/README.md`, `docs/decisiones.md` y primer commit.
- [x] Instalar Jupyter (`notebook` 7.6.1; hubo que reintentar por los cortes de red).
- [x] Power BI Desktop: activar guardado **PBIP** y formato **TMDL**.
- [x] Instalar **DAX Studio**.
- [ ] Instalar **Tabular Editor 2**. Necesario recién en la Fase 10 (Best Practice Analyzer).
- [x] Crear el repo `olist-bi` en GitHub y conectarlo: https://github.com/Joellwh/olist-bi
- [x] GitHub Project con una tarjeta por fase.

## Fase 1: Requerimientos y KPIs — ✅ hecha (2026-10-26)

*Cubre: levantar requerimientos con stakeholders y convertirlos en KPIs.*

- [x] 3 stakeholders ficticios: **Dirección Comercial**, **Logística**, **Experiencia de cliente** (más gerentes regionales para RLS).
- [x] 3 a 5 preguntas de negocio por stakeholder (15 en total).
- [x] Diccionario de KPIs: 27 KPIs con fórmula, origen, granularidad, reglas y valores de referencia (`python -m src.kpi_reference`). Reglas decididas en D-005 a D-008.
- [x] Bocetos de las 5 páginas, con criterios de diseño (`docs/bocetos/`).
- [x] Criterios de aceptación por página.

📦 `docs/01_requerimientos.md`, `docs/kpi_diccionario.md`, `docs/bocetos/`

## Fase 2: Exploración y perfilado — ✅ hecha (2026-10-27)

- [x] Notebook que perfile las 9 tablas (`notebooks/02_perfilado.ipynb`), con funciones testeadas en `src/profiling.py`.
- [x] Problemas conocidos y nuevos: 23 hallazgos (Q01–Q23), entre ellos el código postal que pierde el cero (Q20) y la unión ítems × pagos que infla ventas un 4,5% (Q12).
- [x] Cada problema con gravedad y decisión, más 14 reglas de validación para la Fase 3. Decisiones D-009 a D-011.

📦 `docs/02_calidad_datos.md`

## Fase 3: ETL con Python hacia SQL Server — ✅ hecha (2026-10-27)

*Cubre: Python para transformar, validar y automatizar; capas de extracción y preparación.*

- [x] Extracción de CSV a `raw.*` con `pyodbc` y `fast_executemany`, una transacción por tabla (de 7 minutos a 36 segundos).
- [x] Limpieza en `stg.*` con T-SQL: tipos, deduplicación, normalización de texto, geolocalización por código postal, categorías en español.
- [x] Validación automática con checks propios (V01–V14 del informe de calidad). Si falla una crítica, la carga se corta.
- [x] Log en `etl.log_ejecucion`, `etl.log_paso` y `etl.log_validacion`.
- [x] Idempotente; un único comando: `python -m src.etl.run`. Decisiones D-012 y D-013.
- [x] Tests: unitarios (corren en el CI) y de integración contra SQL Server (KPIs de SQL = KPIs de referencia).

📦 Pipeline reproducible con validaciones y logs: `docs/etl.md`

## Fase 4: Modelo dimensional en SQL Server (3–4 días)

*Cubre: diseñar modelos relacionales.*

- [ ] Matriz de bus.
- [ ] Dimensiones `dw.dim_cliente`, `dim_vendedor`, `dim_producto`, `dim_geografia`, `dim_fecha` (generada por SQL); claves subrogadas y miembro "Desconocido" (-1).
- [ ] Dos hechos con distinta granularidad: `fact_items_pedido` (ítem) y `fact_pedidos` (pedido).
- [ ] PK y FK; diagrama del modelo.

📦 `docs/03_modelo_dimensional.md`

## Fase 5: SQL complejo y rendimiento (3–4 días)

*Cubre: consultas SQL complejas y optimización.*

- [ ] Vistas `rpt.*`: cohortes y retención, recompra (`LAG`), ranking de vendedores (`RANK`, `NTILE`), RFM, variación mensual y acumulado (`SUM() OVER`).
- [ ] `SET STATISTICS IO, TIME ON`, planes de ejecución, índices en FK y fechas, índice columnstore en hechos.
- [ ] Antes y después medidos.

📦 `docs/04_optimizacion_sql.md`

## Fase 6: Modelo semántico en Power BI (4–5 días)

*Cubre: tablas, relaciones, cardinalidades, direcciones de filtro.*

- [ ] Modo Import desde `dw.*`; servidor y base parametrizados en Power Query.
- [ ] Relaciones 1:N con filtro en una dirección; `dim_fecha` marcada como tabla de fechas; los hechos nunca se relacionan entre sí; `USERELATIONSHIP` para relaciones inactivas.
- [ ] Claves ocultas, tabla `_Medidas`, carpetas, formatos y descripciones.
- [ ] Guardar como PBIP y commitear.

📦 `docs/05_modelo_semantico.md`

## Fase 7: Medidas DAX (4–6 días)

*Cubre: medidas DAX y dependencias circulares.*

- [ ] Base: Ventas, Pedidos, Ticket promedio, Clientes únicos, Flete.
- [ ] Tiempo: año anterior, variación interanual %, acumulado del año, media móvil 3 meses.
- [ ] Ratios: % entregas a tiempo, días promedio de entrega, puntaje de reseña, % reseñas negativas, recompra.
- [ ] Avanzadas: Top N dinámico, selector de métrica con `SWITCH`, participación con `ALL` / `ALLSELECTED`.
- [ ] `VAR` en todas las medidas.
- [ ] Caso de dependencia circular reproducido, explicado y resuelto.
- [ ] Optimizar las 3 medidas más pesadas con DAX Studio.

📦 25–35 medidas, `docs/06_dax.md`

## Fase 8: Diseño de reportes (4–6 días)

*Cubre: usabilidad y consistencia.*

- [ ] Tema JSON propio.
- [ ] Páginas: Resumen ejecutivo, Comercial, Logística, Cliente y drill-through de vendedor.
- [ ] Tooltips, bookmarks, segmentadores sincronizados, botón de limpiar filtros.
- [ ] Contrastar con los criterios de aceptación de la Fase 1.
- [ ] Prueba de usabilidad con otra persona.

📦 Reporte completo y `docs/capturas/`

## Fase 9: Seguridad a nivel de fila (1–2 días)

- [ ] `dw.dim_gerente_region` (email, nombre, estados a cargo).
- [ ] RLS estático por región, RLS dinámico con `USERPRINCIPALNAME()` y rol "Dirección" sin restricciones.
- [ ] Probar con "Ver como".

📦 `docs/07_seguridad_rls.md`

## Fase 10: Rendimiento del modelo (2 días)

- [ ] Performance Analyzer, VertiPaq Analyzer, Best Practice Analyzer.
- [ ] Antes y después (tamaño y tiempos).

📦 `docs/08_rendimiento.md`

## Fase 11: Documentación, versionado y despliegue (2–3 días)

- [ ] Ramas por funcionalidad y pull requests.
- [ ] CI: tests de Python y, opcional, BPA sobre el TMDL.
- [ ] `CHANGELOG.md` y tags (`v1.0.0`).
- [ ] Despliegue simulado con `OlistDW_dev` y `OlistDW_prod` y el parámetro de Power Query; cómo sería con Deployment Pipelines.
- [ ] README final con diagrama de arquitectura, capturas y hallazgos.
- [ ] (Opcional) Video de 3 minutos.

📦 `docs/09_despliegue.md`

## Durante todo el proyecto: gestión

- [ ] Mover las tarjetas del GitHub Project.
- [ ] `docs/decisiones.md`: cada decisión, por qué y qué alternativas se descartaron.
- [ ] `docs/riesgos.md`: riesgos, bloqueos y cómo se destrabaron.
