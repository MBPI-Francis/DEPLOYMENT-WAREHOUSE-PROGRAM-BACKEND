"""
Main Application Entry Point.

Boots the FastAPI application, configures CORS and GZip compression middleware,
mounts multi-department routers, and initializes background tasks.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

# Core configuration and database
from core.config import settings
from core.database import engine, Base, ensure_schema_exists
from core.dependencies import get_current_user
from core.scheduler import start_scheduler

# RM Inventory master router and views

from api_rm_inv.settings.create_view_table import (
    create_beginning_view_table,
    create_ending_view_table,
    create_adjusted_ending_view_table,
    create_view_form_entries_log_table,
)
from api_rm_inv.settings.create_product_kind import create_product_kind


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes schemas, tables, views, and maintenance tasks on server boot."""
    print("INFO: Initializing database infrastructure...")

    # 1. Guarantee schema_whrm exists in mbpi_erp_db
    ensure_schema_exists()

    # 2. Create tables inside schema_whrm
    Base.metadata.create_all(bind=engine)

    # 3. Create/verify RM calculation views inside schema_whrm
    create_beginning_view_table()
    create_ending_view_table()
    create_adjusted_ending_view_table()
    create_view_form_entries_log_table()
    create_product_kind()

    # 4. Start automated daily backup scheduler
    start_scheduler()

    yield

    print("INFO: Application shutdown completed.")


app = FastAPI(
    title=settings.APP_NAME,
    description="LAN Backend API serving Raw Materials, Finished Goods, and Production systems.",
    version="2.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware Configuration
# ---------------------------------------------------------------------------

# 1. GZip Compression: Compresses large JSON table responses (over 1 KB) by 70-80%
app.add_middleware(GZipMiddleware, minimum_size=settings.GZIP_MINIMUM_SIZE)

# 2. CORS: Permits all workstations on the office LAN to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Router Mounting
# ---------------------------------------------------------------------------

# 1. Mount central authentication (Company-wide)
from shared.auth.router import router as auth_router
app.include_router(auth_router)

# 2. Raw Materials Inventory API (Active)
from api_rm_inv.router import rm_router
# app.include_router(rm_router)

app.include_router(
    rm_router,
    prefix="/api/v1/rm",
    dependencies=[Depends(get_current_user)]  # 🔒 Blocks any request without a valid token!
)

from shared.audit.router import router as global_audit_router
app.include_router(global_audit_router)

# 3. Finished Goods Inventory API (Future placeholder)
# from api_fg_inv.router import fg_router
# app.include_router(fg_router, prefix="/api/v1/fg")

# 4. Production API (Future placeholder)
# from api_prod.router import prod_router
# app.include_router(prod_router, prefix="/api/v1/prod")


@app.get("/", tags=["Health Check"])
def root():
    """Basic ping route verifying the server is active on the local network."""
    return {
        "status": "online",
        "database": "mbpi_erp_db",
        "schema": settings.DB_SCHEMA,
        "compression": "gzip_enabled"
    }

