"""
Extrae los CSV de Olist desde el zip de Kaggle a data/raw/ y verifica que
estén los 9 archivos con la cantidad de filas esperada.

    python -m src.setup.extract_data "ruta/al/archivo.zip"
    python -m src.setup.extract_data            (solo verifica data/raw/)

Dataset: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
"""

import csv
import sys
import zipfile
from pathlib import Path

from src.paths import RAW_DIR, RAW_FILES, ensure_dir


def extract(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        nombres = set(zf.namelist())
        faltan = sorted(set(RAW_FILES) - nombres)
        if faltan:
            raise SystemExit(f"El zip no tiene estos archivos: {', '.join(faltan)}")
        ensure_dir(RAW_DIR)
        for nombre in RAW_FILES:
            zf.extract(nombre, RAW_DIR)
    print(f"Extraídos {len(RAW_FILES)} archivos en {RAW_DIR}")


def count_rows(path: Path) -> int:
    """
    Filas de datos sin contar el encabezado. Cuenta registros con el módulo csv
    y no saltos de línea, porque las reseñas tienen comentarios con saltos de
    línea dentro de un mismo campo.
    """
    with path.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def verify() -> bool:
    ok = True
    for nombre, esperadas in RAW_FILES.items():
        path = RAW_DIR / nombre
        if not path.exists():
            print(f"  [FALTA] {nombre}")
            ok = False
            continue
        filas = count_rows(path)
        estado = "OK" if filas == esperadas else "DISTINTO"
        ok &= filas == esperadas
        print(f"  [{estado:>8}] {nombre:<42} {filas:>10,} filas (esperadas {esperadas:,})")
    return ok


def main() -> None:
    if len(sys.argv) > 1:
        extract(Path(sys.argv[1]))
    if not verify():
        raise SystemExit("Los archivos de data/raw/ no coinciden con lo esperado.")
    print("Los 9 archivos están completos.")


if __name__ == "__main__":
    main()
