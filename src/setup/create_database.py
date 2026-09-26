"""
Crea la base OlistDW (o la configurada) y sus esquemas en SQL Server.

    python -m src.setup.create_database
"""

from src.config import load_config
from src.db import run_script
from src.paths import SETUP_SQL_DIR


def main() -> None:
    config = load_config()
    print(f"Servidor: {config.server}  |  Base: {config.database}")
    for script in sorted(SETUP_SQL_DIR.glob("*.sql")):
        # Conecta a master: la base todavía puede no existir.
        lotes = run_script(script, database="master", config=config)
        print(f"  {script.name}: {lotes} lotes ejecutados")
    print("Listo.")


if __name__ == "__main__":
    main()
