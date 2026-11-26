# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); las versiones siguen [Semantic Versioning](https://semver.org/lang/es/). Para un tablero, la versión mayor cambia cuando cambia algo que el usuario ya usaba (un KPI que se redefine, una página que se quita); la menor, cuando se agrega algo; la de parche, cuando se corrige.

## [1.1.0] - 2026-11-26

### Agregado

- **% de flete por categoría** (criterio L4 de la Fase 1): el gráfico de flete de Logística tiene un selector para ver el eje por región del cliente o por categoría, con un parámetro de campos (D-024). Por categoría muestra las que tienen 100 ítems vendidos o más; la información sobre herramientas suma ventas, flete e ítems.
- Control de KPIs para el flete por categoría: 48 controles.

### Cambiado

- El gráfico de flete de Logística pasó de columnas a barras horizontales, para que entren las 54 categorías con desplazamiento.

## [1.0.0] - 2026-11-26

Primera versión completa: las 12 fases del [roadmap](docs/roadmap.md).

### Agregado

- **Fase 0, preparación:** repositorio, entorno de Python con dependencias fijadas, SQL Server Express y CI en GitHub Actions.
- **Fase 1, requerimientos:** 3 áreas de negocio con 15 preguntas, diccionario de 28 KPIs con valores de referencia calculados en Python, bocetos de las 5 páginas y criterios de aceptación.
- **Fase 2, perfilado:** notebook sobre las 9 tablas y 23 problemas de calidad, cada uno con su decisión.
- **Fase 3, ETL:** CSV → `raw` → `stg` en Python y T-SQL, con 16 validaciones automáticas y logs en el esquema `etl`. Idempotente, en un solo comando.
- **Fase 4, modelo dimensional:** estrella en `dw` con 5 dimensiones y 2 hechos de distinta granularidad (ítem y pedido).
- **Fase 5, SQL analítico:** vistas `rpt` de cohortes, recompra, ranking de vendedores, RFM y variación mensual; índices elegidos midiendo 5 estrategias.
- **Fase 6, modelo semántico:** Power BI en formato PBIP/TMDL, importando desde `dw`, con servidor y base parametrizados.
- **Fase 7, DAX:** medidas para los 28 KPIs, variación interanual, cruce entre hechos con `TREATAS` y controles interactivos. `Control KPIs.dax` compara el modelo con los valores de referencia.
- **Fase 8, reportes:** tema propio y 5 páginas (Resumen, Comercial, Logística, Cliente y detalle de vendedor), con texto alternativo en todos los visuales y prueba de usabilidad.
- **Fase 9, seguridad por fila:** rol dinámico por gerente regional con `USERPRINCIPALNAME()`, rol de Dirección y roles estáticos por región.
- **Fase 10, rendimiento:** clave numérica de pedido, modelo sin columnas que nada usa y medidas con `USERELATIONSHIP` para las fechas de entrega y estimada. De 33,7 a 9,9 MB, sin visuales de más de 2 s.
- **Fase 11, versionado y despliegue:** pull requests con CI (tests y Best Practice Analyzer sobre el TMDL), despliegue a `OlistDW_dev` y `OlistDW_prod` con condiciones de paso, y esta documentación.

### Conocido

- El despliegue del modelo semántico al servicio de Power BI está documentado pero no ejecutado: requiere una licencia que el proyecto no tiene ([10_despliegue.md](docs/10_despliegue.md) §5).

[1.1.0]: https://github.com/Joellwh/olist-bi/releases/tag/v1.1.0
[1.0.0]: https://github.com/Joellwh/olist-bi/releases/tag/v1.0.0
