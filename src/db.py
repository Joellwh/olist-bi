"""
Conexión a SQL Server y ejecución de scripts .sql.

Los scripts de sql/ se escriben para que también funcionen tal cual en SSMS
(modo SQLCMD) o con la herramienta sqlcmd:

  - Los lotes se separan con GO, que no es T-SQL sino una convención de las
    herramientas. Acá se parte el script en lotes y se ejecuta cada uno.
  - El nombre de la base se escribe como variable de sqlcmd, $(DB_NAME), y se
    reemplaza antes de ejecutar. Así el mismo script crea OlistDW, OlistDW_dev
    u OlistDW_prod.
"""

import re
from pathlib import Path

import pyodbc

from src.config import SqlConfig, load_config

_GO = re.compile(r"^\s*GO\s*;?\s*$", re.IGNORECASE | re.MULTILINE)
_VAR = re.compile(r"\$\((\w+)\)")


def split_batches(script: str) -> list[str]:
    """Parte un script en lotes separados por líneas GO, descartando vacíos."""
    return [lote.strip() for lote in _GO.split(script) if lote.strip()]


def substitute_vars(script: str, variables: dict[str, str]) -> str:
    """Reemplaza las variables $(NOMBRE). Falla si alguna queda sin valor."""
    def reemplazo(m: re.Match) -> str:
        nombre = m.group(1)
        if nombre not in variables:
            raise KeyError(f"El script usa $({nombre}) pero no se le pasó un valor.")
        return variables[nombre]
    return _VAR.sub(reemplazo, script)


def connect(database: str | None = None, config: SqlConfig | None = None) -> pyodbc.Connection:
    """
    Abre una conexión. Por defecto a la base configurada; pasá database="master"
    para operaciones de servidor, como crear la base.

    autocommit=True porque CREATE DATABASE no puede correr dentro de una
    transacción.
    """
    config = config or load_config()
    return pyodbc.connect(config.odbc_string(database), autocommit=True, timeout=10)


def run_script(path: Path, database: str | None = None, config: SqlConfig | None = None) -> int:
    """Ejecuta un archivo .sql lote por lote. Devuelve la cantidad de lotes."""
    config = config or load_config()
    script = substitute_vars(path.read_text(encoding="utf-8"), {"DB_NAME": config.database})
    lotes = split_batches(script)
    with connect(database, config) as conn:
        cursor = conn.cursor()
        for lote in lotes:
            cursor.execute(lote)
            # Consumir todos los resultados para que los errores de lotes con
            # varias sentencias no queden ocultos.
            while cursor.nextset():
                pass
    return len(lotes)
