"""
Benchmark de estrategias de índices sobre el modelo dimensional (Fase 5).

    python -m src.optimizacion

Corre un conjunto de consultas típicas de los tableros contra cada estrategia
y mide, para cada una:

  - lecturas lógicas (páginas de 8 KB leídas, de memoria o disco): la métrica
    principal, porque no depende de qué más esté haciendo la PC. Suma las de
    rowstore y las "lob logical reads", que es donde el columnstore informa
    las suyas, y las de las tablas de trabajo internas (Worktable)
  - CPU en milisegundos (mediana de varias corridas, con la caché caliente)
  - cómo accede el plan a las tablas de hechos (scan, seek, columnstore) y si
    algún operador corre en modo batch (miles de filas por vez en lugar de una)

Al terminar deja la base con la estrategia elegida (sql/03_dw/90_indices.sql),
que es la misma que crea el ETL. Los resultados se documentan en
docs/04_optimizacion_sql.md.
"""

import re
import statistics
import time
import xml.etree.ElementTree as ET

import pyodbc

from src.db import connect, run_script
from src.paths import DW_SQL_DIR

CORRIDAS = 5   # la primera calienta la caché y se descarta

# Consultas representativas: agregaciones grandes (como las de un tablero),
# búsquedas puntuales (un cliente, un vendedor) y las vistas de rpt.
CONSULTAS = {
    "Ventas por categoría (2018)": """
        SELECT p.categoria, SUM(i.precio) AS ventas
        FROM dw.fact_items AS i
        JOIN dw.dim_producto AS p ON p.producto_key = i.producto_key
        JOIN dw.dim_fecha AS f ON f.fecha_key = i.fecha_compra_key
        WHERE f.anio = 2018 AND i.es_venta = 1
        GROUP BY p.categoria""",
    "% a tiempo por estado": """
        SELECT g.estado, AVG(CAST(p.a_tiempo AS FLOAT)) AS pct
        FROM dw.fact_pedidos AS p
        JOIN dw.dim_geografia AS g ON g.geografia_key = p.geografia_key
        JOIN dw.dim_fecha AS f ON f.fecha_key = p.fecha_compra_key
        WHERE f.en_periodo_analisis = 1 AND p.es_entregado = 1
        GROUP BY g.estado""",
    "Pedidos de un cliente": """
        SELECT p.pedido_id, p.fecha_compra_key, p.estado_pedido, p.puntaje_resena
        FROM dw.fact_pedidos AS p
        JOIN dw.dim_cliente AS c ON c.cliente_key = p.cliente_key
        WHERE c.customer_unique_id = '8d50f5eadf50201ccdcedfb9e2ac8455'  -- el cliente con más pedidos
        """,
    "Ventas mensuales de un vendedor": """
        SELECT f.anio_mes, SUM(i.precio) AS ventas
        FROM dw.fact_items AS i
        JOIN dw.dim_fecha AS f ON f.fecha_key = i.fecha_compra_key
        WHERE i.vendedor_key = (SELECT vendedor_key FROM dw.dim_vendedor
                                WHERE seller_id = '4869f7a5dfa277a7dca6462dcf3b52b2')
          AND i.es_venta = 1
        GROUP BY f.anio_mes""",
    "rpt.cohortes": "SELECT cohorte, meses_desde, retencion FROM rpt.cohortes",
    "rpt.ranking_vendedores": "SELECT vendedor_key, ranking_region, cuartil FROM rpt.ranking_vendedores",
    "rpt.rfm_clientes (por segmento)": "SELECT segmento, COUNT(*) FROM rpt.rfm_clientes GROUP BY segmento",
}

_QUITAR_INDICES = """
    DROP INDEX IF EXISTS ix_fact_items_vendedor ON dw.fact_items;
    DROP INDEX IF EXISTS ix_fact_items_fecha ON dw.fact_items;
    DROP INDEX IF EXISTS ix_fact_items_producto ON dw.fact_items;
    DROP INDEX IF EXISTS ix_fact_pedidos_cliente ON dw.fact_pedidos;
    DROP INDEX IF EXISTS ix_fact_pedidos_fecha ON dw.fact_pedidos;
    DROP INDEX IF EXISTS ncci_fact_items ON dw.fact_items;
    DROP INDEX IF EXISTS ncci_fact_pedidos ON dw.fact_pedidos;"""

