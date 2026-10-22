"""
Application Configuration Module.

Centralizes environment variables, database connection strings,
hardware-calibrated connection pool parameters, security settings,
departmental schema namespaces, and network compression thresholds.

HARDWARE ENVIRONMENT PROFILE:
- Host CPU: Intel Xeon E3-1220 V2 @ 3.10GHz (4 physical cores, 4 threads, no hyperthreading).
- Host RAM: 8 GB Total.
- Host Co-tenant Services: PostgreSQL 16 Server, FastAPI Backend, Legacy Visual FoxPro (VFP) Applications (.dbf/.cdx).
"""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    """
    Application runtime configuration optimized for multi-client LAN operations
    coexisting on constrained server hardware.
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
    # Database Connection Pool Tuning (Calibrated for 8GB RAM & 4-Core Xeon)
    # -----------------------------------------------------------------------
    # WHY: Reduced from 20 to 12.
    # PURPOSE: In SQLAlchemy, each Uvicorn worker maintains its own isolated pool.
    # When running 2 workers: 2 workers * 12 connections = 24 persistent connections.
    # IMPACT ON PERFORMANCE & RAM: Each open PostgreSQL connection consumes ~5MB - 10MB of RAM.
    # 24 connections hold only ~120MB - 240MB, leaving ample memory for Windows, FoxPro,
    # and PostgreSQL shared buffers. This avoids OS swapping and prevents Out-of-Memory (OOM) crashes.
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "12"))

    # WHY: Reduced from 10 to 5.
    # PURPOSE: Sets the ceiling for temporary burst connections during morning shift punch-ins or
    # barcode scanner rush hours without permanently allocating RAM.
    # IMPACT ON PERFORMANCE: Under maximum burst across 2 workers: 2 * (12 + 5) = 34 connections maximum.
    # PostgreSQL can comfortably handle 34 active queries without CPU context switching on 4 cores.
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "5"))

    # WHY: Kept at 30 seconds.
    # PURPOSE: Maximum time an incoming request will wait in line for a free connection from the pool.
    # IMPACT ON PERFORMANCE: Prevents PyQt6 desktop clients from hanging indefinitely if a heavy query
    # temporarily saturates the pool; fails with a clean 500 error instead of freezing the UI.
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))

    # WHY: Kept at 1800 seconds (30 minutes).
    # PURPOSE: Automatically recycles and recreates connections older than 30 minutes.
    # IMPACT ON PERFORMANCE: Windows network sockets can become 'stale' or drop silently across the LAN
    # if a workstation sleeps or the switch resets. This drops dead sockets cleanly and reclaims memory.
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    # -----------------------------------------------------------------------
    # Concurrency & Thread Pool Limits (FastAPI AnyIO Limiter)
    # -----------------------------------------------------------------------
    # WHY: Added explicit configuration for FastAPI's anyio worker thread capacity.
    # PURPOSE: Sync endpoints ('def') are dispatched to this thread pool.
    # Default is only 40. Setting this to 60 allows 100+ LAN clients (desktop apps + handhelds)
    # to queue and process quickly without CPU core thrashing on a 4-core Xeon.
    THREAD_POOL_LIMIT: int = int(os.getenv("THREAD_POOL_LIMIT", "60"))

    # -----------------------------------------------------------------------
    # Network Compression Threshold
    # -----------------------------------------------------------------------
    # WHY: Raised from 1000 bytes (1 KB) to 2048 bytes (2 KB).
    # PURPOSE: Compressing very small JSON responses (< 2KB) consumes CPU cycles on the Xeon E3
    # without yielding meaningful bandwidth reduction over an internal 1 Gbps LAN.
    # IMPACT ON PERFORMANCE: Saves CPU clock cycles for FoxPro and PostgreSQL by only running
    # GZip compression on substantial data tables (e.g., reports, SOH lists, large ledgers).
    GZIP_MINIMUM_SIZE: int = 2048

    # -----------------------------------------------------------------------
    # Automated Backup Configuration
    # -----------------------------------------------------------------------
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
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "mbpi-secret-key-plant-operations-2026-secure-token-lan"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 12 hours (1 full shift)

    # -----------------------------------------------------------------------
    # Service Account API Keys for Program-to-Program Integration
    # -----------------------------------------------------------------------
    SERVICE_API_KEYS: dict = field(default_factory=lambda: {
        "mbpi-prod-secret-key-2026": "service_production_app",
        "mbpi-lab-secret-key-2026": "service_lab_program",
        "mbpi-fg-secret-key-2026": "service_finished_goods_app",
    })


settings = Settings()