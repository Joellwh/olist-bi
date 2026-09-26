"""
Configuración de la conexión a SQL Server.

Los valores por defecto apuntan a una instalación local de SQL Server Express
con autenticación de Windows. Para otro servidor o para otra base (por ejemplo
OlistDW_dev / OlistDW_prod en la fase de despliegue) no se toca el código:
se definen variables de entorno.

    OLIST_SQL_SERVER   servidor\\instancia     (por defecto: .\\SQLEXPRESS)
    OLIST_SQL_DATABASE nombre de la base      (por defecto: OlistDW)
    OLIST_SQL_DRIVER   driver ODBC            (por defecto: ODBC Driver 18 for SQL Server)
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SqlConfig:
    server: str
    database: str
    driver: str

    def odbc_string(self, database: str | None = None) -> str:
        """
        Cadena de conexión ODBC con autenticación de Windows.

        TrustServerCertificate=yes hace falta porque el Driver 18 cifra la
        conexión por defecto y una instancia local no tiene un certificado
        firmado por una entidad reconocida. En un servidor real se usaría un
        certificado válido y se quitaría esta opción.
        """
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={database or self.database};"
            "Trusted_Connection=yes;"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )


def load_config() -> SqlConfig:
    return SqlConfig(
        server=os.environ.get("OLIST_SQL_SERVER", r".\SQLEXPRESS"),
        database=os.environ.get("OLIST_SQL_DATABASE", "OlistDW"),
        driver=os.environ.get("OLIST_SQL_DRIVER", "ODBC Driver 18 for SQL Server"),
    )
