"""
Genera los bocetos (wireframes) de las 5 páginas del tablero como SVG.

    python docs/bocetos/generar_bocetos.py

Todas las páginas comparten la misma grilla, encabezado, barra de filtros y
paleta (ver README.md de esta carpeta). Para cambiar un boceto, se edita la
función de su página y se vuelve a correr.
"""

from pathlib import Path
from xml.sax.saxutils import escape

SALIDA = Path(__file__).resolve().parent

# Lienzo de Power BI: 16:9, 1280 x 720. Debajo se agrega una franja de leyenda.
ANCHO, ALTO, ALTO_TOTAL = 1280, 720, 800
MARGEN, GAP = 24, 16
Y_KPI, ALTO_KPI = 116, 100
Y_FILA2, Y_FILA3, ALTO_FILA = 232, 476, 228

FUENTE = "Segoe UI, Helvetica, Arial, sans-serif"
C = {
    "fondo": "#F3F4F6", "tarjeta": "#FFFFFF", "borde": "#D1D5DB",
    "texto": "#1F2937", "tenue": "#6B7280", "boceto": "#9CA3AF", "boceto_claro": "#E5E7EB",
    "acento": "#2563EB", "acento_claro": "#EFF6FF", "malo": "#DC2626", "bueno": "#16A34A",
    "encabezado": "#111827",
}
RAMPA = ["#DBEAFE", "#93C5FD", "#60A5FA", "#2563EB", "#1E3A8A"]  # secuencial de un solo tono

PAGINAS = ["Resumen", "Comercial", "Logística", "Cliente"]
MESES = ["E", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]

# Pedidos reales por mes (2017 y ene-ago 2018): dan la forma de las curvas.
PEDIDOS_2017 = [800, 1780, 2682, 2404, 3700, 3245, 4026, 4331, 4285, 4631, 7544, 5673]
PEDIDOS_2018 = [7269, 6728, 7211, 6939, 6873, 6167, 6292, 6512]


class Svg:
    def __init__(self) -> None:
        self.partes: list[str] = []

    def add(self, s: str) -> None:
        self.partes.append(s)

    def rect(self, x, y, w, h, fill, stroke="none", rx=0, sw=1, dash=None) -> None:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=12, fill=None, weight=400, anchor="start") -> None:
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FUENTE}" font-size="{size}" '
                 f'font-weight="{weight}" fill="{fill or C["texto"]}" text-anchor="{anchor}">{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, stroke, sw=1, dash=None) -> None:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def polyline(self, pts, stroke, sw=2, dash=None) -> None:
        d = f' stroke-dasharray="{dash}"' if dash else ""
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.add(f'<polyline points="{p}" fill="none" stroke="{stroke}" stroke-width="{sw}" '
                 f'stroke-linejoin="round" stroke-linecap="round"{d}/>')

    def guardar(self, nombre: str) -> None:
        cuerpo = "\n".join(self.partes)
        (SALIDA / nombre).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO_TOTAL}" '
            f'width="{ANCHO}" height="{ALTO_TOTAL}">\n{cuerpo}\n</svg>\n', encoding="utf-8")


# ---------------------------------------------------------------- estructura


def pagina(svg: Svg, titulo: str, activa: str | None, numero: int, responde: str) -> None:
    """Fondo, encabezado con navegación, y leyenda debajo del lienzo."""
    svg.rect(0, 0, ANCHO, ALTO_TOTAL, "#FFFFFF")
    svg.rect(0, 0, ANCHO, ALTO, C["fondo"])
    svg.rect(0, 0, ANCHO, 56, C["encabezado"])
    svg.text(MARGEN, 36, titulo, 20, "#FFFFFF", 600)
    x = ANCHO - MARGEN - len(PAGINAS) * 112
    for nombre in PAGINAS:
        if nombre == activa:
            svg.rect(x, 12, 104, 32, C["acento"], rx=6)
        svg.text(x + 52, 33, nombre, 13, "#FFFFFF" if nombre == activa else "#D1D5DB", 600 if nombre == activa else 400, "middle")
        x += 112

    # Leyenda (fuera del lienzo de Power BI)
    svg.line(0, ALTO, ANCHO, ALTO, C["borde"])
    svg.text(MARGEN, ALTO + 30, f"Boceto · Página {numero} de 5 · Responde: {responde}", 13, C["texto"], 600)
    svg.text(MARGEN, ALTO + 54, "Lienzo 1280 × 720 (16:9, tamaño estándar de Power BI). Valores: referencia del diccionario de KPIs o de ejemplo.", 12, C["tenue"])
    lx = 760
    etiqueta(svg, lx, ALTO + 18, "C1 · K01")
    svg.text(lx + 76, ALTO + 32, "pregunta · KPIs", 12, C["tenue"])
    svg.line(lx + 180, ALTO + 28, lx + 210, ALTO + 28, C["acento"], 2.5)
    svg.text(lx + 216, ALTO + 32, "actual", 12, C["tenue"])
    svg.line(lx + 270, ALTO + 28, lx + 300, ALTO + 28, C["boceto"], 2, "5 4")
    svg.text(lx + 306, ALTO + 32, "año ant. / referencia", 12, C["tenue"])
    svg.rect(lx + 180, ALTO + 44, 12, 12, C["malo"], rx=2)
    svg.text(lx + 198, ALTO + 54, "alerta (solo para lo que requiere acción)", 12, C["tenue"])


