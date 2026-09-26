"""
Verifica que el entorno esté listo para trabajar: paquetes de Python, driver
ODBC, conexión a SQL Server, base y esquemas creados, y CSV en data/raw/.

    python -m src.setup.check_environment

Es el criterio de "Fase 0 terminada": si todo sale OK, se puede arrancar.
"""

from importlib.metadata import PackageNotFoundError, version

import pyodbc

from src.config import load_config
from src.db import connect
from src.paths import RAW_DIR, RAW_FILES

ESQUEMAS = ["raw", "stg", "dw", "rpt", "etl"]
PAQUETES = ["pandas", "sqlalchemy", "pyodbc", "pytest"]


def check(nombre: str, ok: bool, detalle: str = "") -> bool:
    print(f"  [{'OK' if ok else 'FALLA':>5}] {nombre}{'  ->  ' + detalle if detalle else ''}")
    return ok


def main() -> None:
    config = load_config()
    resultados = []

    print("Python")
    for paquete in PAQUETES:
        try:
            resultados.append(check(paquete, True, version(paquete)))
        except PackageNotFoundError:
            resultados.append(check(paquete, False, "pip install -r requirements.txt"))

    print("SQL Server")
    driver_ok = config.driver in pyodbc.drivers()
    resultados.append(check(f"driver '{config.driver}'", driver_ok))

    try:
        with connect("master", config) as conn:
            servidor = conn.execute("SELECT SERVERPROPERTY('ProductVersion'), "
                                    "SERVERPROPERTY('Edition')").fetchone()
        resultados.append(check(f"conexión a {config.server}", True, f"{servidor[1]} {servidor[0]}"))

        with connect("master", config) as conn:
            existe = conn.execute("SELECT DB_ID(?)", config.database).fetchone()[0] is not None
        resultados.append(check(f"base {config.database}", existe,
                                "" if existe else "python -m src.setup.create_database"))
        if existe:
            with connect(config=config) as conn:
                presentes = {r[0] for r in conn.execute("SELECT name FROM sys.schemas")}
            for esquema in ESQUEMAS:
                resultados.append(check(f"esquema {esquema}", esquema in presentes))
    except pyodbc.Error as e:
        resultados.append(check(f"conexión a {config.server}", False, str(e).splitlines()[0]))

    print("Datos")
    for nombre in RAW_FILES:
        resultados.append(check(nombre, (RAW_DIR / nombre).exists()))

    total, bien = len(resultados), sum(resultados)
    print(f"\n{bien}/{total} verificaciones OK.")
    if bien < total:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
