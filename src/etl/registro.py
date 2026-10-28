"""
Registro de cada ejecución del ETL en las tablas etl.log_* (sql/00_setup/02_etl_log.sql).

Se escribe con una conexión propia en autocommit: si la carga falla a la
mitad, lo que ya se registró queda guardado, que es justo cuando más se necesita.
"""

from datetime import datetime

import pyodbc

from src.etl.validaciones import Validacion


def iniciar(conn: pyodbc.Connection) -> int:
    fila = conn.execute("INSERT INTO etl.log_ejecucion DEFAULT VALUES; SELECT SCOPE_IDENTITY();")
    fila.nextset()
    return int(fila.fetchone()[0])


def paso(conn: pyodbc.Connection, ejecucion_id: int, capa: str, objeto: str, filas: int | None,
         inicio: datetime, fin: datetime) -> None:
    conn.execute(
        "INSERT INTO etl.log_paso (ejecucion_id, capa, objeto, filas, inicio, fin) VALUES (?, ?, ?, ?, ?, ?)",
        ejecucion_id, capa, objeto, filas, inicio, fin)


def validacion(conn: pyodbc.Connection, ejecucion_id: int, v: Validacion, filas_afectadas: int,
               resultado: str) -> None:
    conn.execute(
        "INSERT INTO etl.log_validacion (ejecucion_id, codigo, gravedad, descripcion, filas_afectadas, resultado)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        ejecucion_id, v.codigo, v.gravedad, v.descripcion, filas_afectadas, resultado)


def finalizar(conn: pyodbc.Connection, ejecucion_id: int, estado: str, mensaje: str | None = None) -> None:
    conn.execute(
        "UPDATE etl.log_ejecucion SET fin = SYSDATETIME(), estado = ?, mensaje = ? WHERE ejecucion_id = ?",
        estado, mensaje[:2000] if mensaje else None, ejecucion_id)