def filtros(svg: Svg, extra: list[tuple[str, int]] | None = None) -> None:
    """Barra de filtros: siempre en el mismo lugar y en el mismo orden."""
    x = MARGEN
    controles = extra or [("Período: Ene-2017 – Ago-2018", 236), ("Región", 150), ("Estado", 130), ("Categoría", 170)]
    for texto, w in controles:
        svg.rect(x, 68, w, 36, C["tarjeta"], C["borde"], 6)
        svg.text(x + 12, 91, texto, 12, C["texto"])
        svg.text(x + w - 14, 91, "▾", 12, C["tenue"], anchor="middle")
        x += w + 12
    svg.rect(ANCHO - MARGEN - 132, 68, 132, 36, C["tarjeta"], C["acento"], 6)
    svg.text(ANCHO - MARGEN - 66, 91, "⟲ Limpiar filtros", 12, C["acento"], 600, "middle")


def etiqueta(svg: Svg, x, y, texto) -> float:
    w = len(texto) * 6.4 + 18
    svg.rect(x, y, w, 20, C["acento_claro"], C["acento"], 10)
    svg.text(x + w / 2, y + 14, texto, 11, C["acento"], 600, "middle")
    return w


def tarjeta(svg: Svg, x, y, w, h, titulo, tag=None, nota=None):
    """Contenedor de un visual. Devuelve el área de dibujo (x, y, w, h)."""
    svg.rect(x, y, w, h, C["tarjeta"], C["borde"], 8)
    svg.text(x + 16, y + 26, titulo, 13, C["texto"], 600)
    if tag:
        tw = len(tag) * 6.4 + 18
        etiqueta(svg, x + w - tw - 12, y + 10, tag)
    if nota:
        svg.text(x + 16, y + h - 12, nota, 11, C["tenue"])
    return x + 16, y + 44, w - 32, h - (78 if nota else 60)


def fila_kpis(svg: Svg, kpis: list[tuple[str, str, str, str]]) -> None:
    """kpis: (etiqueta, valor, variación, código). La variación empieza con ▲ o ▼."""
    n = len(kpis)
    w = (ANCHO - 2 * MARGEN - (n - 1) * GAP) / n
    for i, (nombre, valor, delta, codigo) in enumerate(kpis):
        x = MARGEN + i * (w + GAP)
        svg.rect(x, Y_KPI, w, ALTO_KPI, C["tarjeta"], C["borde"], 8)
        svg.text(x + 16, Y_KPI + 24, nombre, 12, C["tenue"])
        svg.text(x + w - 12, Y_KPI + 24, codigo, 10, C["acento"], 600, "end")
        svg.text(x + 16, Y_KPI + 62, valor, 28, C["texto"], 600)
        color = C["malo"] if delta.startswith("!") else C["tenue"]
        svg.text(x + 16, Y_KPI + 86, delta.lstrip("!"), 12, color)
        # mini tendencia
        pts = [(x + w - 76 + j * 10, Y_KPI + 84 - v * 22) for j, v in enumerate([.3, .4, .35, .55, .5, .7, .65, .8])]
        svg.polyline(pts, C["boceto"], 1.5)


# ---------------------------------------------------------------- visuales


