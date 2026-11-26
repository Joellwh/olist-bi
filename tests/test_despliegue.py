"""Tests de las condiciones del despliegue simulado (src/despliegue.py)."""

from src.despliegue import ENTORNOS, EstadoGit, condiciones

COMMIT = "a" * 40
LISTO = EstadoGit(rama="main", commit=COMMIT, limpio=True, igual_a_origin=True)


def test_dev_se_despliega_desde_cualquier_rama_si_no_hay_cambios_pendientes():
    assert condiciones("dev", EstadoGit("fase-11-despliegue", COMMIT, True, False), set()) == []


def test_ningun_entorno_acepta_cambios_sin_commitear():
    sucio = EstadoGit("main", COMMIT, limpio=False, igual_a_origin=True)
    assert condiciones("dev", sucio, set())
    assert condiciones("prod", sucio, {COMMIT})


def test_prod_exige_que_el_commit_haya_pasado_por_dev():
    assert condiciones("prod", LISTO, {COMMIT}) == []
    assert any("dev" in p for p in condiciones("prod", LISTO, set()))


def test_prod_solo_desde_main_igual_a_github():
    otra_rama = EstadoGit("fase-11-despliegue", COMMIT, True, True)
    adelantada = EstadoGit("main", COMMIT, True, igual_a_origin=False)
    assert any("main" in p for p in condiciones("prod", otra_rama, {COMMIT}))
    assert any("origin/main" in p for p in condiciones("prod", adelantada, {COMMIT}))


def test_entornos_con_bases_distintas_de_la_local():
    assert ENTORNOS == {"dev": "OlistDW_dev", "prod": "OlistDW_prod"}
