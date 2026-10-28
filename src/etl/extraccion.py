"""
Extracción: de los CSV a las tablas raw.*, sin transformar nada.

Cada CSV se lee entero como texto (Q20: si pandas infiere tipos, los códigos
postales pierden el cero inicial) y se inserta en lotes con fast_executemany,
que manda muchas filas por viaje al servidor en vez de una por una.
"""

from pathlib import Path

import pandas as pd
import pyodbc

from src.paths import RAW_DIR, SEEDS_DIR

# Tabla raw -> archivo de origen. El orden es el de carga.
FUENTES: dict[str, Path] = {
    "raw.orders": RAW_DIR / "olist_orders_dataset.csv",
    "raw.order_items": RAW_DIR / "olist_order_items_dataset.csv",
    "raw.order_payments": RAW_DIR / "olist_order_payments_dataset.csv",
    "raw.order_reviews": RAW_DIR / "olist_order_reviews_dataset.csv",
    "raw.customers": RAW_DIR / "olist_customers_dataset.csv",
    "raw.sellers": RAW_DIR / "olist_sellers_dataset.csv",
    "raw.products": RAW_DIR / "olist_products_dataset.csv",
    "raw.category_translation": RAW_DIR / "product_category_name_translation.csv",
    "raw.geolocation": RAW_DIR / "olist_geolocation_dataset.csv",
    "raw.categorias_es": SEEDS_DIR / "categorias.csv",
}

TAMANO_LOTE = 20_000


def leer_csv(archivo: Path) -> pd.DataFrame:
    """Lee un CSV todo como texto. Solo la celda vacía es nulo.

    pandas por defecto también convierte en nulo textos como "NA" o "null";
    en raw tiene que llegar exactamente lo que dice el archivo.
    """
    return pd.read_csv(archivo, dtype=str, keep_default_na=False, na_values=[""])


def filas_para_insertar(df: pd.DataFrame) -> list[tuple]:
    """Convierte el DataFrame en tuplas, con None donde hay nulos (NULL en SQL)."""
    return list(df.astype(object).where(df.notna(), None).itertuples(index=False, name=None))


def columnas_de_tabla(cursor: pyodbc.Cursor, tabla: str) -> list[tuple[str, int]]:
    """Nombre y largo de cada columna de la tabla, en orden."""
    esquema, nombre = tabla.split(".")
    return [(fila.column_name, fila.column_size) for fila in cursor.columns(table=nombre, schema=esquema)]


def verificar_columnas(tabla: str, en_csv: list[str], en_tabla: list[str]) -> None:
    """El CSV y la tabla tienen que tener las mismas columnas, en el mismo orden.

    Si el origen agrega, saca o reordena una columna, es mejor fallar acá con
    un mensaje claro que cargar valores en la columna equivocada.
    """
    if en_csv != en_tabla:
        raise ValueError(f"Las columnas del CSV no coinciden con {tabla}.\n"
                         f"  CSV:   {en_csv}\n  tabla: {en_tabla}")


def cargar_tabla(conn: pyodbc.Connection, tabla: str, archivo: Path) -> int:
    """Vacía la tabla raw, carga el CSV y devuelve la cantidad de filas.

    Todo en una sola transacción: la tabla queda completa o como estaba, nunca
    a medias. Además es mucho más rápido que confirmar cada lote (medido: de
    ~1.800 a ~25.000 filas por segundo). Declarar los tipos con setinputsizes
    evita que pyodbc los consulte y duplica la velocidad otra vez.
    """
    df = leer_csv(archivo)
    cursor = conn.cursor()
    columnas = columnas_de_tabla(cursor, tabla)
    verificar_columnas(tabla, list(df.columns), [nombre for nombre, _ in columnas])

    sql = f"INSERT INTO {tabla} ({', '.join(df.columns)}) VALUES ({', '.join('?' * len(df.columns))})"
    filas = filas_para_insertar(df)
    autocommit_previo = conn.autocommit
    conn.autocommit = False
    try:
        cursor.execute(f"TRUNCATE TABLE {tabla}")
        cursor.fast_executemany = True
        cursor.setinputsizes([(pyodbc.SQL_WVARCHAR, largo, 0) for _, largo in columnas])
        for inicio in range(0, len(filas), TAMANO_LOTE):
            cursor.executemany(sql, filas[inicio:inicio + TAMANO_LOTE])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = autocommit_previo
    return len(filas)
