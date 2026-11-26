"""
Despliegue simulado a los entornos de desarrollo y producción (Fase 11).

    python -m src.despliegue dev
    python -m src.despliegue prod

Tres bases en el mismo SQL Server, una por entorno (docs/10_despliegue.md):

    OlistDW        local: donde se desarrolla; la usan el ETL y los tests por defecto
    OlistDW_dev    desarrollo compartido: lo que se mergeó, antes de producción
    OlistDW_prod   producción: lo que ve el negocio

El despliegue reconstruye la base del entorno con la versión del repo y la
verifica antes de darla por buena:

  1. Condiciones. Sin cambios sin commitear: la base queda asociada a un commit.
     Para prod, además: la rama main igual a la de GitHub (lo que pasó por un
     pull request y el CI) y el mismo commit ya desplegado con éxito en dev.
  2. Tests unitarios.
  3. Base y esquemas, si no existen.
  4. ETL completo; si falla una validación crítica, se corta.
  5. Tests de integración contra el entorno: los KPIs de SQL tienen que dar
     los valores de referencia del diccionario.
  6. Registro en etl.log_despliegue del entorno: qué commit, cuándo y con qué
     resultado. Así se sabe qué versión hay en cada entorno.
"""

import os
import subprocess
import sys
from dataclasses import dataclass

from src.config import load_config
from src.db import connect

ENTORNOS = {"dev": "OlistDW_dev", "prod": "OlistDW_prod"}


@dataclass(frozen=True)
class EstadoGit:
    rama: str
    commit: str
    limpio: bool
    igual_a_origin: bool


def condiciones(entorno: str, git: EstadoGit, commits_ok_en_dev: set[str]) -> list[str]:
    """Motivos por los que no se puede desplegar; vacía si se puede."""
    problemas = []
    if not git.limpio:
        problemas.append("hay cambios sin commitear: la base no quedaría asociada a un commit")
    if entorno == "prod":
        if git.rama != "main":
            problemas.append(f"producción se despliega desde main, no desde {git.rama}")
        elif not git.igual_a_origin:
            problemas.append("main no es igual a origin/main: a producción va lo que pasó por un pull request")
        if git.commit not in commits_ok_en_dev:
            problemas.append(f"el commit {git.commit[:7]} no se desplegó con éxito en dev")
    return problemas


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def estado_git() -> EstadoGit:
    _git("fetch", "--quiet", "origin")
    rama = _git("rev-parse", "--abbrev-ref", "HEAD")
    commit = _git("rev-parse", "HEAD")
    origin = subprocess.run(["git", "rev-parse", f"origin/{rama}"], capture_output=True, text=True).stdout.strip()
    return EstadoGit(rama, commit, limpio=_git("status", "--porcelain") == "", igual_a_origin=commit == origin)


def commits_ok(base: str) -> set[str]:
    """Commits desplegados con éxito en una base; vacío si la base o el registro no existen."""
    try:
        conn = connect(database=base)
        filas = conn.execute("SELECT version_git FROM etl.log_despliegue WHERE resultado = 'OK'").fetchall()
        conn.close()
    except Exception:  # la base todavía no existe: nada desplegado
        return set()
    return {f[0] for f in filas}


def registrar(base: str, entorno: str, commit: str, resultado: str, detalle: str | None = None) -> None:
    conn = connect(database=base)
    conn.execute("INSERT INTO etl.log_despliegue (entorno, version_git, resultado, detalle) VALUES (?, ?, ?, ?)",
                 entorno, commit, resultado, detalle)
    conn.close()


def _pytest(*args: str) -> bool:
    return subprocess.run([sys.executable, "-m", "pytest", "-q", *args]).returncode == 0


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in ENTORNOS:
        print("Uso: python -m src.despliegue dev|prod")
        return 2
    entorno, base = argv[0], ENTORNOS[argv[0]]
    # Todo lo que corre desde acá (setup, ETL, tests) apunta a la base del entorno
    os.environ["OLIST_SQL_DATABASE"] = base
    git = estado_git()
    print(f"Despliegue a {entorno} ({load_config().server} / {base})  |  {git.rama} @ {git.commit[:7]}")

    print("1. Condiciones")
    problemas = condiciones(entorno, git, commits_ok(ENTORNOS["dev"]) if entorno == "prod" else set())
    for p in problemas:
        print(f"    NO: {p}")
    if problemas:
        return 1
    print("    ok")

    print("2. Tests unitarios")
    if not _pytest("--ignore=tests/test_integracion_sql.py"):
        return 1

    # Se importan acá porque leen la configuración al ejecutarse, ya con la base del entorno
    from src.etl import run as etl
    from src.setup import create_database

    print("3. Base y esquemas")
    create_database.main()

    print("4. ETL")
    if etl.main() != 0:
        registrar(base, entorno, git.commit, "FALLA", "ETL")
        return 1

    print("5. Tests de integración contra el entorno")
    if not _pytest("tests/test_integracion_sql.py"):
        registrar(base, entorno, git.commit, "FALLA", "tests de integración")
        return 1

    registrar(base, entorno, git.commit, "OK")
    print(f"\nDesplegado: {base} tiene la versión {git.commit[:7]}.")
    print(f"En Power BI: parámetro BaseDatos = {base} (docs/10_despliegue.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
