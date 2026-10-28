"""
Tests del ETL que no necesitan SQL Server ni los CSV de Olist (corren en el CI).
"""

import re

import pandas as pd
import pytest

from src.etl.extraccion import filas_para_insertar, leer_csv, verificar_columnas
from src.etl.run import tabla_de_script
from src.etl.validaciones import (ADVERTENCIA, CRITICA, VALIDACIONES_RAW, VALIDACIONES_STG,
                                  resultado)
from src.paths import DOCS_DIR, SEEDS_DIR

TODAS = VALIDACIONES_RAW + VALIDACIONES_STG


# --- extracción -------------------------------------------------------------

def test_leer_csv_conserva_ceros_y_textos_parecidos_a_nulos(tmp_path):
    archivo = tmp_path / "x.csv"
    archivo.write_text("zip,ciudad\n09790,NA\n01001,\n", encoding="utf-8")
    df = leer_csv(archivo)
    assert list(df["zip"]) == ["09790", "01001"]          # Q20: sin perder el cero
    assert df.loc[0, "ciudad"] == "NA"                     # "NA" es texto, no nulo
    assert pd.isna(df.loc[1, "ciudad"])                    # solo la celda vacía es nulo


def test_filas_para_insertar_convierte_nulos_en_none():
    df = pd.DataFrame({"a": ["1", None], "b": [float("nan"), "x"]})
    assert filas_para_insertar(df) == [("1", None), (None, "x")]


def test_verificar_columnas_falla_si_el_origen_cambia():
    verificar_columnas("raw.t", ["a", "b"], ["a", "b"])
    with pytest.raises(ValueError, match="no coinciden"):
        verificar_columnas("raw.t", ["b", "a"], ["a", "b"])


def test_tabla_de_script():
    assert tabla_de_script(SEEDS_DIR / "11_customers.sql") == "stg.customers"
    assert tabla_de_script(SEEDS_DIR / "18_order_reviews.sql") == "stg.order_reviews"
    assert tabla_de_script(SEEDS_DIR / "01_tablas_stg.sql") is None


# --- validaciones -----------------------------------------------------------

def test_resultado_segun_gravedad():
    assert resultado(CRITICA, 0) == "OK"
    assert resultado(CRITICA, 3) == "FALLA"
    assert resultado(ADVERTENCIA, 0) == "OK"
    assert resultado(ADVERTENCIA, 3) == "AVISO"


def test_validaciones_bien_formadas():
    for v in TODAS:
        assert re.fullmatch(r"V\d{2}", v.codigo), v
        assert v.gravedad in (CRITICA, ADVERTENCIA), v
        assert v.sql.lstrip().upper().startswith("SELECT"), v
        assert len(v.descripcion) <= 300, v   # largo de la columna en etl.log_validacion


def test_validaciones_coinciden_con_el_informe_de_calidad():
    """Cada regla del informe está implementada, con la misma gravedad, y no hay reglas de más."""
    informe = (DOCS_DIR / "02_calidad_datos.md").read_text(encoding="utf-8")
    criticas_doc, advertencias_doc = informe.split("### 🟡 Advertencias")
    en_doc = {**{c: CRITICA for c in re.findall(r"^\| (V\d{2}) \|", criticas_doc, re.M)},
              **{c: ADVERTENCIA for c in re.findall(r"^\| (V\d{2}) \|", advertencias_doc, re.M)}}
    en_codigo = {v.codigo: v.gravedad for v in TODAS}
    assert en_codigo == en_doc


# --- tabla propia de categorías (D-011) --------------------------------------

def test_categorias_en_espanol():
    categorias = pd.read_csv(SEEDS_DIR / "categorias.csv", dtype=str)
    assert len(categorias) == 73
    assert categorias.category_name_pt.is_unique
    assert categorias.category_es.notna().all() and categorias.category_es.is_unique
    # Las 2 que faltan en la traducción de Olist (Q18)
    assert {"pc_gamer", "portateis_cozinha_e_preparadores_de_alimentos"} <= set(categorias.category_name_pt)
