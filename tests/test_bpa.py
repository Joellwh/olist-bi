"""Tests del control del Best Practice Analyzer (src/bpa.py)."""

import json

import pytest

from src.bpa import EXCEPCIONES, comparar, leer_excepciones, leer_trx

TRX = """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010">
  <Results>
    <UnitTestResult testName="[Formatting] Hide fact table columns" outcome="Failed">
      <Output><ErrorInfo>
        <Message>2 object(s) in violation of rule</Message>
        <StackTrace>Objects in violation:
  'fact_pedidos'[Puntaje de reseña] (Column)
  'Gerentes'[Estado (sigla)] (Column)</StackTrace>
      </ErrorInfo></Output>
    </UnitTestResult>
    <UnitTestResult testName="[Formatting] First letter of objects must be capitalized" outcome="Failed">
      <Output><ErrorInfo>
        <StackTrace>Objects in violation:
  'dim_fecha' (Table (Import))
  Dirección (Role)</StackTrace>
      </ErrorInfo></Output>
    </UnitTestResult>
    <UnitTestResult testName="[Performance] Do not use floating point data types" outcome="Passed" />
  </Results>
</TestRun>
"""


@pytest.fixture
def trx(tmp_path):
    ruta = tmp_path / "bpa.trx"
    ruta.write_text(TRX, encoding="utf-8")
    return ruta


def test_lee_solo_las_reglas_que_fallan_con_sus_objetos(trx):
    assert leer_trx(trx) == {
        ("[Formatting] Hide fact table columns", "'fact_pedidos'[Puntaje de reseña]"),
        ("[Formatting] Hide fact table columns", "'Gerentes'[Estado (sigla)]"),
        ("[Formatting] First letter of objects must be capitalized", "'dim_fecha'"),
        ("[Formatting] First letter of objects must be capitalized", "Dirección"),
    }


def test_un_aviso_sin_excepcion_es_nuevo():
    nuevos, sobrantes = comparar({("R", "a"), ("R", "b")}, {("R", "a")})
    assert nuevos == {("R", "b")} and not sobrantes


def test_una_excepcion_que_ya_no_aparece_sobra():
    nuevos, sobrantes = comparar({("R", "a")}, {("R", "a"), ("R", "viejo")})
    assert not nuevos and sobrantes == {("R", "viejo")}


def test_una_excepcion_sin_motivo_no_se_acepta(tmp_path):
    ruta = tmp_path / "excepciones.json"
    ruta.write_text(json.dumps([{"regla": "R", "motivo": "", "objetos": ["a"]}]), encoding="utf-8")
    with pytest.raises(ValueError):
        leer_excepciones(ruta)


def test_las_excepciones_del_modelo_tienen_motivo():
    assert leer_excepciones(EXCEPCIONES)