def ejes(svg, px, py, pw, ph, etiquetas_x=None):
    for k in range(4):
        yy = py + ph * k / 3
        svg.line(px, yy, px + pw, yy, C["boceto_claro"])
    if etiquetas_x:
        paso = pw / (len(etiquetas_x) - 1) if len(etiquetas_x) > 1 else 0
        for i, e in enumerate(etiquetas_x):
            svg.text(px + i * paso, py + ph + 16, e, 10, C["tenue"], anchor="middle")


def curva(px, py, pw, ph, valores, n_total, maximo):
    paso = pw / (n_total - 1)
    return [(px + i * paso, py + ph - v / maximo * ph * 0.92) for i, v in enumerate(valores)]


def barras_h(svg, px, py, pw, ph, etiquetas, valores, resaltar=0, valores_txt=None, color=None):
    n = len(etiquetas)
    alto = min(22, ph / n - 6)
    ancho_etq = 112
    for i, (e, v) in enumerate(zip(etiquetas, valores)):
        yy = py + i * (ph / n)
        svg.text(px + ancho_etq - 8, yy + alto / 2 + 4, e, 11, C["texto"], anchor="end")
        fill = color or (C["acento"] if i < resaltar else C["boceto"])
        largo = (pw - ancho_etq - 60) * v
        svg.rect(px + ancho_etq, yy, largo, alto, fill, rx=3)
        if valores_txt:
            svg.text(px + ancho_etq + largo + 6, yy + alto / 2 + 4, valores_txt[i], 11, C["tenue"])


def columnas(svg, px, py, pw, ph, etiquetas, valores, colores=None, valores_txt=None):
    n = len(etiquetas)
    ancho = pw / n * 0.6
    for i, (e, v) in enumerate(zip(etiquetas, valores)):
        cx = px + (i + 0.5) * pw / n
        h = (ph - 44) * v  # deja lugar para la etiqueta de valor arriba de la barra más alta
        svg.rect(cx - ancho / 2, py + ph - 20 - h, ancho, h, (colores or [C["acento"]] * n)[i], rx=3)
        svg.text(cx, py + ph - 4, e, 11, C["tenue"], anchor="middle")
        if valores_txt:
            svg.text(cx, py + ph - 26 - h, valores_txt[i], 12, C["texto"], 600, "middle")


def mapa_mosaico(svg, px, py, pw, ph, intensidad):
    """Mapa de mosaicos de Brasil: un cuadrado por estado, todos del mismo tamaño."""
    grilla = {
        "RR": (2, 0), "AP": (4, 0),
        "AM": (1, 1), "PA": (3, 1), "MA": (4, 1), "CE": (5, 1), "RN": (6, 1),
        "AC": (0, 2), "RO": (1, 2), "MT": (2, 2), "TO": (3, 2), "PI": (4, 2), "PE": (5, 2), "PB": (6, 2),
        "MS": (1, 3), "GO": (2, 3), "DF": (3, 3), "BA": (4, 3), "SE": (5, 3), "AL": (6, 3),
        "PR": (1, 4), "SP": (2, 4), "MG": (3, 4), "ES": (4, 4),
        "SC": (1, 5), "RJ": (3, 5),
        "RS": (1, 6),
    }
    lado = min((pw - 90) / 7, ph / 7) - 3
    for uf, (col, fila) in grilla.items():
        nivel = intensidad.get(uf, 0)
        x, y = px + col * (lado + 3), py + fila * (lado + 3)
        svg.rect(x, y, lado, lado, RAMPA[nivel], rx=3)
        svg.text(x + lado / 2, y + lado / 2 + 4, uf, 10, "#FFFFFF" if nivel >= 3 else C["texto"], 600, "middle")
    lx = px + 7 * (lado + 3) + 12
    svg.text(lx, py + 12, "Ventas", 11, C["tenue"])
    for i, color in enumerate(RAMPA):
        svg.rect(lx, py + 20 + i * 18, 14, 14, color, rx=2)
    svg.text(lx + 20, py + 31, "menos", 10, C["tenue"])
    svg.text(lx + 20, py + 20 + 4 * 18 + 11, "más", 10, C["tenue"])


INTENSIDAD_VENTAS = {"SP": 4, "RJ": 3, "MG": 3, "RS": 2, "PR": 2, "SC": 2, "BA": 2, "DF": 1, "GO": 1, "ES": 1, "PE": 1, "CE": 1}


