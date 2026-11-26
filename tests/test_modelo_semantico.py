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
PARAMETROS = {"Top N", "Meses desde cohorte", "Selector de métrica", "Eje del flete"}   # tablas sin relaciones
SEGURIDAD = {"Gerentes"}   # sin relaciones: la lee el rol dinámico (Fase 9)
ROLES = DEFINICION / "roles"


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
    assert {p.stem for p in TABLAS.glob("*.tmdl")} == DIMENSIONES | HECHOS | PARAMETROS | SEGURIDAD | {"_Medidas"}


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


def test_parametro_de_campos_del_flete():
    # L4: el gráfico de flete de Logística cambia de eje entre región y categoría (D-024)
    texto = (TABLAS / "Eje del flete.tmdl").read_text(encoding="utf-8")
    assert "extendedProperty ParameterMetadata" in texto
    assert "NAMEOF ( 'dim_geografia'[Región] )" in texto and "NAMEOF ( 'dim_producto'[Categoría] )" in texto


@pytest.mark.parametrize("columna", ["fecha_entrega_key", "fecha_estimada_key"])
def test_cada_relacion_inactiva_la_activa_una_medida(columna):
    # Una relación inactiva que nada activa es peso muerto (Best Practice Analyzer, Fase 10)
    texto = (TABLAS / "_Medidas.tmdl").read_text(encoding="utf-8")
    assert f"USERELATIONSHIP ( fact_pedidos[{columna}], dim_fecha[fecha_key] )" in texto


def test_dim_fecha_marcada_como_tabla_de_fechas():
    assert "dataCategory: Time" in (TABLAS / "dim_fecha.tmdl").read_text(encoding="utf-8")
    assert "isKey" in _columnas("dim_fecha")["Fecha"]


@pytest.mark.parametrize("tabla", sorted(DIMENSIONES | HECHOS | SEGURIDAD))
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
                                            ("fact_pedidos", "dias_entrega")])
def test_decimales_en_decimal_fijo(tabla, columna):
    # Decimal fijo y no coma flotante: exacto al sumar y más liviano (Fase 10)
    assert "dataType: decimal" in _columnas(tabla)[columna]


# --- Rendimiento (Fase 10, docs/09_rendimiento.md) ---

IDENTIFICADORES_DE_TEXTO = {"pedido_id", "customer_unique_id", "product_id", "seller_id"}


@pytest.mark.parametrize("tabla", sorted(DIMENSIONES | HECHOS))
def test_sin_identificadores_de_texto(tabla):
    # Textos de 32 caracteres, uno distinto por fila: eran el 47% del modelo
    cargadas = set(re.findall(r"sourceColumn: (\w+)", (TABLAS / f"{tabla}.tmdl").read_text(encoding="utf-8")))
    assert not cargadas & IDENTIFICADORES_DE_TEXTO


def test_cruce_entre_hechos_por_clave_numerica():
    for tabla in HECHOS:
        assert "dataType: int64" in _columnas(tabla)["pedido_key"]
    texto = (TABLAS / "_Medidas.tmdl").read_text(encoding="utf-8")
    cruces = re.findall(r"TREATAS \( VALUES \( (\S+) \), (\S+) \)", texto)
    assert cruces and set(cruces) == {("fact_items[pedido_key]", "fact_pedidos[pedido_key]")}


@pytest.mark.parametrize("tabla", sorted(HECHOS))
def test_columnas_ocultas_de_los_hechos_sin_jerarquia_de_atributos(tabla):
    # Las jerarquías de atributos solo sirven a Excel (MDX) y eran el 24% del modelo
    for nombre, bloque in _columnas(tabla).items():
        if "isHidden" in bloque:
            assert "isAvailableInMdx: false" in bloque, f"{tabla}.{nombre}"


@pytest.mark.parametrize("tabla, clave", [("dim_geografia", "geografia_key"), ("dim_cliente", "cliente_key"),
                                          ("dim_vendedor", "vendedor_key"), ("dim_producto", "producto_key")])
def test_claves_de_dimension_marcadas(tabla, clave):
    assert "isKey" in _columnas(tabla)[clave]


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


def test_variaciones_interanuales_solo_si_son_comparables():
    """D-021: contra 2016, casi vacío, la variación de 2017 daría más de 13.000%."""
    variaciones = {n: m for n, m in _medidas().items() if n.startswith("Var. interanual")}
    assert len(variaciones) == 5
    assert not [n for n, m in variaciones.items() if "[Año anterior comparable]" not in m]


def test_puntaje_negativo_excluye_vacios():
    """En DAX, vacío <= 2 da verdadero: sin el límite inferior, los pedidos sin reseña serían negativos."""
    puntaje = r"\[(?:puntaje_resena|Puntaje de reseña)\]"
    malas = [n for n, m in _medidas().items() if re.search(puntaje + r" *<=", m) and not re.search(puntaje + r" *>= *1", m)]
    assert not malas


# --- Seguridad por fila (Fase 9) ---

def _roles() -> dict[str, str]:
    """Nombre de cada rol -> su definición."""
    return {re.search(r"^role '?(.+?)'?$", p.read_text(encoding="utf-8"), re.M).group(1): p.read_text(encoding="utf-8")
            for p in ROLES.glob("*.tmdl")}


def _permisos(rol: str) -> dict[str, str]:
    return dict(re.findall(r"^\ttablePermission '?(.+?)'? = (.+)$", _roles()[rol], re.M))


def test_roles_declarados_en_el_modelo():
    """Un rol con archivo pero sin su "ref role" en model.tmdl, o al revés, no carga."""
    declarados = set(re.findall(r"^ref role '?(.+?)'?$", (DEFINICION / "model.tmdl").read_text(encoding="utf-8"), re.M))
    assert declarados == set(_roles()) == {"Dirección", "Gerente regional", "Región Centro-Oeste", "Región Nordeste",
                                          "Región Norte", "Región Sudeste", "Región Sur"}


def test_direccion_ve_todo():
    assert _permisos("Dirección") == {}


def test_rol_dinamico_filtra_la_geografia_del_usuario():
    """El filtro va sobre dim_geografia, que filtra los dos hechos; el usuario sale del inicio de sesión."""
    permisos = _permisos("Gerente regional")
    assert set(permisos) == {"dim_geografia", "Gerentes"}
    assert "USERPRINCIPALNAME ()" in permisos["dim_geografia"]
    assert "Gerentes[Email]" in permisos["dim_geografia"]
    assert permisos["Gerentes"] == "[Email] = USERPRINCIPALNAME ()"   # cada gerente ve solo su fila


def test_ningun_rol_estatico_ve_la_tabla_de_gerentes():
    for rol in [r for r in _roles() if r.startswith("Región ")]:
        assert _permisos(rol)["Gerentes"] == "FALSE ()", rol


def test_tabla_de_gerentes_oculta():
    assert "\tisHidden" in (TABLAS / "Gerentes.tmdl").read_text(encoding="utf-8").split("column")[0]


def test_regiones_de_los_gerentes_existen():
    """Una región mal escrita en la carga deja sus estados sin gerente (la validación V16 lo frena en el ETL)."""
    from src.paths import DW_SQL_DIR
    regiones = set(re.findall(r"N'([\w-]+)'\)", (DW_SQL_DIR / "11_dim_geografia.sql").read_text(encoding="utf-8")))
    gerentes = set(re.findall(r"N'[^']+',\s*N'([\w-]+)'\)", (DW_SQL_DIR / "15_seguridad_gerentes.sql").read_text(encoding="utf-8")))
    assert gerentes == regiones - {"Desconocida"}
