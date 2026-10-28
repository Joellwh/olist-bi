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


@pytest.fixture(scope="module")
def referencia():
    from src.kpi_reference import cargar, calcular
    return calcular(cargar())


@pytest.mark.parametrize("kpi", list(KPIS_SQL))
def test_kpi_sql_igual_a_referencia(conn, referencia, kpi):
    valor_sql = conn.execute(KPIS_SQL[kpi]).fetchone()[0]
    esperado = referencia[kpi]
    if isinstance(valor_sql, Decimal):
        valor_sql = float(valor_sql)
    assert valor_sql == pytest.approx(esperado, abs=0.01), f"{kpi}: SQL {valor_sql} vs referencia {esperado}"


def test_ultima_ejecucion_ok(conn):
    estado = conn.execute("SELECT TOP 1 estado FROM etl.log_ejecucion ORDER BY ejecucion_id DESC").fetchone()[0]
    assert estado == "OK"
