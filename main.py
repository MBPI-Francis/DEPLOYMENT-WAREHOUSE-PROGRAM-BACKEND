"""
Main Application Entry Point.

Boots the FastAPI application, mounts multi-department routers 
(Raw Materials, Finished Goods, Production), and initializes background services.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Core database and background tasks
from core.database import engine, Base
from core.scheduler import start_scheduler

# RM Inventory module setup and views
from api_rm_inv.router import rm_router
from api_rm_inv.settings.create_view_table import (
    create_beginning_view_table,
    create_ending_view_table,
    create_adjusted_ending_view_table,
    create_view_form_entries_log_table,
)
from api_rm_inv.settings.create_product_kind import create_product_kind


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown events cleanly.
    Modern replacement for deprecated @app.on_event('startup').
    """
    # 1. Ensure all database tables exist
    print("INFO: Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    # 2. Initialize RM database views and default product kinds
    print("INFO: Initializing RM stock views...")
    create_beginning_view_table()
    create_ending_view_table()
    create_adjusted_ending_view_table()
    create_view_form_entries_log_table()
    create_product_kind()

    # 3. Start automated daily backup scheduler
    start_scheduler()

    yield  # Application runs here

    print("INFO: Application shutdown completed.")


# Initialize the master FastAPI app
app = FastAPI(
    title="Warehouse Operations API",
    description="LAN Backend API serving Raw Materials, Finished Goods, and Production systems.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware for LAN client connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Mount Business Domain APIs
# ---------------------------------------------------------------------------

# 1. Raw Materials Inventory API (Active)
app.include_router(rm_router)

# 2. Finished Goods Inventory API (Future placeholder)
# from api_fg_inv.router import fg_router
# app.include_router(fg_router, prefix="/api/v1/fg")

# 3. Production API (Future placeholder)
# from api_prod.router import prod_router
# app.include_router(prod_router, prefix="/api/v1/prod")


@app.get("/", tags=["Health Check"])
def root():
    """Basic health check route verifying that the API server is active on the LAN."""
    return {"status": "online", "message": "Warehouse Operations API is operational"}