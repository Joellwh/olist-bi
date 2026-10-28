"""
Tests de las funciones de perfilado. Usan DataFrames chicos armados a mano,
así no dependen de los CSV (que no están en el repo ni en el CI).
"""

import pandas as pd

from src.profiling import (
    fechas_invertidas,
    huerfanos,
    normalizar_texto,
    perfil_columnas,
    resumen_tabla,
    variantes_de_texto,
)


def test_perfil_columnas_cuenta_nulos_y_distintos():
    df = pd.DataFrame({"a": [1, 2, 2, None], "b": ["x", "x", "y", "z"]})
    perfil = perfil_columnas(df)
    assert perfil.loc["a", "nulos"] == 1
    assert perfil.loc["a", "% nulos"] == 25.0
    assert perfil.loc["a", "distintos"] == 2
    assert perfil.loc["a", "mínimo"] == 1 and perfil.loc["a", "máximo"] == 2
    assert pd.isna(perfil.loc["b", "mínimo"])  # texto: no se calcula rango


def test_resumen_tabla_detecta_clave_repetida():
    df = pd.DataFrame({"pedido": [1, 1, 2], "item": [1, 2, 1]})
    assert resumen_tabla(df, ["pedido"])["clave única"] is False
    assert resumen_tabla(df, ["pedido", "item"])["clave única"] is True


def test_resumen_tabla_cuenta_filas_duplicadas():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    assert resumen_tabla(df, ["a"])["filas duplicadas"] == 1


def test_huerfanos_ignora_nulos():
    padre = pd.DataFrame({"id": [1, 2]})
    hijo = pd.DataFrame({"fk": [1, 3, None]})
    assert huerfanos(hijo, "fk", padre, "id") == 1


def test_fechas_invertidas_solo_compara_filas_completas():
    df = pd.DataFrame({
        "compra": ["2018-01-10", "2018-01-10", "2018-01-10"],
        "entrega": ["2018-01-05", "2018-01-15", None],
    })
    assert fechas_invertidas(df, "compra", "entrega") == 1



def test_normalizar_texto():
    assert normalizar_texto("  São  Paulo ") == "sao paulo"
    assert normalizar_texto("SAO PAULO") == "sao paulo"
    assert normalizar_texto(None) is None
    assert normalizar_texto(float("nan")) is None


def test_normalizar_texto_limpia_texto_corrupto_y_puntuacion():
    assert normalizar_texto("sa£o paulo") == "sao paulo"      # carácter no ASCII: se borra
    assert normalizar_texto("´teresopolis") == "teresopolis"
    assert normalizar_texto("sbc/sp") == "sbc sp"             # puntuación: pasa a espacio
    assert normalizar_texto("sao paulo - sp") == "sao paulo - sp"  # el guion se conserva
    assert normalizar_texto("d'oeste") == "d'oeste"
    assert normalizar_texto("santa barbara d´oeste") == "santa barbara d'oeste"  # ´ como apóstrofo
    assert normalizar_texto("4º centenario") == "4 centenario"   # º: se borra, igual que en SQL
    assert normalizar_texto(" / ") is None


def test_variantes_de_texto_agrupa_formas_de_un_mismo_nombre():
    serie = pd.Series(["são paulo", "sao paulo", "Sao Paulo", "campinas"])
    variantes = variantes_de_texto(serie)
    assert list(variantes.index) == ["sao paulo"]
    assert variantes.loc["sao paulo", "variantes"] == 3
