"""
Tests del modelo semántico de Power BI. Leen los archivos TMDL, que son texto,
así que corren en el CI sin Power BI ni datos.

Protegen las decisiones de docs/05_modelo_semantico.md: Power BI reescribe estos
archivos al guardar, y un clic de más (como un filtro bidireccional o una
relación entre hechos) tiene que aparecer como un test fallido.
"""

import re

import pytest

from src.paths import DOCS_DIR, POWERBI_DIR

DEFINICION = POWERBI_DIR / "olist.SemanticModel" / "definition"
TABLAS = DEFINICION / "tables"
DIMENSIONES = {"dim_fecha", "dim_geografia", "dim_cliente", "dim_vendedor", "dim_producto"}
HECHOS = {"fact_items", "fact_pedidos"}
PARAMETROS = {"Top N", "Meses desde cohorte", "Selector de métrica"}   # tablas sin relaciones


def _relaciones() -> list[str]:
    texto = (DEFINICION / "relationships.tmdl").read_text(encoding="utf-8")
    return [b for b in re.split(r"(?m)^relationship ", texto)[1:]]


def _extremo(relacion: str, lado: str) -> tuple[str, str]:
    return re.search(rf"{lado}Column: '?([\w ]+?)'?\.'?([\w ]+?)'?\s*$", relacion, re.M).groups()


def _columnas(tabla: str) -> dict[str, str]:
    """Nombre de cada columna -> su bloque de propiedades."""
    texto = (TABLAS / f"{tabla}.tmdl").read_text(encoding="utf-8")
    bloques = re.split(r"(?m)^\t(?=column |hierarchy |partition |annotation |measure |/// )", texto)
    return {re.match(r"column '?([^'\n=]+?)'?\s*(=.*)?$", b, re.M).group(1): b
            for b in bloques if b.startswith("column ")}


def test_solo_estan_las_tablas_del_modelo():
    assert {p.stem for p in TABLAS.glob("*.tmdl")} == DIMENSIONES | HECHOS | PARAMETROS | {"_Medidas"}


def test_tablas_de_fechas_automaticas_desactivadas():
    assert "__PBI_TimeIntelligenceEnabled = 0" in (DEFINICION / "model.tmdl").read_text(encoding="utf-8")


def test_todas_las_relaciones_van_de_un_hecho_a_una_dimension():
    relaciones = _relaciones()
    assert len(relaciones) == 10
    for r in relaciones:
        assert _extremo(r, "from")[0] in HECHOS, r     # lado "muchos"
        assert _extremo(r, "to")[0] in DIMENSIONES, r  # lado "uno": nunca hecho con hecho


def test_ninguna_relacion_tiene_filtro_bidireccional():
    assert not [r for r in _relaciones() if "crossFilteringBehavior" in r]


def test_inactivas_solo_las_fechas_de_entrega_y_estimada():
    inactivas = {_extremo(r, "from")[1] for r in _relaciones() if "isActive: false" in r}
    assert inactivas == {"fecha_entrega_key", "fecha_estimada_key"}


def test_dim_fecha_marcada_como_tabla_de_fechas():
    assert "dataCategory: Time" in (TABLAS / "dim_fecha.tmdl").read_text(encoding="utf-8")
    assert "isKey" in _columnas("dim_fecha")["Fecha"]


@pytest.mark.parametrize("tabla", sorted(DIMENSIONES | HECHOS))
def test_conexion_por_parametros(tabla):
    """Sin servidor ni base escritos a mano: la Fase 11 cambia de entorno con los parámetros."""
    texto = (TABLAS / f"{tabla}.tmdl").read_text(encoding="utf-8")
    assert "Sql.Database(Servidor, BaseDatos)" in texto
    assert "SQLEXPRESS" not in texto


@pytest.mark.parametrize("tabla", sorted(DIMENSIONES | HECHOS))
def test_claves_tecnicas_ocultas(tabla):
    for nombre, bloque in _columnas(tabla).items():
        if nombre.endswith("_key") or nombre.endswith("_id"):
            assert "isHidden" in bloque, f"{tabla}.{nombre} tendría que estar oculta"


@pytest.mark.parametrize("tabla, columna", [("fact_items", "precio"), ("fact_items", "flete"),
                                            ("fact_pedidos", "valor_pagado")])
def test_montos_en_decimal_fijo(tabla, columna):
    assert "dataType: decimal" in _columnas(tabla)[columna]


# --- Medidas (Fase 7) ---

def _medidas() -> dict[str, str]:
    """Nombre de cada medida -> su expresión y propiedades."""
    texto = (TABLAS / "_Medidas.tmdl").read_text(encoding="utf-8")
    bloques = re.split(r"(?m)^	measure ", texto)[1:]
    return {re.match(r"'?(.+?)'?\s*=", b).group(1): b.split("/// ")[0] for b in bloques}


def test_cada_kpi_del_diccionario_tiene_su_medida():
    diccionario = (DOCS_DIR / "kpi_diccionario.md").read_text(encoding="utf-8")
    codigos = set(re.findall(r"^\| \*\*(K\d{2})\*\*", diccionario, re.M))
    medidas = (TABLAS / "_Medidas.tmdl").read_text(encoding="utf-8")
    assert len(codigos) == 28
    assert not [k for k in codigos if f"/// {k}" not in medidas]


def test_a_tiempo_siempre_filtra_entregados():
    """En DAX, vacío = FALSE da verdadero: sin es_entregado se cuentan los pedidos sin entregar."""
    malas = [n for n, m in _medidas().items() if "fact_pedidos[a_tiempo]" in m and "fact_pedidos[es_entregado]" not in m]
    assert not malas


def test_puntaje_negativo_excluye_vacios():
    """En DAX, vacío <= 2 da verdadero: sin el límite inferior, los pedidos sin reseña serían negativos."""
    malas = [n for n, m in _medidas().items() if re.search(r"puntaje_resena\] *<=", m) and not re.search(r"puntaje_resena\] *>= *1", m)]
    assert not malas
