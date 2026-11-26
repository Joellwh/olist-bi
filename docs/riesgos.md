# Riesgos y bloqueos

Lo que pudo salir mal o frenó el proyecto, y cómo se resolvió. Las decisiones de diseño están en el [registro de decisiones](decisiones.md); acá van los problemas.

## Datos

| Riesgo o bloqueo | Impacto | Cómo se resolvió |
|---|---|---|
| Unir ítems con pagos multiplica filas: un pedido puede tener varios pagos | Ventas infladas un 4,5%, sin ningún error visible | Detectado en el perfilado (Q12). Los pagos se agregan por pedido antes de unirse, y los dos hechos tienen distinta granularidad y no se unen (D-014). Una validación del ETL concilia las ventas de `raw` con las de `dw`. |
| El código postal pierde el cero inicial al leerse como número (Q20) | El 24% de los clientes deja de coincidir con la geolocalización, sin ningún error | Se lee siempre como texto y se guarda como `CHAR(5)`; la validación V07 controla que todos tengan 5 dígitos. |
| 2016 casi no tiene datos | Variaciones interanuales absurdas (+13.558% en 2017) | Período de análisis de enero de 2017 a agosto de 2018, y la variación interanual solo se muestra si el año anterior es comparable (D-021). |
| Los CSV pesan 126 MB y tienen licencia propia | No se pueden versionar en GitHub | `data/raw/` en `.gitignore` y un script que los extrae del zip de Kaggle ([data/README.md](../data/README.md)). Por eso el CI no corre los tests de integración. |
| Casi un tercio de la "recompra" es el mismo carrito partido en dos pedidos | Un KPI que parece decir algo que no dice | Un KPI nuevo, K28, que cuenta días distintos de compra. K25 no se redefinió porque ya estaba publicado ([04_optimizacion_sql.md](04_optimizacion_sql.md)). |

## Power BI

| Riesgo o bloqueo | Impacto | Cómo se resolvió |
|---|---|---|
| En DAX, un vacío comparado con `FALSE()` da verdadero | Pedidos no entregados contados como tardíos | Toda medida sobre `a_tiempo` filtra también `es_entregado`; tests que lo controlan ([06_dax.md](06_dax.md)). |
| Dependencia circular entre columnas calculadas, por la transición de contexto de `CALCULATE` | Un error que no se entiende leyendo las fórmulas | Reproducida a propósito y resuelta con `ALLEXCEPT` ([06_dax.md](06_dax.md)). El modelo la evita por diseño: no tiene columnas calculadas en las tablas de datos (D-016). |
| Power BI reescribe los archivos del reporte al guardar: cambia el orden del JSON, guarda el último vendedor de la página de detalle y puede mover un visual si se lo toca | Commits con cambios que nadie hizo a propósito | Revisar el diff antes de cada commit. Los tests del modelo semántico fallan si algo de diseño cambia (una relación bidireccional, un rol sin filtro, una columna de texto pesada). |
| Editar los archivos del proyecto con Power BI abierto | Power BI detecta el cambio externo y puede pisarlo al guardar | Regla: comprobar que Power BI esté cerrado antes de cada edición, y hacer un respaldo. |
| Sin licencia del servicio de Power BI | No se puede publicar ni asignar miembros a los roles | Despliegue simulado con tres bases y el parámetro de Power Query; la publicación, documentada paso a paso ([10_despliegue.md](10_despliegue.md) §5). |
| VertiPaq Analyzer, justo después de actualizar, muestra cada columna de texto con un diccionario de 1 MB | Un antes y después de rendimiento falso | Medir siempre con el modelo guardado y vuelto a abrir ([09_rendimiento.md](09_rendimiento.md) §1). |
| Performance Analyzer varía entre corridas porque incluye la espera entre visuales | Conclusiones sobre el motor basadas en ruido | Cada consulta DAX se vuelve a medir con la caché vacía (mediana de 3), que es estable. |
| La actualización del modelo tarda unos 4 minutos | Lentitud al iterar | Diagnosticado: SQL Server espera a Power BI Desktop (`ASYNC_NETWORK_IO`), las consultas se pliegan. Es el límite de Desktop, no del modelo ([10_despliegue.md](10_despliegue.md) §4). |

## Herramientas y entorno

| Riesgo o bloqueo | Impacto | Cómo se resolvió |
|---|---|---|
| El CI estuvo roto desde la Fase 0: `pytest` no encontraba el paquete `src` | Durante varias fases, el CI en rojo no avisaba nada útil | `pythonpath` en `pyproject.toml`. Desde entonces, los tests se corren igual que en el CI y el resultado del CI se revisa después de cada push. |
| Caída de GitHub Actions (2026-11-09): el CI falló dos veces con "Internal server error" | Un push sin verificar | Comprobado en un clon limpio que los tests pasaban, y el CI se volvió a correr cuando GitHub se normalizó. |
| La primera carga a SQL Server tardaba 7 minutos | ETL lento para iterar | `fast_executemany` y una transacción por tabla: 36 segundos ([etl.md](etl.md)). |
| Red inestable para descargas grandes de `pip` | La instalación de dependencias se cortaba | Reintentos de la instalación. |
| Commits directos a `main` hasta la Fase 10 | Un error llegaba a `main` antes de que el CI lo viera | Desde la Fase 11, ramas y pull requests: el CI corre antes del merge ([10_despliegue.md](10_despliegue.md) §1). |
