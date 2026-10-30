"""
Tests de integración: necesitan SQL Server con el ETL ya corrido y los CSV en
data/raw/. Si no están (por ejemplo en el CI de GitHub), se saltean solos.

    python -m src.etl.run
    pytest tests/test_integracion_sql.py -v

Verifican lo que los tests unitarios no pueden: que dos implementaciones
independientes den el mismo resultado.
"""

from decimal import Decimal

import pytest

from src.paths import RAW_DIR

pyodbc = pytest.importorskip("pyodbc")


@pytest.fixture(scope="module")
def conn():
    from src.db import connect
    try:
        conexion = connect()
        ok = conexion.execute("SELECT CASE WHEN OBJECT_ID('stg.orders') IS NULL THEN 0"
                              " ELSE (SELECT COUNT(*) FROM stg.orders) END").fetchone()[0]
    except pyodbc.Error:
        pytest.skip("SQL Server no disponible")
    if not ok:
        pytest.skip("stg vacío: correr primero python -m src.etl.run")
    if not (RAW_DIR / "olist_orders_dataset.csv").exists():
        pytest.skip("Faltan los CSV en data/raw/")
    yield conexion
    conexion.close()


def test_normalizacion_sql_igual_a_python(conn):
    """stg.fn_normalizar_texto y src.profiling.normalizar_texto coinciden en todas las ciudades."""
    from src.profiling import normalizar_texto
    filas = conn.execute(
        "SELECT ciudad, stg.fn_normalizar_texto(ciudad) FROM ("
        " SELECT customer_city AS ciudad FROM raw.customers UNION"
        " SELECT seller_city FROM raw.sellers UNION"
        " SELECT geolocation_city FROM raw.geolocation) AS c").fetchall()
    distintas = [(original, sql) for original, sql in filas if normalizar_texto(original) != sql]
    assert not distintas, f"{len(distintas)} ciudades normalizan distinto, por ejemplo: {distintas[:5]}"


# Los KPIs calculados en SQL sobre stg, con las reglas R1-R9, tienen que coincidir
# con src.kpi_reference, que los calcula con pandas directamente sobre los CSV.
_PERIODO = "o.purchase_ts >= '2017-01-01' AND o.purchase_ts < '2018-09-01'"
_VALIDOS = f"{_PERIODO} AND o.order_status NOT IN ('canceled', 'unavailable')"
_ENTREGADOS = f"{_VALIDOS} AND o.order_status = 'delivered' AND o.delivered_customer_ts IS NOT NULL"

KPIS_SQL = {
    "K01 Ventas": f"SELECT SUM(i.price) FROM stg.order_items i JOIN stg.orders o ON o.order_id = i.order_id WHERE {_VALIDOS}",
    "K02 Pedidos": f"SELECT COUNT(DISTINCT i.order_id) FROM stg.order_items i JOIN stg.orders o ON o.order_id = i.order_id WHERE {_VALIDOS}",
    "K06 Clientes únicos": f"SELECT COUNT(DISTINCT c.customer_unique_id) FROM stg.orders o JOIN stg.customers c ON c.customer_id = o.customer_id WHERE {_VALIDOS}",
    "K14 Flete total": f"SELECT SUM(i.freight_value) FROM stg.order_items i JOIN stg.orders o ON o.order_id = i.order_id WHERE {_VALIDOS}",
    "K16 Pedidos entregados": f"SELECT COUNT(*) FROM stg.orders o WHERE {_ENTREGADOS}",
    "K20 Pedidos con demora": f"SELECT COUNT(*) FROM stg.orders o WHERE {_ENTREGADOS} AND CAST(o.delivered_customer_ts AS DATE) > o.estimated_delivery_date",
    "K22 Puntaje promedio de reseña": f"SELECT AVG(CAST(r.review_score AS DECIMAL(9, 6))) FROM stg.order_reviews r JOIN stg.orders o ON o.order_id = r.order_id WHERE r.es_ultima_del_pedido = 1 AND {_VALIDOS}",
}


# Los mismos KPIs sobre el modelo dimensional, usando las columnas de reglas de
# negocio de los hechos (D-016) y el período de dim_fecha (D-008). Así se
# verifica que las reglas calculadas en SQL son las del diccionario.
_P = "JOIN dw.dim_fecha f ON f.fecha_key = {t}.fecha_compra_key AND f.en_periodo_analisis = 1"
_PED = f"FROM dw.fact_pedidos p {_P.format(t='p')}"
_ITE = f"FROM dw.fact_items i {_P.format(t='i')} WHERE i.es_venta = 1"

