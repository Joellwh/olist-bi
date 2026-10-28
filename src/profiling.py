"""
Funciones de perfilado y chequeo de calidad de datos.

Se usan en el notebook de la Fase 2 para explorar, y en la Fase 3 como base de
las validaciones del ETL: el mismo chequeo que encontró un problema es el que
después verifica que esté resuelto.

Todas reciben DataFrames y devuelven números o DataFrames; no imprimen ni leen
archivos, así se pueden testear con datos chicos armados a mano.
"""

import unicodedata

import pandas as pd


def perfil_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por columna: tipo, nulos, valores distintos, mínimo y máximo."""
    filas = []
    for col in df.columns:
        serie = df[col]
        no_nulos = serie.dropna()
        ordenable = pd.api.types.is_numeric_dtype(serie) or pd.api.types.is_datetime64_any_dtype(serie)
        filas.append({
            "columna": col,
            "tipo": str(serie.dtype),
            "nulos": int(serie.isna().sum()),
            "% nulos": round(serie.isna().mean() * 100, 2) if len(serie) else 0.0,
            "distintos": int(serie.nunique()),
            "mínimo": no_nulos.min() if ordenable and len(no_nulos) else None,
            "máximo": no_nulos.max() if ordenable and len(no_nulos) else None,
            "ejemplo": no_nulos.iloc[0] if len(no_nulos) else None,
        })
    return pd.DataFrame(filas).set_index("columna")


def resumen_tabla(df: pd.DataFrame, clave: list[str]) -> dict[str, int | bool]:
    """Tamaño, filas duplicadas y si la clave candidata identifica cada fila."""
    return {
        "filas": len(df),
        "columnas": df.shape[1],
        "filas duplicadas": int(df.duplicated().sum()),
        "claves repetidas": int(df.duplicated(subset=clave).sum()),
        "clave única": not df.duplicated(subset=clave).any(),
    }


def huerfanos(hijo: pd.DataFrame, col_hijo: str, padre: pd.DataFrame, col_padre: str) -> int:
    """Filas del hijo cuya clave no existe en el padre (integridad referencial).

    Los nulos no cuentan como huérfanos: una clave foránea vacía es otro
    problema, que se mide con los nulos de la columna.
    """
    claves = hijo[col_hijo].dropna()
    return int((~claves.isin(padre[col_padre])).sum())


def fechas_invertidas(df: pd.DataFrame, anterior: str, posterior: str) -> int:
    """Filas donde la fecha que debería ser posterior es anterior.

    Solo se comparan filas con las dos fechas cargadas.
    """
    a = pd.to_datetime(df[anterior])
    p = pd.to_datetime(df[posterior])
    return int((p < a).sum())


def fuera_de_rango(serie: pd.Series, minimo=None, maximo=None) -> int:
    """Valores no nulos por debajo del mínimo o por encima del máximo (inclusive)."""
    s = serie.dropna()
    fuera = pd.Series(False, index=s.index)
    if minimo is not None:
        fuera |= s < minimo
    if maximo is not None:
        fuera |= s > maximo
    return int(fuera.sum())


def normalizar_texto(texto: str | None) -> str | None:
    """Minúsculas, sin tildes y con un solo espacio entre palabras.

    "  São  Paulo " y "sao paulo" quedan iguales: así se detectan (y en la
    Fase 3 se unifican) las variantes de un mismo nombre.
    """
    if texto is None or (isinstance(texto, float) and pd.isna(texto)):
        return None
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def variantes_de_texto(serie: pd.Series) -> pd.DataFrame:
    """Valores normalizados que en el original aparecen escritos de más de una forma."""
    df = pd.DataFrame({"original": serie.dropna().unique()})
    df["normalizado"] = df["original"].map(normalizar_texto)
    grupos = df.groupby("normalizado")["original"].agg(["nunique", lambda s: sorted(s)])
    grupos.columns = ["variantes", "formas"]
    return grupos[grupos["variantes"] > 1].sort_values("variantes", ascending=False)
