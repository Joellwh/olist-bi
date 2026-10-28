"""
Reglas de validación del ETL, tal como están definidas en docs/02_calidad_datos.md.

Cada regla es una consulta que devuelve un solo número: cuántas filas la rompen.
Cero es OK. Si es mayor a cero, una regla CRITICA corta la carga y una
ADVERTENCIA se registra con la cantidad y la carga sigue (D-009).

Las reglas se agrupan por capa: las de raw corren apenas se cargan los CSV
(antes de tipar, porque stg tiene claves primarias y un duplicado haría fallar
el INSERT con un error poco claro); las de stg, después de construir staging.
"""

from dataclasses import dataclass

from src.paths import RAW_FILES

CRITICA = "CRITICA"
ADVERTENCIA = "ADVERTENCIA"


@dataclass(frozen=True)
class Validacion:
    codigo: str
    gravedad: str
    descripcion: str
    sql: str


def resultado(gravedad: str, filas_afectadas: int) -> str:
    """OK si no hay filas afectadas; si no, FALLA (crítica) o AVISO (advertencia)."""
    if filas_afectadas == 0:
        return "OK"
    return "FALLA" if gravedad == CRITICA else "AVISO"


def _claves_repetidas(tabla: str, clave: str) -> str:
    return f"SELECT COUNT(*) FROM (SELECT 1 AS x FROM {tabla} GROUP BY {clave} HAVING COUNT(*) > 1) AS d"


def _huerfanos(hijo: str, col_hijo: str, padre: str, col_padre: str) -> str:
    return (f"SELECT COUNT(*) FROM {hijo} AS h LEFT JOIN {padre} AS p ON p.{col_padre} = h.{col_hijo} "
            f"WHERE h.{col_hijo} IS NOT NULL AND p.{col_padre} IS NULL")


# Archivo CSV -> tabla raw, para comparar la cantidad de filas (V01).
_TABLA_RAW = {
    "olist_customers_dataset.csv": "raw.customers",
    "olist_geolocation_dataset.csv": "raw.geolocation",
    "olist_order_items_dataset.csv": "raw.order_items",
    "olist_order_payments_dataset.csv": "raw.order_payments",
    "olist_order_reviews_dataset.csv": "raw.order_reviews",
    "olist_orders_dataset.csv": "raw.orders",
    "olist_products_dataset.csv": "raw.products",
    "olist_sellers_dataset.csv": "raw.sellers",
    "product_category_name_translation.csv": "raw.category_translation",
}

VALIDACIONES_RAW: list[Validacion] = [
    *[Validacion("V01", CRITICA, f"{tabla} tiene las {esperadas:,} filas del CSV".replace(",", "."),
                 f"SELECT ABS(COUNT(*) - {esperadas}) FROM {tabla}")
      for archivo, esperadas in RAW_FILES.items() for tabla in [_TABLA_RAW[archivo]]],
    *[Validacion("V02", CRITICA, f"Clave única en {tabla} ({clave})", _claves_repetidas(tabla, clave))
      for tabla, clave in [
          ("raw.orders", "order_id"),
          ("raw.order_items", "order_id, order_item_id"),
          ("raw.order_payments", "order_id, payment_sequential"),
          ("raw.order_reviews", "review_id, order_id"),
          ("raw.customers", "customer_id"),
          ("raw.sellers", "seller_id"),
          ("raw.products", "product_id"),
          ("raw.categorias_es", "category_name_pt"),
      ]],
    Validacion("V07", CRITICA, "Códigos postales de 5 dígitos (clientes, vendedores, geolocalización)",
               "SELECT (SELECT COUNT(*) FROM raw.customers WHERE customer_zip_code_prefix NOT LIKE '[0-9][0-9][0-9][0-9][0-9]')"
               " + (SELECT COUNT(*) FROM raw.sellers WHERE seller_zip_code_prefix NOT LIKE '[0-9][0-9][0-9][0-9][0-9]')"
               " + (SELECT COUNT(*) FROM raw.geolocation WHERE geolocation_zip_code_prefix NOT LIKE '[0-9][0-9][0-9][0-9][0-9]')"),
    # Advertencias que se miden sobre el origen, antes de que stg las corrija
    Validacion("V12", ADVERTENCIA, "Pagos not_defined, con valor 0 o con 0 cuotas",
               "SELECT COUNT(*) FROM raw.order_payments WHERE payment_type = 'not_defined'"
               " OR CAST(payment_value AS DECIMAL(10, 2)) <= 0 OR payment_installments = '0'"),
    Validacion("V14", ADVERTENCIA, "Puntos de geolocalización fuera de Brasil (descartados)",
               "SELECT COUNT(*) FROM raw.geolocation"
               " WHERE CAST(geolocation_lat AS FLOAT) NOT BETWEEN -33.8 AND 5.3"
               " OR CAST(geolocation_lng AS FLOAT) NOT BETWEEN -74.0 AND -34.7"),
]