_ROWSTORE = """
    CREATE INDEX ix_fact_items_vendedor ON dw.fact_items (vendedor_key)
        INCLUDE (fecha_compra_key, precio, es_venta);
    CREATE INDEX ix_fact_items_fecha ON dw.fact_items (fecha_compra_key)
        INCLUDE (producto_key, vendedor_key, precio, es_venta);
    CREATE INDEX ix_fact_items_producto ON dw.fact_items (producto_key)
        INCLUDE (fecha_compra_key, precio, es_venta);
    CREATE INDEX ix_fact_pedidos_cliente ON dw.fact_pedidos (cliente_key)
        INCLUDE (fecha_compra_key, es_valido);
    CREATE INDEX ix_fact_pedidos_fecha ON dw.fact_pedidos (fecha_compra_key)
        INCLUDE (geografia_key, cliente_key, es_valido, es_entregado, a_tiempo, puntaje_resena);"""

_COLUMNSTORE = """
    CREATE NONCLUSTERED COLUMNSTORE INDEX ncci_fact_items ON dw.fact_items
        (pedido_id, item_nro, producto_key, vendedor_key, cliente_key, geografia_key,
         fecha_compra_key, precio, flete, es_venta);
    CREATE NONCLUSTERED COLUMNSTORE INDEX ncci_fact_pedidos ON dw.fact_pedidos
        (pedido_id, cliente_key, geografia_key, fecha_compra_key, fecha_entrega_key, fecha_estimada_key,
         es_valido, es_vendido, es_entregado, a_tiempo, dias_entrega, dias_vs_estimada, puntaje_resena, items);"""

# Solo los dos índices rowstore que sirven a búsquedas puntuales (un cliente,
# un vendedor); las agregaciones ya las resuelve el columnstore.
_PUNTUALES = """
    CREATE INDEX ix_fact_items_vendedor ON dw.fact_items (vendedor_key)
        INCLUDE (fecha_compra_key, precio, es_venta);
    CREATE INDEX ix_fact_pedidos_cliente ON dw.fact_pedidos (cliente_key)
        INCLUDE (fecha_compra_key, es_valido);"""

ESTRATEGIAS = {
    "A. Solo claves primarias": [_QUITAR_INDICES],
    "B. Índices rowstore en claves foráneas": [_QUITAR_INDICES, _ROWSTORE],
    "C. Columnstore en los hechos": [_QUITAR_INDICES, _COLUMNSTORE],
    "D. Rowstore + columnstore": [_QUITAR_INDICES, _ROWSTORE, _COLUMNSTORE],
    "E. Columnstore + 2 índices puntuales": [_QUITAR_INDICES, _PUNTUALES, _COLUMNSTORE],
}

_TAMANIO_INDICES = """
    SELECT CAST(SUM(s.used_page_count) * 8 / 1024.0 AS DECIMAL(9, 1))
    FROM sys.dm_db_partition_stats AS s
    JOIN sys.indexes AS i ON i.object_id = s.object_id AND i.index_id = s.index_id
    WHERE s.object_id IN (OBJECT_ID('dw.fact_items'), OBJECT_ID('dw.fact_pedidos')) AND i.index_id > 1"""

_LECTURAS = re.compile(r"Table '(\w+)'.*?logical reads (\d+).*?lob logical reads (\d+)")
_CPU = re.compile(r"CPU time = (\d+) ms")
_HECHOS = ("fact_items", "fact_pedidos")


def _accesos_a_hechos(plan_xml: str) -> set[str]:
    """Del plan real: cómo se lee cada tabla de hechos ('fact_items: Index Seek',
    'fact_items: Columnstore') y 'modo batch' si algún operador corre así."""
    raiz = ET.fromstring(plan_xml)
    ns = {"p": raiz.tag.split("}")[0].strip("{")}
    accesos = set()
    for relop in raiz.iter(f"{{{ns['p']}}}RelOp"):
        if relop.get("ActualExecutionMode", relop.get("EstimatedExecutionMode")) == "Batch":
            accesos.add("modo batch")
        acceso = relop.find("p:IndexScan", ns)
        if acceso is None:
            continue
        objeto = acceso.find("p:Object", ns)
        tabla = objeto.get("Table", "").strip("[]") if objeto is not None else ""
        if tabla in _HECHOS:
            tipo = "Columnstore" if acceso.get("Storage") == "ColumnStore" else relop.get("PhysicalOp")
            accesos.add(f"{tabla}: {tipo}")
    return accesos


