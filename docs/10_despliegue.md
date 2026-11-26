# Versionado y despliegue

**Fase:** 11

Cómo llega un cambio desde una rama hasta producción. El flujo de Git es real: ramas, pull requests y CI en GitHub. Los entornos se simulan con tres bases en el mismo SQL Server y el parámetro de Power Query. El servicio de Power BI no se usó (requiere una licencia que el proyecto no tiene); §5 describe cómo sería.

```
 rama ──► pull request ──► CI ──► merge a main ──► despliegue a dev ──► despliegue a prod
          (revisión)      tests                    OlistDW_dev         OlistDW_prod
                          Best Practice Analyzer   ETL + validaciones  solo lo que ya pasó por dev
                                                   KPIs = referencia   KPIs = referencia
```

## 1. Versionado

- **Una rama por funcionalidad y un pull request para sumarla a `main`.** El CI corre sobre el pull request, antes del merge: un error queda en la rama y `main` siempre funciona. Hasta la Fase 10 se commiteaba directo en `main`, y el CI avisaba recién cuando el error ya estaba ahí.
- **El CI tiene dos jobs** ([.github/workflows/ci.yml](../.github/workflows/ci.yml)):
  - `tests`: los tests de Python, en Linux. Los de integración se saltean solos porque necesitan SQL Server y los CSV.
  - `best-practice-analyzer`: Tabular Editor 2 revisa los archivos TMDL del modelo, en Windows, y [src/bpa.py](../src/bpa.py) compara el resultado con las excepciones justificadas ([09_rendimiento.md](09_rendimiento.md) §7).
- **Todo lo de Power BI se versiona como texto.** El formato PBIP guarda el modelo en TMDL y el reporte en JSON, así que un pull request muestra qué medida o qué visual cambió. La caché con los datos importados no se versiona (`.gitignore`): se regenera desde SQL Server.
- **Protección de `main` (recomendada, se configura en GitHub):** *Settings → Branches → Add rule* para `main`, con "Require a pull request before merging" y "Require status checks to pass" marcando los dos jobs. Así ni siquiera el dueño del repo puede saltearse el CI por error.

## 2. Entornos

| Entorno | Base | Para qué | Quién la carga |
|---|---|---|---|
| Local | `OlistDW` | Desarrollar y probar en la propia máquina | `python -m src.etl.run`, a mano |
| Desarrollo | `OlistDW_dev` | Lo que se mergeó, antes de producción | `python -m src.despliegue dev` |
| Producción | `OlistDW_prod` | Lo que ve el negocio | `python -m src.despliegue prod` |

Las tres tienen el mismo esquema y los mismos datos: lo que cambia entre entornos es la **versión del código** que las construyó. En un caso real, dev tendría una copia o una muestra, y prod los datos vivos, en servidores distintos.

## 3. Despliegue de la base

[src/despliegue.py](../src/despliegue.py) reconstruye la base del entorno con la versión del repo y la verifica antes de darla por buena:

| Paso | dev | prod |
|---|---|---|
| 1. Sin cambios sin commitear: la base queda asociada a un commit | ✔ | ✔ |
| 1. Desde `main`, igual a GitHub: lo que pasó por un pull request y el CI | | ✔ |
| 1. El mismo commit ya desplegado con éxito en dev | | ✔ |
| 2. Tests unitarios | ✔ | ✔ |
| 3. Base y esquemas, si no existen | ✔ | ✔ |
| 4. ETL completo; una validación crítica que falla lo corta | ✔ | ✔ |
| 5. Tests de integración contra el entorno: los KPIs de SQL dan los valores de referencia | ✔ | ✔ |
| 6. Registro en `etl.log_despliegue`: commit, momento y resultado | ✔ | ✔ |

La condición de producción es la misma idea que *Deployment Pipelines* en el servicio de Power BI: a producción no se despliega algo nuevo, se **promueve** lo que ya funcionó en el entorno anterior.

Para saber qué versión hay en cada entorno:

```sql
SELECT TOP 1 version_git, momento FROM OlistDW_prod.etl.log_despliegue
WHERE resultado = 'OK' ORDER BY momento DESC;
```

**Prueba de la condición:** desde una rama, con cambios sin commitear y sin nada en dev, el despliegue a prod se niega por los tres motivos y no toca la base.

