"""
Control del Best Practice Analyzer en el CI (Fase 11).

Tabular Editor 2 revisa el modelo (los archivos TMDL) contra las reglas de
Microsoft y deja el resultado en un archivo TRX. Este módulo lo compara con las
excepciones aceptadas en powerbi/bpa_excepciones.json, cada una con su motivo
(docs/09_rendimiento.md):

  - un aviso que no está en las excepciones hace fallar el CI: es un problema
    nuevo, o una excepción que hay que justificar;
  - una excepción que ya no aparece también: la lista tiene que reflejar el
    modelo actual, no avisos que se corrigieron.

Uso: python -m src.bpa resultado.trx
"""

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from src.paths import POWERBI_DIR

EXCEPCIONES = POWERBI_DIR / "bpa_excepciones.json"
_NS = {"t": "http://microsoft.com/schemas/VisualStudio/TeamTest/2010"}
# "  'Tabla'[Columna] (Column)" o "  'Tabla' (Table (Import))": el tipo puede
# tener un paréntesis adentro, y el nombre también ('Gerentes'[Estado (sigla)]).
_OBJETO = re.compile(r"^\s+(.+) \(((?:[^()]|\([^()]*\))+)\)$")


def leer_trx(ruta: Path) -> set[tuple[str, str]]:
    """Avisos del TRX como pares (regla, objeto)."""
    avisos = set()
    for resultado in ET.parse(ruta).getroot().iterfind(".//t:UnitTestResult", _NS):
        if resultado.get("outcome") != "Failed":
            continue
        detalle = resultado.findtext(".//t:StackTrace", default="", namespaces=_NS)
        for linea in detalle.splitlines()[1:]:   # la primera es "Objects in violation:"
            m = _OBJETO.match(linea)
            if m:
                avisos.add((resultado.get("testName"), m.group(1)))
    return avisos


def leer_excepciones(ruta: Path = EXCEPCIONES) -> set[tuple[str, str]]:
    excepciones = set()
    for e in json.loads(ruta.read_text(encoding="utf-8")):
        if not e.get("motivo"):
            raise ValueError(f"La excepción de '{e['regla']}' no tiene motivo")
        excepciones |= {(e["regla"], objeto) for objeto in e["objetos"]}
    return excepciones


def comparar(avisos: set, excepciones: set) -> tuple[set, set]:
    """(avisos nuevos, excepciones que ya no aparecen)."""
    return avisos - excepciones, excepciones - avisos


def main(argv: list[str]) -> int:
    avisos = leer_trx(Path(argv[0]))
    nuevos, sobrantes = comparar(avisos, leer_excepciones())
    for regla, objeto in sorted(nuevos):
        print(f"NUEVO      {regla}: {objeto}")
    for regla, objeto in sorted(sobrantes):
        print(f"YA NO PASA {regla}: {objeto} (sacarlo de {EXCEPCIONES.name})")
    print(f"{len(avisos)} avisos, todos con excepción justificada." if not (nuevos or sobrantes)
          else f"{len(nuevos)} avisos nuevos y {len(sobrantes)} excepciones de más.")
    return 1 if nuevos or sobrantes else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