def mapa_calor(svg, px, py, pw, ph, filas, cols, valores, titulo_filas, titulo_cols, formato="{:.0f}"):
    ancho_etq = 70
    cw = (pw - ancho_etq) / len(cols)
    ch = (ph - 34) / len(filas)
    svg.text(px + ancho_etq + (pw - ancho_etq) / 2, py + 10, titulo_cols, 11, C["tenue"], anchor="middle")
    for j, c in enumerate(cols):
        svg.text(px + ancho_etq + (j + 0.5) * cw, py + 28, c, 10, C["tenue"], anchor="middle")
    for i, f in enumerate(filas):
        y = py + 34 + i * ch
        svg.text(px + ancho_etq - 8, y + ch / 2 + 4, f, 10, C["texto"], anchor="end")
        for j in range(len(cols)):
            v = valores[i][j]
            if v is None:
                continue
            nivel = min(4, int(v * 5))
            svg.rect(px + ancho_etq + j * cw + 1, y + 1, cw - 2, ch - 2, RAMPA[nivel], rx=2)
            if ch >= 16 and cw >= 34:
                svg.text(px + ancho_etq + (j + 0.5) * cw, y + ch / 2 + 4, formato.format(v * 100) if "%" in formato else formato.format(v * 20),
                         10, "#FFFFFF" if nivel >= 3 else C["texto"], anchor="middle")
    svg.text(px, py + 10, titulo_filas, 11, C["tenue"])


def tabla(svg, px, py, pw, ph, encabezados, filas, anchos, barras_col=None):
    alto = min(26, ph / (len(filas) + 1))
    x = px
    for e, a in zip(encabezados, anchos):
        svg.text(x + (a * pw if e != encabezados[0] else 0) - (8 if e != encabezados[0] else 0), py + 16, e, 11, C["tenue"], 600,
                 "end" if e != encabezados[0] else "start")
        x += a * pw
    svg.line(px, py + alto, px + pw, py + alto, C["borde"])
    for i, fila in enumerate(filas):
        y = py + alto * (i + 1)
        x = px
        for j, (v, a) in enumerate(zip(fila, anchos)):
            if barras_col is not None and j == barras_col:
                largo = (a * pw - 60) * float(v.split("|")[1])
                svg.rect(x + 4, y + 7, largo, alto - 14, C["acento_claro"], C["acento"], 2, 0.5)
                svg.text(x + a * pw - 8, y + alto / 2 + 4, v.split("|")[0], 11, C["texto"], anchor="end")
            else:
                color = C["malo"] if v.startswith("▼") else C["texto"]
                svg.text(x + (0 if j == 0 else a * pw - 8), y + alto / 2 + 4, v, 11, color, anchor="start" if j == 0 else "end")
            x += a * pw
        svg.line(px, y + alto, px + pw, y + alto, C["boceto_claro"])


# ---------------------------------------------------------------- páginas


def resumen() -> None:
    s = Svg()
    pagina(s, "Olist · Resumen ejecutivo", "Resumen", 1, "C1, L1, X1 (una cifra por área)")
    filtros(s)
    fila_kpis(s, [
        ("Ventas", "R$ 13,4 M", "▲ +138% vs año ant.", "K01"),
        ("Pedidos", "97.905", "▲ vs año ant.", "K02"),
        ("Ticket promedio", "R$ 137", "▲ vs año ant.", "K03"),
        ("% entregas a tiempo", "93,2%", "▼ vs año ant.", "K17"),
        ("Puntaje de reseña", "4,12", "▲ vs año ant.", "K22"),
    ])
    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA2, 744, 472, "Ventas por mes: 2018 contra 2017", "C1 · K01 K07",
                             "Nov-2017: pico de Black Friday. 2018 se compara solo hasta agosto.")
    ejes(s, px, py, pw, ph - 20, MESES)
    mx = max(PEDIDOS_2017 + PEDIDOS_2018)
    s.polyline(curva(px, py, pw, ph - 20, PEDIDOS_2017, 12, mx), C["boceto"], 2, "6 5")
    s.polyline(curva(px, py, pw, ph - 20, PEDIDOS_2018, 12, mx), C["acento"], 3)
    ult = curva(px, py, pw, ph - 20, PEDIDOS_2018, 12, mx)[-1]
    s.text(ult[0] + 8, ult[1] + 4, "2018", 12, C["acento"], 600)
    s.text(px + pw - 4, curva(px, py, pw, ph - 20, PEDIDOS_2017, 12, mx)[-1][1] - 8, "2017", 12, C["tenue"], 600, "end")

    px, py, pw, ph = tarjeta(s, 784, Y_FILA2, 472, ALTO_FILA, "Top 5 categorías por ventas", "C2 · K01 K11")
    barras_h(s, px, py, pw, ph, ["Salud y belleza", "Relojes y regalos", "Cama, mesa y baño", "Deportes", "Informática"],
             [1, .955, .83, .78, .72], resaltar=1, valores_txt=["9,3%", "8,9%", "7,7%", "7,3%", "6,7%"])
    px, py, pw, ph = tarjeta(s, 784, Y_FILA3, 472, ALTO_FILA, "Ventas por estado del cliente", "C3 · K01")
    mapa_mosaico(s, px, py, pw, ph, INTENSIDAD_VENTAS)
    s.guardar("01_resumen.svg")