KPIS_DW = {
    "K01 Ventas": f"SELECT SUM(i.precio) {_ITE}",
    "K02 Pedidos": f"SELECT COUNT(*) {_PED} WHERE p.es_vendido = 1",
    "K06 Clientes únicos": f"SELECT COUNT(DISTINCT p.cliente_key) {_PED} WHERE p.es_valido = 1",
    "K14 Flete total": f"SELECT SUM(i.flete) {_ITE}",
    "K16 Pedidos entregados": f"SELECT COUNT(*) {_PED} WHERE p.es_valido = 1 AND p.es_entregado = 1",
    "K17 % entregas a tiempo": f"SELECT AVG(CAST(p.a_tiempo AS FLOAT)) {_PED} WHERE p.es_valido = 1 AND p.es_entregado = 1",
    "K18 Días promedio de entrega": f"SELECT AVG(p.dias_entrega) {_PED} WHERE p.es_valido = 1 AND p.es_entregado = 1",
    "K19 Días promedio de demora": f"SELECT AVG(CAST(p.dias_vs_estimada AS FLOAT)) {_PED} WHERE p.es_valido = 1 AND p.dias_vs_estimada > 0",
    "K20 Pedidos con demora": f"SELECT COUNT(*) {_PED} WHERE p.es_valido = 1 AND p.a_tiempo = 0",
    "K22 Puntaje promedio de reseña": f"SELECT AVG(CAST(p.puntaje_resena AS FLOAT)) {_PED} WHERE p.es_valido = 1",
    "K23 % reseñas negativas": f"SELECT AVG(CASE WHEN p.puntaje_resena <= 2 THEN 1.0 ELSE 0 END) {_PED} WHERE p.es_valido = 1 AND p.puntaje_resena IS NOT NULL",
    "K25 Tasa de recompra": f"SELECT AVG(CASE WHEN n > 1 THEN 1.0 ELSE 0 END) FROM (SELECT p.cliente_key, COUNT(*) AS n {_PED} WHERE p.es_valido = 1 GROUP BY p.cliente_key) AS c",
    "K28 Tasa de recompra en días distintos": f"SELECT AVG(CASE WHEN dias > 1 THEN 1.0 ELSE 0 END) FROM (SELECT p.cliente_key, COUNT(DISTINCT f.fecha) AS dias {_PED} WHERE p.es_valido = 1 GROUP BY p.cliente_key) AS c",
    "K26 Brecha de puntaje por demora": f"SELECT AVG(CASE WHEN p.a_tiempo = 1 THEN CAST(p.puntaje_resena AS FLOAT) END) - AVG(CASE WHEN p.a_tiempo = 0 THEN CAST(p.puntaje_resena AS FLOAT) END) {_PED} WHERE p.es_valido = 1",
}


@pytest.fixture(scope="module")
def referencia():
    from src.kpi_reference import cargar, calcular
    return calcular(cargar())


@pytest.mark.parametrize("capa, kpi", [("stg", k) for k in KPIS_SQL] + [("dw", k) for k in KPIS_DW])
def test_kpi_sql_igual_a_referencia(conn, referencia, capa, kpi):
    consulta = (KPIS_SQL if capa == "stg" else KPIS_DW)[kpi]
    valor_sql = conn.execute(consulta).fetchone()[0]
    esperado = referencia[kpi]
    if isinstance(valor_sql, Decimal):
        valor_sql = float(valor_sql)
    # Tolerancia: un centavo en montos; 0,00005 en porcentajes (se muestran con 1 o 2 decimales)
    tolerancia = 0.00005 if abs(esperado) < 1 else 0.01
    assert valor_sql == pytest.approx(esperado, abs=tolerancia), f"{capa} {kpi}: SQL {valor_sql} vs referencia {esperado}"


def test_ultima_ejecucion_ok(conn):
    estado = conn.execute("SELECT TOP 1 estado FROM etl.log_ejecucion ORDER BY ejecucion_id DESC").fetchone()[0]
    assert estado == "OK"


