"""
Pipeline completo: CSV -> raw -> validaciones -> stg -> validaciones.

    python -m src.etl.run

Carga completa en cada ejecución (D-012): las tablas se vacían y se vuelven a
llenar, así que correrlo dos veces deja exactamente el mismo resultado. Cada
paso y cada validación quedan registrados en etl.log_*.

Si una validación CRITICA falla, la ejecución se corta, queda como FALLA en
etl.log_ejecucion y el comando termina con código 1 (para que un programador
de tareas o el CI se entere).
"""

import sys
from datetime import datetime
from pathlib import Path

import pyodbc

from src.config import load_config
from src.db import connect, run_script
from src.etl import registro
from src.etl.extraccion import FUENTES, cargar_tabla
from src.etl.validaciones import VALIDACIONES_RAW, VALIDACIONES_STG, Validacion, resultado
from src.paths import RAW_SQL_DIR, STG_SQL_DIR


class ValidacionCriticaFallida(Exception):
    pass


def tabla_de_script(script: Path) -> str | None:
    """'11_customers.sql' -> 'stg.customers'. Los scripts 0x son de estructura y no cargan una tabla."""
    prefijo, _, nombre = script.stem.partition("_")
    return None if prefijo.startswith("0") else f"stg.{nombre}"


def validar(conn: pyodbc.Connection, ejecucion_id: int, validaciones: list[Validacion]) -> None:
    fallidas = []
    for v in validaciones:
        filas = int(conn.execute(v.sql).fetchone()[0])
        res = resultado(v.gravedad, filas)
        registro.validacion(conn, ejecucion_id, v, filas, res)
        marca = {"OK": "  ok ", "AVISO": "aviso", "FALLA": "FALLA"}[res]
        print(f"    [{marca}] {v.codigo} {v.descripcion}" + (f": {filas:,}".replace(",", ".") if filas else ""))
        if res == "FALLA":
            fallidas.append(f"{v.codigo} {v.descripcion} ({filas})")
    if fallidas:
        raise ValidacionCriticaFallida("Validaciones críticas fallidas: " + "; ".join(fallidas))


def main() -> int:
    config = load_config()
    print(f"ETL Olist  |  {config.server}  |  base {config.database}")
    conn = connect(config=config)
    ejecucion_id = registro.iniciar(conn)
    print(f"Ejecución #{ejecucion_id}")

    try:
        print("1. raw: estructura y carga de CSV")
        for script in sorted(RAW_SQL_DIR.glob("*.sql")):
            run_script(script, config=config)
        for tabla, archivo in FUENTES.items():
            inicio = datetime.now()
            filas = cargar_tabla(conn, tabla, archivo)
            registro.paso(conn, ejecucion_id, "raw", tabla, filas, inicio, datetime.now())
            print(f"    {tabla:<28} {filas:>10,} filas  ({(datetime.now() - inicio).total_seconds():.1f} s)".replace(",", "."))

        print("2. Validaciones sobre raw")
        validar(conn, ejecucion_id, VALIDACIONES_RAW)

        print("3. stg: tipos y limpieza")
        for script in sorted(STG_SQL_DIR.glob("*.sql")):
            inicio = datetime.now()
            run_script(script, config=config)
            tabla = tabla_de_script(script)
            filas = conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0] if tabla else None
            registro.paso(conn, ejecucion_id, "stg", tabla or script.name, filas, inicio, datetime.now())
            if tabla:
                print(f"    {tabla:<28} {filas:>10,} filas  ({(datetime.now() - inicio).total_seconds():.1f} s)".replace(",", "."))

        print("4. Validaciones sobre stg")
        validar(conn, ejecucion_id, VALIDACIONES_STG)

    except Exception as error:  # se registra cualquier falla, no solo las de validación
        registro.finalizar(conn, ejecucion_id, "FALLA", f"{type(error).__name__}: {error}")
        print(f"\nFALLA en la ejecución #{ejecucion_id}: {error}")
        return 1

    registro.finalizar(conn, ejecucion_id, "OK")
    print(f"\nEjecución #{ejecucion_id} terminada: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