def medir(conn: pyodbc.Connection, sql: str) -> dict:
    """Corre la consulta CORRIDAS veces; devuelve lecturas, CPU (mediana) y accesos del plan."""
    cpus, lecturas, accesos = [], 0, set()
    cursor = conn.cursor()
    for corrida in range(CORRIDAS):
        mensajes, planes = [], []
        cursor.execute("SET STATISTICS IO, TIME ON; SET STATISTICS XML ON;")
        cursor.execute(sql)
        while True:
            mensajes += [m[1] for m in cursor.messages or []]
            if cursor.description:
                filas = cursor.fetchall()
                if cursor.description[0][0].startswith("Microsoft SQL Server") and filas:
                    planes.append(filas[0][0])
            if not cursor.nextset():
                break
        cursor.execute("SET STATISTICS XML OFF; SET STATISTICS IO, TIME OFF;")
        texto = "\n".join(mensajes)
        if corrida == 0:
            continue
        lecturas = sum(int(n) + int(lob) for _, n, lob in _LECTURAS.findall(texto))
        # El último "CPU time" es el de la ejecución (los anteriores son de compilación)
        cpus.append(int(_CPU.findall(texto)[-1]) if _CPU.findall(texto) else 0)
        for plan in planes:
            accesos |= _accesos_a_hechos(plan)
    return {"lecturas": lecturas, "cpu_ms": statistics.median(cpus), "accesos": sorted(accesos)}


def aplicar(conn: pyodbc.Connection, lotes: list[str]) -> None:
    for lote in lotes:
        conn.execute(lote)


def main() -> None:
    conn = connect()
    resultados, costos = {}, {}
    for estrategia, lotes in ESTRATEGIAS.items():
        aplicar(conn, lotes[:1])            # quitar los índices de la estrategia anterior: no se cronometra
        inicio = time.perf_counter()
        aplicar(conn, lotes[1:])
        costos[estrategia] = (time.perf_counter() - inicio, conn.execute(_TAMANIO_INDICES).fetchone()[0] or 0)
        print(f"\n== {estrategia}  (crear índices: {costos[estrategia][0]:.1f} s, ocupan {costos[estrategia][1]} MB)")
        for nombre, sql in CONSULTAS.items():
            r = medir(conn, sql)
            resultados[(estrategia, nombre)] = r
            print(f"  {nombre:<34} {r['lecturas']:>8,} lecturas  {r['cpu_ms']:>6} ms CPU   {'; '.join(r['accesos'])}"
                  .replace(",", "."))

    print("\n== Tabla para docs/04_optimizacion_sql.md (lecturas lógicas / ms de CPU)\n")
    print("| Consulta | " + " | ".join(e.split(". ")[0] for e in ESTRATEGIAS) + " |")
    print("|---|" + "---:|" * len(ESTRATEGIAS))
    for nombre in CONSULTAS:
        celdas = [f"{resultados[(e, nombre)]['lecturas']:,} / {resultados[(e, nombre)]['cpu_ms']}".replace(",", ".")
                  for e in ESTRATEGIAS]
        print(f"| {nombre} | " + " | ".join(celdas) + " |")
    print("| **Espacio extra (MB)** | " + " | ".join(f"{costos[e][1]}".replace(".", ",") for e in ESTRATEGIAS) + " |")
    print("| **Tiempo de creación (s)** | " + " | ".join(f"{costos[e][0]:.1f}".replace(".", ",") for e in ESTRATEGIAS) + " |")

    run_script(DW_SQL_DIR / "90_indices.sql")
    print("\nBase restaurada con la estrategia elegida (sql/03_dw/90_indices.sql).")


if __name__ == "__main__":
    main()