def comercial() -> None:
    s = Svg()
    pagina(s, "Olist · Comercial", "Comercial", 2, "C1, C2, C3, C4, C5")
    filtros(s)
    fila_kpis(s, [
        ("Ventas", "R$ 13,4 M", "▲ +138% vs año ant.", "K01"),
        ("Pedidos", "97.905", "▲ vs año ant.", "K02"),
        ("Ticket promedio", "R$ 137", "▲ vs año ant.", "K03"),
        ("Ítems por pedido", "1,14", "▲ vs año ant.", "C5 · K05"),
        ("Vendedores activos", "3.029", "▲ vs año ant.", "K12"),
    ])
    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA2, 600, ALTO_FILA, "Ventas mensuales y media móvil de 3 meses", "C1 · K01 K10")
    serie = PEDIDOS_2017 + PEDIDOS_2018
    ejes(s, px, py, pw, ph - 18, ["Ene-17", "", "", "", "", "Jun-17", "", "", "", "", "Nov-17", "", "", "", "", "Abr-18", "", "", "", "Ago-18"])
    n = len(serie)
    ancho = pw / n * 0.62
    for i, v in enumerate(serie):
        h = (ph - 18) * v / max(serie) * 0.92
        s.rect(px + i * pw / (n - 1) - ancho / 2, py + ph - 18 - h, ancho, h, C["acento_claro"], C["acento"], 2, 0.6)
    movil = [sum(serie[max(0, i - 2):i + 1]) / len(serie[max(0, i - 2):i + 1]) for i in range(n)]
    s.polyline(curva(px, py, pw, ph - 18, movil, n, max(serie)), C["acento"], 2.5)

    px, py, pw, ph = tarjeta(s, 640, Y_FILA2, 616, ALTO_FILA, "Categorías: ventas, participación y variación", "C2 · K01 K11 K08")
    tabla(s, px, py, pw, ph, ["Categoría", "Ventas", "Participación", "Var. interanual"], [
        ["Salud y belleza", "R$ 1,25 M", "9,3%|1", "▲ +211%"],
        ["Relojes y regalos", "R$ 1,19 M", "8,9%|.955", "▲ +243%"],
        ["Cama, mesa y baño", "R$ 1,04 M", "7,7%|.83", "▲ +107%"],
        ["Deportes", "R$ 0,98 M", "7,3%|.78", "▲ +136%"],
        ["Informática", "R$ 0,90 M", "6,7%|.72", "▲ +129%"],
        ["…", "", "|0", ""],
    ], [.34, .2, .26, .2], barras_col=2)

    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA3, 420, ALTO_FILA, "Ventas por estado", "C3 · K01 K03",
                             "Tooltip: ventas, pedidos y ticket promedio del estado.")
    mapa_mosaico(s, px, py, pw, ph + 14, INTENSIDAD_VENTAS)

    px, py, pw, ph = tarjeta(s, 460, Y_FILA3, 796, ALTO_FILA, "Top N vendedores por ventas", "C4 · K01 K11",
                             "Clic derecho en un vendedor → Obtener detalles → página Detalle de vendedor.")
    # Selector de N (parámetro numérico de Power BI)
    s.text(px + pw - 170, py + 12, "Top N", 11, C["tenue"], 600)
    s.line(px + pw - 170, py + 28, px + pw - 30, py + 28, C["borde"], 3)
    s.add(f'<circle cx="{px + pw - 130:.1f}" cy="{py + 28:.1f}" r="7" fill="{C["acento"]}"/>')
    s.text(px + pw - 4, py + 32, "10", 11, C["acento"], 600, "end")
    barras_h(s, px, py + 10, pw - 180, ph - 10, [f"Vendedor {i}" for i in range(1, 7)],
             [1, .86, .7, .62, .55, .5], color=C["acento"],
             valores_txt=["2,0%", "1,7%", "1,4%", "1,2%", "1,1%", "1,0%"])
    s.text(px + pw - 170, py + 64, "Cada barra muestra", 11, C["tenue"])
    s.text(px + pw - 170, py + 80, "la participación sobre", 11, C["tenue"])
    s.text(px + pw - 170, py + 96, "el total visible (K11).", 11, C["tenue"])
    s.guardar("02_comercial.svg")