# --- Vistas analíticas (rpt, Fase 5): cada una tiene que cerrar con los KPIs ---

def _valor(conn, sql):
    valor = conn.execute(sql).fetchone()[0]
    return float(valor) if isinstance(valor, Decimal) else valor


def test_ventas_mensuales_cierra_con_k01_k08_k09(conn, referencia):
    assert _valor(conn, "SELECT SUM(ventas) FROM rpt.ventas_mensuales WHERE en_periodo_analisis = 1") \
        == pytest.approx(referencia["K01 Ventas"], abs=0.01)
    assert _valor(conn, "SELECT acumulado_anio FROM rpt.ventas_mensuales WHERE anio_mes = 201808") \
        == pytest.approx(referencia["K09 Ventas acumuladas 2018"], abs=0.01)
    interanual = _valor(conn, "SELECT SUM(CASE WHEN anio = 2018 THEN ventas END) / SUM(CASE WHEN anio = 2017 THEN ventas END) - 1"
                              " FROM rpt.ventas_mensuales WHERE mes <= 8 AND anio IN (2017, 2018)")
    assert interanual == pytest.approx(referencia["K08 Variación interanual % (ene-ago 2018)"], abs=0.00005)


def test_ventas_mensuales_no_saltea_meses_sin_ventas(conn):
    """Nov-2016 no tuvo pedidos: tiene que aparecer con 0, y nov-2017 sin variación interanual."""
    fila = conn.execute("SELECT ventas FROM rpt.ventas_mensuales WHERE anio_mes = 201611").fetchone()
    assert fila is not None and fila[0] == 0
    assert conn.execute("SELECT variacion_interanual FROM rpt.ventas_mensuales WHERE anio_mes = 201711").fetchone()[0] is None
    meses = conn.execute("SELECT COUNT(*), COUNT(DISTINCT anio_mes) FROM rpt.ventas_mensuales").fetchone()
    assert tuple(meses) == (26, 26)   # sep-2016 a oct-2018, uno por fila


def test_cohortes(conn):
    # El mes 0 es la definición de la cohorte: retención 100% siempre
    assert conn.execute("SELECT COUNT(*) FROM rpt.cohortes WHERE meses_desde = 0 AND retencion <> 1").fetchone()[0] == 0
    # Cada persona con un pedido válido está en exactamente una cohorte
    personas = conn.execute("SELECT COUNT(*) FROM dw.dim_cliente WHERE cohorte IS NOT NULL").fetchone()[0]
    assert conn.execute("SELECT SUM(clientes) FROM rpt.cohortes WHERE meses_desde = 0").fetchone()[0] == personas


def test_recompra_una_fila_por_persona(conn):
    personas = conn.execute("SELECT COUNT(*) FROM dw.dim_cliente WHERE cohorte IS NOT NULL").fetchone()[0]
    assert tuple(conn.execute("SELECT COUNT(*), COUNT(DISTINCT cliente_key) FROM rpt.recompra_clientes").fetchone()) == (personas, personas)
    assert conn.execute("SELECT COUNT(*) FROM rpt.recompra_clientes WHERE es_recompra = 1 AND segunda_compra IS NULL").fetchone()[0] == 0


def test_ranking_vendedores(conn, referencia):
    total, participacion, primero, cuartiles = conn.execute(
        "SELECT SUM(ventas), SUM(participacion), MIN(ranking_total), COUNT(DISTINCT cuartil) FROM rpt.ranking_vendedores").fetchone()
    assert float(total) == pytest.approx(referencia["K01 Ventas"], abs=0.01)
    assert float(participacion) == pytest.approx(1, abs=0.001)
    assert (primero, cuartiles) == (1, 4)
    assert conn.execute("SELECT COUNT(*) FROM rpt.ranking_vendedores").fetchone()[0] == referencia["K12 Vendedores activos"]


def test_rfm_cierra_con_k01_y_k06(conn, referencia):
    personas, monto = conn.execute("SELECT COUNT(*), SUM(monto) FROM rpt.rfm_clientes").fetchone()
    assert personas == referencia["K06 Clientes únicos"]
    assert float(monto) == pytest.approx(referencia["K01 Ventas"], abs=0.01)
    assert conn.execute("SELECT COUNT(*) FROM rpt.rfm_clientes WHERE segmento IS NULL").fetchone()[0] == 0
