"""
Application Configuration Module.

Centralizes environment variables, database connection strings,
connection pool parameters, security settings, departmental schema namespaces,
and network compression thresholds.
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """
    Application runtime configuration optimized for multi-client LAN operations.
    """
    APP_NAME: str = "MBPI ERP - Warehouse Operations API"

    # PostgreSQL Connection String pointing to mbpi_erp_db
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:mbpi@localhost:5433/mbpi_erp_db"
    )

    # Dedicated schema for Raw Material Warehouse (Active Module)
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "schema_whrm")

    # -----------------------------------------------------------------------
    # Future Departmental Schema Namespaces (Single Database, Isolated Schemas)
    # -----------------------------------------------------------------------
    SCHEMA_RM: str = os.getenv("SCHEMA_RM", "schema_whrm")      # Raw Materials Warehouse
    SCHEMA_FG: str = os.getenv("SCHEMA_FG", "schema_whfg")      # Finished Goods Warehouse
    SCHEMA_PROD: str = os.getenv("SCHEMA_PROD", "schema_prod")  # Production & Batch Runs
    SCHEMA_LAB: str = os.getenv("SCHEMA_LAB", "schema_labqc")   # Quality Control & Lab

    # -----------------------------------------------------------------------
    # Database Connection Pool Tuning (High-Concurrency LAN)
    # -----------------------------------------------------------------------
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))        # Steady persistent connections
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))  # Burst connections for traffic spikes
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))  # Wait up to 30s before timing out
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))# Reconnect after 30 mins to avoid stale sockets

    # Network Compression Threshold
    GZIP_MINIMUM_SIZE: int = 1000  # Compress any response larger than 1 KB

    # Backup configuration
    BACKUP_FOLDER: str = os.getenv(
        "BACKUP_FOLDER",
        r"\\system-server\IT\Francis-Program-Projects\DB BACKUPS\WAREHOUSE PROGRAM"
    )
    PG_DUMP_PATH: str = os.getenv(
        "PG_DUMP_PATH",
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
    )

    # -----------------------------------------------------------------------
    # JWT Authentication & Security Configuration (Runs 100% Offline / LAN)
    # -----------------------------------------------------------------------
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "mbpi-secret-key-plant-operations-2026-secure-token-lan")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 12 hours (1 full shift)

    # -----------------------------------------------------------------------
    # Service Account API Keys for Program-to-Program Integration
    # -----------------------------------------------------------------------
    # Using field(default_factory=...) to comply with Python dataclass standards
    SERVICE_API_KEYS: dict = field(default_factory=lambda: {
        "mbpi-prod-secret-key-2026": "service_production_app",
        "mbpi-lab-secret-key-2026": "service_lab_program",
        "mbpi-fg-secret-key-2026": "service_finished_goods_app",
    })


settings = Settings()