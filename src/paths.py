"""
Rutas del proyecto, resueltas desde la ubicación de este archivo.

Todos los scripts importan de acá en lugar de construir rutas relativas al
directorio de trabajo, así el resultado no depende de desde dónde se corran.

    ROOT/
    ├── data/raw/*.csv          (9 CSV de Olist, NO versionados: ver data/README.md)
    ├── sql/00_setup/           (creación de la base y los esquemas)
    ├── sql/01_raw ... 04_views (una carpeta por capa)
    ├── powerbi/                (proyecto .pbip)
    └── docs/                   (requerimientos, KPIs, decisiones)
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SEEDS_DIR = DATA_DIR / "seeds"      # tablas propias del proyecto, versionadas
SQL_DIR = ROOT / "sql"
SETUP_SQL_DIR = SQL_DIR / "00_setup"
RAW_SQL_DIR = SQL_DIR / "01_raw"
STG_SQL_DIR = SQL_DIR / "02_staging"
DW_SQL_DIR = SQL_DIR / "03_dw"
RPT_SQL_DIR = SQL_DIR / "04_views"
DOCS_DIR = ROOT / "docs"
POWERBI_DIR = ROOT / "powerbi"

# Los 9 archivos que trae el zip de Kaggle, con la cantidad de filas de datos
# (sin encabezado) que tiene cada uno. src/setup/extract_data.py verifica que
# estén todos y completos; si Kaggle publica otra versión, esto lo detecta.
RAW_FILES = {
    "olist_customers_dataset.csv": 99_441,
    "olist_geolocation_dataset.csv": 1_000_163,
    "olist_order_items_dataset.csv": 112_650,
    "olist_order_payments_dataset.csv": 103_886,
    "olist_order_reviews_dataset.csv": 99_224,
    "olist_orders_dataset.csv": 99_441,
    "olist_products_dataset.csv": 32_951,
    "olist_sellers_dataset.csv": 3_095,
    "product_category_name_translation.csv": 71,
}


def ensure_dir(path: Path) -> Path:
    """Crea el directorio (y sus padres) si no existe, y lo devuelve."""
    path.mkdir(parents=True, exist_ok=True)
    return path