def logistica() -> None:
    s = Svg()
    pagina(s, "Olist · Logística", "Logística", 3, "L1, L2, L3, L4, L5")
    filtros(s, [("Período: Ene-2017 – Ago-2018", 236), ("Región", 150), ("Estado", 130), ("Estado del vendedor", 190)])
    fila_kpis(s, [
        ("% entregas a tiempo", "93,2%", "▼ vs año ant.", "L1 · K17"),
        ("Días de entrega", "12,5", "mediana: 10,2 días", "L2 · K18"),
        ("Días de demora", "10,6", "solo pedidos tardíos", "L3 · K19"),
        ("Pedidos con demora", "6.531", "!▲ vs año ant.", "L3 · K20"),
        ("% flete s/ ventas", "16,6%", "▼ vs año ant.", "L4 · K15"),
        ("Tasa de cancelación", "1,19%", "1.182 pedidos", "L5 · K21"),
    ])
    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA2, 600, ALTO_FILA, "% de entregas a tiempo por mes", "L1 · K17")
    a_tiempo = [.971, .97, .954, .934, .97, .97, .972, .971, .956, .958, .876, .925, .943, .859, .81, .955, .934, .988, .966, .938]
    ejes(s, px, py, pw, ph - 18, ["Ene-17", "", "", "", "", "Jun-17", "", "", "", "", "Nov-17", "", "", "", "", "Abr-18", "", "", "", "Ago-18"])
    escala = lambda v: py + (ph - 18) * (1 - (v - .75) / .25)  # eje de 75% a 100%
    pts = [(px + i * pw / 19, escala(v)) for i, v in enumerate(a_tiempo)]
    s.line(px, escala(.932), px + pw, escala(.932), C["boceto"], 1.5, "6 5")
    s.text(px + 4, escala(.932) + 14, "promedio 93,2%", 10, C["tenue"])
    s.polyline(pts, C["acento"], 2.5)
    for i in (10, 13, 14):  # meses bajo el promedio que piden explicación
        s.add(f'<circle cx="{pts[i][0]:.1f}" cy="{pts[i][1]:.1f}" r="4.5" fill="{C["malo"]}"/>')
    s.text(pts[14][0] + 10, pts[14][1] + 4, "Feb–Mar 2018", 11, C["malo"], 600)

    px, py, pw, ph = tarjeta(s, 640, Y_FILA2, 616, ALTO_FILA, "Días promedio de entrega por estado del cliente", "L2 · K18")
    barras_h(s, px, py, pw, ph, ["RR", "AP", "AM", "AL", "PA", "…", "SP"],
             [1, .91, .88, .82, .80, 0, .29], resaltar=0, color=None,
             valores_txt=["29,9", "27,2", "26,4", "24,5", "23,8", "", "8,7"])
    s.text(px + pw - 4, py + ph, "Ordenado de mayor a menor. Eje en días.", 10, C["tenue"], anchor="end")

    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA3, 744, ALTO_FILA, "Rutas: días de demora promedio (vendedor → cliente)", "L3 · K19 K20",
                             "Celdas vacías: rutas con menos de 30 pedidos (sin dato confiable).")
    cols = ["SP", "RJ", "MG", "RS", "PR", "BA", "PE", "CE", "PA", "AM"]
    filas = ["SP", "PR", "MG", "RJ", "SC"]
    vals = [[.15, .35, .2, .3, .2, .5, .6, .65, .75, .85],
            [.25, .4, .3, .2, .1, .55, None, .7, None, None],
            [.3, .35, .1, .45, .35, .45, None, None, None, None],
            [.35, .2, .3, None, .4, .6, None, None, None, None],
            [.3, .45, .4, .2, .15, None, None, None, None, None]]
    mapa_calor(s, px, py, pw, ph, filas, cols, vals, "Vendedor", "Estado del cliente", "{:.0f}")

    px, py, pw, ph = tarjeta(s, 784, Y_FILA3, 472, ALTO_FILA, "% de flete sobre ventas por región", "L4 · K15")
    columnas(s, px, py, pw, ph, ["Sudeste", "Sur", "C.-Oeste", "Nordeste", "Norte"], [.67, .78, .78, .96, 1],
             [C["boceto"], C["boceto"], C["boceto"], C["acento"], C["acento"]], ["15,2%", "17,6%", "17,6%", "21,7%", "22,7%"])
    s.guardar("03_logistica.svg")


