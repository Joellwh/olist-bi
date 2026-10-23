# Diccionario de KPIs

**Fase:** 1 · **Requerimientos:** [01_requerimientos.md](01_requerimientos.md)

Cada KPI tiene una única definición, que se implementa igual en SQL (Fase 5) y en DAX (Fase 7). El código (K01, K02…) es el que se usa en los requerimientos, en las descripciones de las medidas de Power BI y en los tests.

## Cómo leer este documento

- **Fórmula:** en lenguaje de negocio, con los nombres de columna del dataset original. Los nombres de tablas y columnas del modelo se definen en la Fase 4.
- **Granularidad:** el nivel más fino al que el KPI tiene sentido. Se puede agregar hacia arriba (mes, estado, categoría), nunca bajar más.
- **Valor de referencia:** calculado con `python -m src.kpi_reference` sobre los CSV, aplicando las reglas R1–R9 al período completo (2017-01-01 a 2018-08-31). **Power BI tiene que dar el mismo número** sin filtros; si no coincide, hay un error en alguna capa.

## Filtros base

Salvo que el KPI diga otra cosa, todos parten de estos conjuntos:

| Conjunto | Definición | Pedidos en el período |
|---|---|---|
| **Pedidos del período** | Fecha de compra entre 2017-01-01 y 2018-08-31 | 99.092 |
| **Pedidos válidos** | Pedidos del período, salvo estado `canceled` o `unavailable` (R1) | 97.910 |
| **Pedidos vendidos** | Pedidos válidos con al menos un ítem (R8) | 97.905 |
| **Pedidos entregados** | Pedidos válidos con estado `delivered` y fecha de entrega cargada | 96.203 |
| **Reseñas válidas** | Última reseña de cada pedido válido (R7) | 97.181 |

---

## Comercial

| Código | KPI | Fórmula | Origen | Granularidad | Valor de referencia |
|---|---|---|---|---|---|
| **K01** | Ventas | Suma de `price` de los ítems de pedidos vendidos. No incluye flete (R2). | order_items + orders | Ítem | R$ 13.449.529,68 |
| **K02** | Pedidos | Cantidad de pedidos vendidos distintos. | orders + order_items | Pedido | 97.905 |
| **K03** | Ticket promedio | K01 / K02 | — | Pedido | R$ 137,37 |
| **K04** | Ítems vendidos | Cantidad de filas de ítems de pedidos vendidos. Cada fila es una unidad. | order_items | Ítem | 111.752 |
| **K05** | Ítems por pedido | K04 / K02 | — | Pedido | 1,14 |
| **K06** | Clientes únicos | Cantidad de `customer_unique_id` distintos con al menos un pedido válido (R5). | orders + customers | Cliente | 94.707 |
| **K07** | Ventas año anterior | K01 desplazado 12 meses hacia atrás (mismo período del año anterior). | — | Mes | Sin valor único: depende del mes |
| **K08** | Variación interanual % | (K01 − K07) / K07. Vacío si K07 = 0. | — | Mes | +138,3% (ene–ago 2018: R$ 7.341.037,41 contra ene–ago 2017: R$ 3.080.850,81) |
| **K09** | Ventas acumuladas del año | K01 desde el 1 de enero del año hasta la fecha del contexto. | — | Día | 2018 al 31-ago: R$ 7.341.037,41 |
| **K10** | Media móvil 3 meses | Promedio de K01 de los últimos 3 meses, incluido el actual. Vacío si no hay 3 meses de datos. | — | Mes | Sin valor único |
| **K11** | Participación % | K01 del elemento / K01 del total visible (respeta los filtros de la página). | — | Variable | Sin filtros: 100% |
| **K12** | Vendedores activos | Cantidad de `seller_id` distintos con al menos un ítem en pedidos vendidos. | order_items | Vendedor | 3.029 |
| **K13** | Ventas entregadas | K01 restringido a pedidos entregados. Sirve para conciliar con Logística. | order_items + orders | Ítem | R$ 13.179.777,95 |

## Logística

| Código | KPI | Fórmula | Origen | Granularidad | Valor de referencia |
|---|---|---|---|---|---|
| **K14** | Flete total | Suma de `freight_value` de los ítems de pedidos vendidos. | order_items | Ítem | R$ 2.234.177,06 |
| **K15** | % flete sobre ventas | K14 / K01 | — | Ítem | 16,6% |
| **K16** | Pedidos entregados | Cantidad de pedidos entregados (ver filtros base). | orders | Pedido | 96.203 |
| **K17** | % entregas a tiempo | Pedidos entregados con fecha de entrega (sin hora) ≤ fecha estimada, sobre K16 (R3). | orders | Pedido | 93,2% |
| **K18** | Días promedio de entrega | Promedio de (`order_delivered_customer_date` − `order_purchase_timestamp`) en días con decimales, sobre pedidos entregados. | orders | Pedido | 12,54 días (mediana: 10,21) |
| **K19** | Días promedio de demora | Promedio de (fecha de entrega − fecha estimada) en días enteros, **solo pedidos tardíos**. | orders | Pedido | 10,62 días |
| **K20** | Pedidos con demora | K16 − pedidos a tiempo. | orders | Pedido | 6.531 |
| **K21** | Tasa de cancelación | Pedidos `canceled` o `unavailable` / pedidos del período. Es el único KPI que **no** parte de pedidos válidos. | orders | Pedido | 1,19% (1.182 pedidos) |

## Experiencia de cliente

| Código | KPI | Fórmula | Origen | Granularidad | Valor de referencia |
|---|---|---|---|---|---|
| **K22** | Puntaje promedio de reseña | Promedio de `review_score` (1 a 5) de las reseñas válidas. | order_reviews | Pedido | 4,12 |
| **K23** | % reseñas negativas | Reseñas válidas con puntaje 1 o 2 / reseñas válidas. | order_reviews | Pedido | 13,9% |
| **K24** | % reseñas positivas | Reseñas válidas con puntaje 4 o 5 / reseñas válidas. | order_reviews | Pedido | 77,9% |
| **K25** | Tasa de recompra | Clientes únicos con 2 o más pedidos válidos / K06. | orders + customers | Cliente | 3,0% |
| **K26** | Brecha de puntaje por demora | K22 de pedidos a tiempo − K22 de pedidos tardíos. Solo pedidos entregados con reseña. | orders + order_reviews | Pedido | 2,02 puntos (4,29 a tiempo contra 2,27 tarde) |
| **K27** | Retención por cohorte | De los clientes cuya primera compra válida fue en el mes M, % que vuelve a comprar en el mes M+n. | orders + customers | Cliente × mes | Se calcula en la Fase 5 (vista `rpt` de cohortes) |

---

## Hallazgos que ya dejan los valores de referencia

- **La demora destruye la reseña:** un pedido tardío promedia 2,27 puntos contra 4,29 de uno a tiempo (K26). Es el hallazgo central para CX y Logística.
- **El flete pesa:** 16,6 centavos por cada real de producto (K15). Vale la pena ver si es mayor en el Norte y Nordeste, lejos de los vendedores de São Paulo.
- **Casi nadie vuelve:** 3% de recompra (K25). Ver el riesgo en [01_requerimientos.md](01_requerimientos.md#8-supuestos-y-riesgos).

## Cambios a este diccionario

Un KPI publicado no se redefine: si cambia la regla, se crea un KPI nuevo con otro código y se registra la decisión en [decisiones.md](decisiones.md). Así un número que alguien vio en una reunión sigue significando lo mismo.
