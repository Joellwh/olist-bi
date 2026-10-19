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

## Fase 0: Preparación — ✅ hecha (2026-09-26), con pendientes manuales

- [x] Dataset de Kaggle descargado y extraído en `data/raw/` (9 CSV, conteo de filas verificado).
- [x] Repo local `olist-bi` con la estructura de carpetas.
- [x] Base `OlistDW` en `.\SQLEXPRESS` con esquemas `raw`, `stg`, `dw`, `rpt` y `etl` (script idempotente).
- [x] Entorno `.venv` (pandas, pyodbc, sqlalchemy, pytest), verificador de entorno (21/21 OK), 8 tests y workflow de CI.
- [x] README, `data/README.md`, `docs/decisiones.md` y primer commit.
- [x] Instalar Jupyter (`notebook` 7.6.1; hubo que reintentar por los cortes de red).
- [x] Power BI Desktop: activar guardado **PBIP** y formato **TMDL**.
- [x] Instalar **DAX Studio**.
- [ ] Instalar **Tabular Editor 2**. Necesario recién en la Fase 10 (Best Practice Analyzer).
- [ ] Crear el repo vacío `olist-bi` en GitHub y conectarlo.
- [ ] (Opcional) GitHub Project con una tarjeta por fase.

## Fase 1: Requerimientos y KPIs (2–3 días)

*Cubre: levantar requerimientos con stakeholders y convertirlos en KPIs.*

- [ ] 3 stakeholders ficticios: **Dirección Comercial**, **Logística**, **Experiencia de cliente**.
- [ ] 3 a 5 preguntas de negocio por stakeholder.
- [ ] Diccionario de KPIs: nombre, fórmula, tabla de origen, granularidad y reglas de negocio (¿cancelados cuentan como venta? ¿el flete es venta? ¿"a tiempo" contra fecha estimada o SLA fijo?).
- [ ] Bocetos a mano de cada página.
- [ ] Criterios de aceptación por página.

📦 `docs/01_requerimientos.md`, `docs/kpi_diccionario.md`, `docs/bocetos/`

## Fase 2: Exploración y perfilado (2–3 días)

- [ ] Notebook que perfile las 9 tablas: filas, nulos, duplicados, rangos, cardinalidad de claves.
- [ ] Problemas conocidos: `geolocation` repetido por código postal, reseñas duplicadas, varios ítems y pagos por pedido (granularidad), fechas faltantes en no entregados, categorías en portugués.
- [ ] Documentar cada problema y la decisión tomada.

📦 `docs/02_calidad_datos.md`

## Fase 3: ETL con Python hacia SQL Server (4–6 días)

*Cubre: Python para transformar, validar y automatizar; capas de extracción y preparación.*

- [ ] Extracción de CSV a `raw.*` (`pyodbc` + SQLAlchemy, `fast_executemany=True`).
- [ ] Limpieza en `stg.*`: tipos, deduplicación, normalización, traducción de categorías.
- [ ] Validación automática (pandera o checks propios): integridad referencial, fechas coherentes, precios y fletes ≥ 0. Si falla una regla crítica, la carga se corta.
- [ ] Log en `etl.log_ejecucion` (inicio, fin, filas por tabla, estado).
- [ ] Idempotente; un único comando: `python -m src.etl.run`.
- [ ] Tests con pytest.

📦 Pipeline reproducible con validaciones y logs.

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
