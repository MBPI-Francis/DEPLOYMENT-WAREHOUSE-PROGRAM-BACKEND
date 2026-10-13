"""
Application Configuration Module.

Centralizes environment variables, database connection strings,
and PostgreSQL schema definitions.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """
    Application runtime configuration.

    Attributes:
        DATABASE_URL: PostgreSQL connection string pointing to mbpi_erp_db.
        DB_SCHEMA: Target PostgreSQL schema name (schema_whrm).
    """
    APP_NAME: str = "Plant Operations API"

    # 1. Connected to mbpi_erp_db (adjust host/port/credentials as needed)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:mbpi@localhost:5433/mbpi_erp_db"
    )

    # 2. Target schema dedicated to Raw Material Warehouse
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "schema_whrm")

    # Connection pool tuning
    DB_POOL_SIZE: int = 15
    DB_MAX_OVERFLOW: int = 10

    # Backup configuration
    BACKUP_FOLDER: str = os.getenv(
        "BACKUP_FOLDER",
        r"\\system-server\IT\Francis-Program-Projects\DB BACKUPS\WAREHOUSE PROGRAM"
    )
    PG_DUMP_PATH: str = os.getenv(
        "PG_DUMP_PATH",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
    )


settings = Settings()