def cliente() -> None:
    s = Svg()
    pagina(s, "Olist · Experiencia de cliente", "Cliente", 4, "X1, X2, X3, X4, X5")
    filtros(s)
    fila_kpis(s, [
        ("Puntaje de reseña", "4,12", "▲ vs año ant.", "X1 · K22"),
        ("% reseñas negativas", "13,9%", "!▲ vs año ant.", "X1 · K23"),
        ("% reseñas positivas", "77,9%", "▼ vs año ant.", "X1 · K24"),
        ("Tasa de recompra", "3,0%", "clientes con 2+ pedidos", "X4 · K25"),
        ("Brecha por demora", "−2,0", "puntos: tarde vs a tiempo", "X2 · K26"),
    ])
    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA2, 744, ALTO_FILA, "Distribución de puntajes por mes", "X1 · K22 K23 K24")
    n = 20
    colores = ["#B91C1C", "#F87171", C["boceto_claro"], "#93C5FD", C["acento"]]  # 1 a 5: divergente
    w = pw / n * 0.7
    for i in range(n):
        malo = .13 + (.08 if i in (13, 14) else 0)
        partes = [malo * .75, malo * .25, .09, .19, 1 - malo - .28]
        y = py + ph - 18
        for p, c in zip(partes, colores):
            h = (ph - 18) * p
            s.rect(px + i * pw / n + (pw / n - w) / 2, y - h, w, h, c)
            y -= h
    for i, e in enumerate(["Ene-17", "Jun-17", "Nov-17", "Abr-18", "Ago-18"]):
        s.text(px + [0, 5, 10, 15, 19][i] * pw / n + pw / n / 2, py + ph - 2, e, 10, C["tenue"], anchor="middle")
    lx = px + pw - 390  # a la izquierda de la etiqueta de pregunta
    for j, (c, e) in enumerate(zip(colores, ["1", "2", "3", "4", "5 ★"])):
        s.rect(lx + j * 50, py - 30, 12, 12, c, rx=2)
        s.text(lx + j * 50 + 16, py - 20, e, 10, C["tenue"])

    px, py, pw, ph = tarjeta(s, 784, Y_FILA2, 472, ALTO_FILA, "Puntaje promedio: a tiempo contra tarde", "X2 · K22 K26",
                             "El hallazgo central: la demora explica la mala reseña.")
    columnas(s, px + 40, py, pw - 80, ph, ["Entregado a tiempo", "Entregado tarde"], [4.29 / 5, 2.27 / 5],
             [C["acento"], C["malo"]], ["4,29 ★", "2,27 ★"])

    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA3, 744, ALTO_FILA, "Cohortes: % de clientes que vuelve a comprar", "X5 · K27",
                             "Fila: mes de la primera compra. Columna: meses después. Escala hasta 1% (la recompra es baja).")
    meses = ["Ene-17", "Feb-17", "Mar-17", "Abr-17", "May-17", "…"]
    vals = [[.8 - .1 * j if j < 6 - i else None for j in range(10)] for i in range(6)]
    for i in range(6):
        for j in range(10):
            if vals[i][j] is not None:
                vals[i][j] = max(.05, vals[i][j] - .05 * i)
    vals[5] = [None] * 10
    mapa_calor(s, px, py, pw, ph, meses, [f"+{k}" for k in range(1, 11)], vals, "Cohorte", "Meses después de la primera compra", "{:.1f}%")

    px, py, pw, ph = tarjeta(s, 784, Y_FILA3, 472, ALTO_FILA, "Categorías con más reseñas negativas", "X3 · K23",
                             "Solo categorías con 200 reseñas o más.")
    barras_h(s, px, py, pw, ph, ["Muebles oficina", "Audio", "Confort hogar", "Telefonía fija", "Construcción"],
             [1, .97, .86, .80, .79], resaltar=0, color=C["malo"],
             valores_txt=["22,4%", "21,8%", "19,2%", "18,0%", "17,7%"])
    s.guardar("04_cliente.svg")


