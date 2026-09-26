"""
Tests de la infraestructura base. No necesitan SQL Server, así que también
corren en el CI de GitHub, donde no hay una instancia disponible.
"""

import pytest

from src.config import SqlConfig
from src.db import split_batches, substitute_vars
from src.paths import RAW_FILES, SETUP_SQL_DIR


def test_split_batches_separa_por_go():
    script = "SELECT 1;\nGO\nSELECT 2;\n  go  \nSELECT 3;"
    assert split_batches(script) == ["SELECT 1;", "SELECT 2;", "SELECT 3;"]


def test_split_batches_no_corta_go_dentro_de_una_linea():
    # "GO" como parte de un identificador o texto no es un separador.
    script = "SELECT 'GO' AS texto, 1 AS GOLES;\nGO"
    assert split_batches(script) == ["SELECT 'GO' AS texto, 1 AS GOLES;"]


def test_split_batches_descarta_lotes_vacios():
    assert split_batches("GO\n\nGO\nSELECT 1;\nGO\n") == ["SELECT 1;"]


def test_substitute_vars_reemplaza():
    assert substitute_vars("USE [$(DB_NAME)];", {"DB_NAME": "OlistDW"}) == "USE [OlistDW];"


def test_substitute_vars_falla_si_falta_una_variable():
    with pytest.raises(KeyError, match="OTRA"):
        substitute_vars("$(DB_NAME) $(OTRA)", {"DB_NAME": "x"})


def test_odbc_string_usa_la_base_configurada_o_la_indicada():
    config = SqlConfig(server=r".\SQLEXPRESS", database="OlistDW", driver="ODBC Driver 18 for SQL Server")
    assert "DATABASE=OlistDW;" in config.odbc_string()
    assert "DATABASE=master;" in config.odbc_string("master")
    assert "DRIVER={ODBC Driver 18 for SQL Server};" in config.odbc_string()


def test_script_de_setup_crea_los_cinco_esquemas():
    script = (SETUP_SQL_DIR / "01_create_database.sql").read_text(encoding="utf-8")
    for esquema in ["raw", "stg", "dw", "rpt", "etl"]:
        assert f"CREATE SCHEMA {esquema}" in script
    # Todo el script tiene que resolverse solo con DB_NAME.
    lotes = split_batches(substitute_vars(script, {"DB_NAME": "OlistDW"}))
    assert len(lotes) == 4


def test_se_esperan_los_nueve_csv_de_olist():
    assert len(RAW_FILES) == 9
    assert all(filas > 0 for filas in RAW_FILES.values())