VALIDACIONES_STG: list[Validacion] = [
    *[Validacion("V03", CRITICA, f"Sin huérfanos: {hijo}.{col} -> {padre}", _huerfanos(hijo, col, padre, col_padre))
      for hijo, col, padre, col_padre in [
          ("stg.orders", "customer_id", "stg.customers", "customer_id"),
          ("stg.order_items", "order_id", "stg.orders", "order_id"),
          ("stg.order_items", "product_id", "stg.products", "product_id"),
          ("stg.order_items", "seller_id", "stg.sellers", "seller_id"),
          ("stg.order_payments", "order_id", "stg.orders", "order_id"),
          ("stg.order_reviews", "order_id", "stg.orders", "order_id"),
      ]],
    Validacion("V04", CRITICA, "Precio > 0, flete >= 0 y valor de pago >= 0",
               "SELECT (SELECT COUNT(*) FROM stg.order_items WHERE price <= 0 OR freight_value < 0)"
               " + (SELECT COUNT(*) FROM stg.order_payments WHERE payment_value < 0)"),
    Validacion("V05", CRITICA, "Entrega y entrega estimada no anteriores a la compra",
               "SELECT COUNT(*) FROM stg.orders WHERE delivered_customer_ts < purchase_ts"
               " OR estimated_delivery_date < CAST(purchase_ts AS DATE)"),
    Validacion("V06", CRITICA, "Puntaje de reseña entre 1 y 5",
               "SELECT COUNT(*) FROM stg.order_reviews WHERE review_score NOT BETWEEN 1 AND 5"),
    Validacion("V08", CRITICA, "Conciliación raw -> stg: misma cantidad de filas en las 7 tablas transaccionales",
               "SELECT " + " + ".join(
                   f"ABS((SELECT COUNT(*) FROM raw.{t}) - (SELECT COUNT(*) FROM stg.{t}))"
                   for t in ["orders", "order_items", "order_payments", "order_reviews", "customers", "sellers", "products"])),
    Validacion("V08", CRITICA, "Conciliación raw -> stg: ventas y flete (diferencia en centavos)",
               "SELECT CAST(ABS((SELECT SUM(price + freight_value) FROM stg.order_items)"
               " - (SELECT SUM(CAST(price AS DECIMAL(12, 2)) + CAST(freight_value AS DECIMAL(12, 2))) FROM raw.order_items))"
               " * 100 AS INT)"),
    Validacion("V09", ADVERTENCIA, "Fechas intermedias desordenadas (aprobación, despacho, entrega)",
               "SELECT COUNT(*) FROM stg.orders WHERE delivered_carrier_ts < purchase_ts"
               " OR delivered_carrier_ts < approved_ts OR delivered_customer_ts < delivered_carrier_ts"),
    Validacion("V10", ADVERTENCIA, "Pedidos entregados sin fecha de entrega",
               "SELECT COUNT(*) FROM stg.orders WHERE order_status = 'delivered' AND delivered_customer_ts IS NULL"),
    Validacion("V11", ADVERTENCIA, "Reseñas creadas antes de la compra",
               "SELECT COUNT(*) FROM stg.order_reviews WHERE creada_antes_de_compra = 1"),
    Validacion("V13", ADVERTENCIA, "Productos sin categoría",
               "SELECT COUNT(*) FROM stg.products WHERE category_name_pt IS NULL"),
    Validacion("V13", ADVERTENCIA, "Categorías de productos sin nombre en español",
               _huerfanos("stg.products", "category_name_pt", "stg.categorias", "category_name_pt")),
]