def detalle_vendedor() -> None:
    s = Svg()
    pagina(s, "Olist · Detalle de vendedor", None, 5, "C4 y X3 para un vendedor puntual (página de obtención de detalles)")
    filtros(s, [("← Volver", 100), ("Vendedor: 4a3c…f21 · SP", 230), ("Período: Ene-2017 – Ago-2018", 236)])
    fila_kpis(s, [
        ("Ventas", "R$ 229 mil", "1,7% del marketplace", "K01 K11"),
        ("Pedidos", "1.132", "ranking: 3 de 3.029", "K02"),
        ("Ticket promedio", "R$ 202", "marketplace: R$ 137", "K03"),
        ("% entregas a tiempo", "88,4%", "!marketplace: 93,2%", "K17"),
        ("Puntaje de reseña", "3,85", "!marketplace: 4,12", "K22"),
    ])
    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA2, 744, ALTO_FILA, "Ventas mensuales del vendedor", "C4 · K01")
    serie = [.1, .15, .2, .22, .3, .35, .33, .4, .45, .5, .8, .6, .7, .75, .72, .68, .7, .66, .64, .7]
    ejes(s, px, py, pw, ph - 18, ["Ene-17", "", "", "", "", "Jun-17", "", "", "", "", "Nov-17", "", "", "", "", "Abr-18", "", "", "", "Ago-18"])
    s.polyline(curva(px, py, pw, ph - 18, serie, 20, 1), C["acento"], 2.5)

    px, py, pw, ph = tarjeta(s, 784, Y_FILA2, 472, ALTO_FILA, "Puntajes recibidos", "X3 · K22 K23")
    barras_h(s, px, py, pw, ph, ["5 ★", "4 ★", "3 ★", "2 ★", "1 ★"], [1, .35, .2, .08, .3], resaltar=0,
             valores_txt=["55%", "19%", "11%", "4%", "16%"])
    s.rect(px + 112, py + 4 * ph / 5, (pw - 172) * .3, min(22, ph / 5 - 6), C["malo"], rx=3)

    px, py, pw, ph = tarjeta(s, MARGEN, Y_FILA3, 600, ALTO_FILA, "Ventas por categoría", "C4 · K01 K11")
    barras_h(s, px, py, pw, ph, ["Relojes y regalos", "Accesorios", "Perfumería", "Otras"], [1, .45, .25, .12], color=C["acento"],
             valores_txt=["62%", "24%", "9%", "5%"])

    px, py, pw, ph = tarjeta(s, 640, Y_FILA3, 616, ALTO_FILA, "Entregas por estado del cliente", "L1 L2 · K17 K18",
                             "Ordenado por pedidos. En rojo, estados con % a tiempo bajo el promedio del marketplace.")
    tabla(s, px, py, pw, ph, ["Estado", "Pedidos", "% a tiempo", "Días de entrega"], [
        ["SP", "468", "95,1%", "7,9"],
        ["RJ", "152", "▼ 84,2%", "14,6"],
        ["MG", "131", "92,4%", "11,8"],
        ["BA", "58", "▼ 79,3%", "19,2"],
        ["…", "", "", ""],
    ], [.25, .2, .27, .28])
    s.guardar("05_detalle_vendedor.svg")


if __name__ == "__main__":
    for generar in (resumen, comercial, logistica, cliente, detalle_vendedor):
        generar()
    print("Bocetos generados en", SALIDA)