**Despliegue a dev** (2026-11-26, primero desde la rama de este cambio y después desde `main`, con el commit del merge): ETL completo con las 16 validaciones (las críticas, en OK; los avisos, los conocidos de [02_calidad_datos.md](02_calidad_datos.md)), 30 tests de integración en OK contra `OlistDW_dev`, y el registro con el commit.

**Despliegue a prod** (2026-11-26, commit `559c08c` de `main`): las tres condiciones en OK, porque ese commit ya estaba desplegado con éxito en dev. ETL completo y 30 tests de integración en OK contra `OlistDW_prod`.

## 4. Power BI: cambiar de entorno con un parámetro

El modelo no tiene el servidor ni la base escritos en las consultas: los leen de dos parámetros de Power Query, `Servidor` y `BaseDatos` ([expressions.tmdl](../powerbi/olist.SemanticModel/definition/expressions.tmdl), D-018). El archivo versionado apunta a `OlistDW`, la base local.

**Cambiar de entorno en Power BI Desktop:** *Inicio → Transformar datos → Editar parámetros*, cambiar `BaseDatos` y aplicar los cambios.

**Probado con dev** (2026-11-26): con `BaseDatos = OlistDW_dev`, la actualización leyó las 8 tablas de `.\SQLEXPRESS/OlistDW_dev`, y los 47 controles de `Control KPIs.dax` dieron OK. Se cerró sin guardar, para que el repo siga apuntando a la base local.

La actualización tarda unos 4 minutos. SQL Server pasa ese tiempo esperando a que Power BI lea las filas (espera `ASYNC_NETWORK_IO`): el límite está en Power BI Desktop, no en la base ni en las consultas, que se pliegan a SQL (cada tabla es un `SELECT` de sus columnas).

## 5. Cómo sería en el servicio de Power BI

No se ejecutó: publicar y compartir requiere una licencia Pro o Premium por usuario. Es el diseño que seguiría.

1. **Tres áreas de trabajo**, `Olist BI [Dev]`, `[Test]` y `[Prod]`, unidas por una **canalización de implementación** (*Deployment Pipelines*).
2. **Publicar en Dev** desde Power BI Desktop. Alternativa: conectar el área de trabajo de Dev al repo de GitHub (integración con Git), que lee el mismo formato PBIP de este repo.
3. **Reglas de implementación** en cada etapa: el parámetro `BaseDatos` vale `OlistDW_dev` en Dev y Test, y `OlistDW_prod` en Prod. Es lo que acá se hace a mano en el paso 4: la canalización lo aplica sola al promover.
4. **Puerta de enlace de datos local** (*on-premises data gateway*): el servicio está en la nube y SQL Server en una máquina local, así que la actualización necesita una puerta de enlace instalada en la red de la base, con las credenciales de cada origen.
5. **Actualización programada** en Prod, después del ETL nocturno. Si el ETL falla una validación crítica, la base no cambia, y el informe sigue mostrando la última carga buena.
6. **Seguridad por fila** ([08_seguridad_rls.md](08_seguridad_rls.md)): en *Seguridad* del modelo semántico, los gerentes regionales (mejor como un grupo de Microsoft Entra que uno por uno) van al rol `Gerente regional`, y Dirección a `Dirección`. El rol dinámico no cambia cuando entra un gerente nuevo: alcanza con su fila en `dw.seguridad_gerentes`. Antes de abrirlo, se prueba con *Probar como rol* con un usuario de cada caso, como en la Fase 9.
7. **Una aplicación** para los consumidores, en lugar de darles acceso al área de trabajo: ven el informe, no pueden editarlo, y la seguridad por fila se aplica. Los permisos de edición quedan para quien desarrolla.
8. **Promover de Test a Prod** después de revisar en Test. La canalización compara las etapas y muestra qué cambió.

## 6. Límites de la simulación

- **Los tres entornos están en el mismo servidor.** En un caso real, prod estaría en otro servidor, con otras credenciales, y el despliegue correría desde un servidor de integración, no desde la máquina de quien desarrolla.
- **El despliegue de Power BI es manual.** El cambio de parámetro está probado, pero no hay nada que lo haga solo; en el servicio lo hacen las reglas de la canalización (§5).
- **El despliegue no corre en el CI.** El runner de GitHub no tiene SQL Server ni los CSV (no se versionan: [data/README.md](../data/README.md)).
