# Requerimientos de negocio

**Fase:** 1 · **Estado:** aprobado (2026-10-23) · **Diccionario de KPIs:** [kpi_diccionario.md](kpi_diccionario.md)

Este documento traduce las necesidades de tres áreas de Olist en preguntas de negocio, KPIs y páginas de tablero con criterios de aceptación. Las áreas son ficticias; los datos son reales.

---

## 1. Contexto

Olist es un marketplace brasileño que conecta vendedores pequeños con grandes plataformas de e-commerce. El dataset cubre unos 99 mil pedidos entre 2016 y 2018, con ítems, pagos, reseñas, clientes y vendedores de los 27 estados de Brasil.

Hoy cada área arma sus números a mano, con criterios distintos: Comercial cuenta como venta lo que Logística todavía no entregó, y nadie sabe si "cliente" es una cuenta o una persona. El objetivo es **una única fuente de verdad**: un modelo con definiciones acordadas y un tablero por área.

## 2. Alcance

**Incluido**
- Pedidos con fecha de compra entre **2017-01-01 y 2018-08-31** (20 meses completos). Ver [D-008](decisiones.md#d-008--período-de-análisis-ene-2017-a-ago-2018).
- Ventas, logística de entrega y experiencia del cliente (reseñas y recompra).
- Seguridad por región: cada gerente regional ve solo sus estados (Fase 9).

**Fuera de alcance**
- Rentabilidad: el dataset no trae costos de producto ni comisiones de Olist.
- Marketing y adquisición: no hay datos de campañas ni de tráfico.
- Pronósticos: el tablero es descriptivo; un modelo predictivo sería otro proyecto.
- Análisis del texto de las reseñas (están en portugués y la mayoría vienen vacías).

## 3. Stakeholders

| Área | Responsable (ficticio) | Qué decide con el tablero | Frecuencia de uso |
|---|---|---|---|
| **Dirección Comercial** | Directora Comercial | Qué categorías y vendedores impulsar, en qué regiones crecer | Semanal |
| **Logística** | Jefe de Operaciones Logísticas | Dónde se concentran las demoras y qué rutas renegociar con transportistas | Diaria |
| **Experiencia de cliente** | Responsable de CX | Qué causa las malas reseñas y cómo mejorar la recompra | Semanal |
| **Gerentes regionales** | Uno por región | Lo mismo que Comercial, limitado a sus estados | Semanal |

## 4. Preguntas de negocio

Cada pregunta tiene un código que se usa en los criterios de aceptación (sección 7) y en las pruebas de la Fase 8.

### Dirección Comercial

| Código | Pregunta | KPIs |
|---|---|---|
| **C1** | ¿Cuánto vendemos y cómo evoluciona mes a mes? ¿Crecemos contra el año anterior? | K01, K07, K08, K09, K10 |
| **C2** | ¿Qué categorías concentran las ventas y cuáles crecen más? | K01, K08, K11 |
| **C3** | ¿Qué estados compran más y cuál es su ticket promedio? | K01, K02, K03 |
| **C4** | ¿Qué vendedores son los más importantes y qué peso tienen en el total? | K01, K11, K12 |
| **C5** | ¿Los clientes compran más de un producto por pedido? | K04, K05 |

### Logística

| Código | Pregunta | KPIs |
|---|---|---|
| **L1** | ¿Qué porcentaje de pedidos llega en la fecha prometida y cómo evoluciona? | K17 |
| **L2** | ¿Cuántos días tarda un pedido en llegar, según el estado del cliente? | K18 |
| **L3** | Cuando llegamos tarde, ¿por cuántos días? ¿En qué rutas (estado del vendedor → estado del cliente)? | K19, K20 |
| **L4** | ¿Cuánto pesa el flete sobre la venta, por región y por categoría? | K14, K15 |
| **L5** | ¿Cuántos pedidos se cancelan o quedan sin stock? | K21 |

### Experiencia de cliente

| Código | Pregunta | KPIs |
|---|---|---|
| **X1** | ¿Cómo califican los clientes su compra y cómo evoluciona? | K22, K23, K24 |
| **X2** | ¿Cuánto empeora la reseña cuando el pedido llega tarde? | K22, K26 |
| **X3** | ¿Qué categorías y vendedores reciben más reseñas negativas? | K23 |
| **X4** | ¿Qué porcentaje de clientes vuelve a comprar? ¿Cuánto tardan? | K25 |
| **X5** | De los clientes que compraron por primera vez en un mes, ¿cuántos vuelven en los meses siguientes? | K27 |

## 5. Reglas de negocio acordadas

Estas reglas se aplican igual en SQL, en Python y en DAX. El detalle y los valores de referencia están en el [diccionario de KPIs](kpi_diccionario.md).

| # | Regla | Decisión |
|---|---|---|
| R1 | **¿Qué es una venta?** | Todo pedido salvo los `canceled` y `unavailable`. Se vende al confirmar, no al entregar. ([D-005](decisiones.md#d-005--qué-pedidos-cuentan-como-venta)) |
| R2 | **¿El flete es venta?** | No. Ventas = precio de los productos. El flete es un KPI aparte. ([D-006](decisiones.md#d-006--el-flete-no-forma-parte-de-la-venta)) |
| R3 | **¿Qué es "a tiempo"?** | Entregado hasta el día estimado prometido al cliente, comparando fechas sin hora. ([D-007](decisiones.md#d-007--a-tiempo-contra-la-fecha-estimada-por-día)) |
| R4 | **Período** | Compras entre 2017-01-01 y 2018-08-31. ([D-008](decisiones.md#d-008--período-de-análisis-ene-2017-a-ago-2018)) |
| R5 | **¿Qué es un cliente?** | Una persona (`customer_unique_id`). El `customer_id` del dataset cambia en cada pedido, así que contarlo daría un cliente por pedido. |
| R6 | **Fecha de referencia** | Todos los KPIs se ubican en el tiempo por la **fecha de compra**, incluidas entregas y reseñas, para poder relacionar demora y reseña de un mismo pedido. |
| R7 | **Reseñas duplicadas** | Si un pedido tiene varias reseñas, vale la última respondida. |
| R8 | **Pedidos sin ítems** | No cuentan como pedido vendido (son 5 en el período, todos en estados intermedios). |
| R9 | **Región** | La región comercial es la del **cliente**. El estado del vendedor se usa solo para analizar rutas logísticas (L3). |

## 6. Páginas del tablero

| # | Página | Para quién | Preguntas |
|---|---|---|---|
| 1 | **Resumen ejecutivo** | Dirección | C1, L1, X1 (una cifra de cada área) |
| 2 | **Comercial** | Comercial, gerentes regionales | C1–C5 |
| 3 | **Logística** | Logística | L1–L5 |
| 4 | **Cliente** | CX | X1–X5 |
| 5 | **Detalle de vendedor** (drill-through) | Comercial, CX | C4, X3 para un vendedor puntual |

Filtros comunes a todas las páginas: período, región/estado del cliente y categoría de producto.

## 7. Criterios de aceptación

Una página está terminada cuando cumple todos sus criterios. Se verifican en la Fase 8.

**Generales (todas las páginas)**
- [ ] Cada pregunta asignada a la página se responde sin exportar datos ni usar otra herramienta.
- [ ] Los totales coinciden con los valores de referencia del diccionario de KPIs (tolerancia: redondeo).
- [ ] Los filtros de período, región y categoría están sincronizados entre páginas y hay un botón para limpiarlos.
- [ ] Cada visual tarda menos de 2 segundos en Performance Analyzer.
- [ ] Un gerente regional ve solo sus estados, y los totales de todas las páginas cambian en consecuencia (Fase 9).

**1. Resumen ejecutivo**
- [ ] Muestra Ventas, Pedidos, Ticket promedio, % a tiempo y Puntaje promedio, cada uno con su variación interanual.
- [ ] Incluye la tendencia mensual de ventas contra el año anterior.
- [ ] Se entiende en menos de 10 segundos: sin más de 6 visuales.

**2. Comercial**
- [ ] Ranking de categorías con ventas, participación y variación interanual (C2).
- [ ] Mapa o ranking de estados con ventas y ticket promedio (C3).
- [ ] Top N vendedores con N elegible por el usuario (C4).
- [ ] Clic derecho en un vendedor lleva a su página de detalle.

**3. Logística**
- [ ] % a tiempo por mes, con una línea de referencia del promedio (L1).
- [ ] Días de entrega por estado del cliente (L2).
- [ ] Matriz de rutas (estado vendedor × estado cliente) coloreada por demora (L3).
- [ ] % de flete por región y categoría (L4).

**4. Cliente**
- [ ] Distribución de puntajes de 1 a 5 y su evolución (X1).
- [ ] Comparación directa del puntaje a tiempo contra tarde (X2).
- [ ] Tabla de cohortes por mes de primera compra (X5).

**5. Detalle de vendedor**
- [ ] Muestra ventas, pedidos, % a tiempo y puntaje del vendedor elegido, con su evolución mensual.
- [ ] Tiene un botón para volver a la página de origen.

## 8. Supuestos y riesgos

- **Recompra muy baja (3%).** Es una característica del marketplace (los clientes compran a través de otras tiendas), no un error de datos. Las cohortes (X5) van a mostrar retenciones muy chicas; el tablero tiene que explicarlo para que no se lea como una falla.
- **Crecimiento interanual alto (+138% en ene–ago 2018).** Refleja que la plataforma estaba en plena expansión en 2017. Comparar meses sueltos de principios de 2017 exagera el crecimiento.
- **RLS sin usuarios reales.** Los gerentes regionales son ficticios; la seguridad se prueba con "Ver como rol" en Power BI Desktop.
- **Las reglas pueden cambiar.** Si un área pide otra definición (por ejemplo, contar el flete como venta), se registra una nueva decisión y se crea una medida nueva en vez de modificar la existente.
