"""
Calcula los valores de referencia de los KPIs directamente desde los CSV,
aplicando las reglas de negocio R1-R9 de docs/01_requerimientos.md.

    python -m src.kpi_reference

Son los números contra los que se controla cada capa: las vistas SQL (Fase 5)
y las medidas DAX (Fase 7) tienen que dar lo mismo sin filtros. Si alguno de
estos valores cambia, hay que actualizar docs/kpi_diccionario.md.
"""

import pandas as pd

from src.paths import RAW_DIR

PERIODO_DESDE = "2017-01-01"  # R4: meses completos (D-008)
PERIODO_HASTA = "2018-09-01"  # exclusivo
ESTADOS_NO_VENTA = ["canceled", "unavailable"]  # R1 (D-005)


def cargar() -> dict[str, pd.DataFrame]:
    fechas = ["order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"]
    return {
        "orders": pd.read_csv(RAW_DIR / "olist_orders_dataset.csv", parse_dates=fechas),
        "items": pd.read_csv(RAW_DIR / "olist_order_items_dataset.csv"),
        "reviews": pd.read_csv(RAW_DIR / "olist_order_reviews_dataset.csv", parse_dates=["review_answer_timestamp"]),
        "customers": pd.read_csv(RAW_DIR / "olist_customers_dataset.csv"),
    }


def calcular(t: dict[str, pd.DataFrame]) -> dict[str, float]:
    compra = t["orders"].order_purchase_timestamp
    periodo = t["orders"][(compra >= PERIODO_DESDE) & (compra < PERIODO_HASTA)]
    validos = periodo[~periodo.order_status.isin(ESTADOS_NO_VENTA)].merge(t["customers"], on="customer_id")
    items = t["items"][t["items"].order_id.isin(validos.order_id)]  # R8: sin ítems no hay pedido vendido

    entregados = validos[(validos.order_status == "delivered") & validos.order_delivered_customer_date.notna()]
    # R3 (D-007): se compara la fecha de entrega sin hora contra la estimada
    tarde = entregados.order_delivered_customer_date.dt.normalize() > entregados.order_estimated_delivery_date
    demora = (entregados.order_delivered_customer_date.dt.normalize() - entregados.order_estimated_delivery_date).dt.days
    dias_entrega = (entregados.order_delivered_customer_date - entregados.order_purchase_timestamp).dt.total_seconds() / 86400

    # R7: si un pedido tiene varias reseñas, vale la última respondida
    resenas = (t["reviews"].sort_values("review_answer_timestamp")
               .drop_duplicates("order_id", keep="last"))
    resenas = resenas[resenas.order_id.isin(validos.order_id)]
    puntaje_entrega = entregados.assign(tarde=tarde).merge(resenas, on="order_id")

    pedidos_por_cliente = validos.groupby("customer_unique_id").order_id.nunique()  # R5
    dias_de_compra = validos.groupby("customer_unique_id").order_purchase_timestamp.agg(lambda s: s.dt.normalize().nunique())

    ventas_por_mes = (items.merge(validos[["order_id", "order_purchase_timestamp"]], on="order_id")
                      .set_index("order_purchase_timestamp").price.resample("MS").sum())
    ene_ago_2017 = ventas_por_mes["2017-01":"2017-08"].sum()
    ene_ago_2018 = ventas_por_mes["2018-01":"2018-08"].sum()

    ventas = items.price.sum()
    pedidos = items.order_id.nunique()
    return {
        "K01 Ventas": ventas,
        "K02 Pedidos": pedidos,
        "K03 Ticket promedio": ventas / pedidos,
        "K04 Ítems vendidos": len(items),
        "K05 Ítems por pedido": len(items) / pedidos,
        "K06 Clientes únicos": validos.customer_unique_id.nunique(),
        "K08 Variación interanual % (ene-ago 2018)": ene_ago_2018 / ene_ago_2017 - 1,
        "K09 Ventas acumuladas 2018": ene_ago_2018,
        "K12 Vendedores activos": items.seller_id.nunique(),
        "K13 Ventas entregadas": items[items.order_id.isin(entregados.order_id)].price.sum(),
        "K14 Flete total": items.freight_value.sum(),
        "K15 % flete sobre ventas": items.freight_value.sum() / ventas,
        "K16 Pedidos entregados": len(entregados),
        "K17 % entregas a tiempo": 1 - tarde.mean(),
        "K18 Días promedio de entrega": dias_entrega.mean(),
        "K19 Días promedio de demora": demora[demora > 0].mean(),
        "K20 Pedidos con demora": int(tarde.sum()),
        "K21 Tasa de cancelación": 1 - len(validos) / len(periodo),
        "K22 Puntaje promedio de reseña": resenas.review_score.mean(),
        "K23 % reseñas negativas": (resenas.review_score <= 2).mean(),
        "K24 % reseñas positivas": (resenas.review_score >= 4).mean(),
        "K25 Tasa de recompra": (pedidos_por_cliente > 1).mean(),
        "K28 Tasa de recompra en días distintos": (dias_de_compra > 1).mean(),
        "K26 Brecha de puntaje por demora": (puntaje_entrega[~puntaje_entrega.tarde].review_score.mean()
                                             - puntaje_entrega[puntaje_entrega.tarde].review_score.mean()),
    }


def main() -> None:
    for kpi, valor in calcular(cargar()).items():
        if "%" in kpi or "Tasa" in kpi:
            texto = f"{valor:.2%}"
        elif float(valor).is_integer():
            texto = f"{valor:,.0f}"
        else:
            texto = f"{valor:,.2f}"
        print(f"  {kpi:<45} {texto:>18}")


if __name__ == "__main__":
    main()
