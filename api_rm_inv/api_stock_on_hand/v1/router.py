"""
API Router for Stock on Hand Module.

All endpoints use synchronous 'def' to allow threadpool concurrency
across LAN workstations and include limit/offset pagination.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, File, UploadFile, status
from sqlalchemy.orm import Session

from core.database import get_db
from api_rm_inv.api_stock_on_hand.v1.schemas import (
    StockOnHandCreate,
    StockOnHandUpdate,
    StockOnHandResponse,
    HistoricalStockOnHandResponse
)
from api_rm_inv.api_stock_on_hand.v1.service import StockOnHandService

router = APIRouter(prefix="/api/v1/rm/stock-on-hand", tags=["Stock on Hand"])


@router.post(
    "/create/",
    response_model=StockOnHandResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual Stock on Hand baseline record"
)
def create_rm_soh(
    payload: StockOnHandCreate,
    db: Session = Depends(get_db)
):
    """
    Initializes a Stock on Hand baseline row.
    Accepts human business keys: rm_code, wh_number, status_name.
    """
    service = StockOnHandService(db)
    return service.create_rm_soh(payload)


@router.get(
    "/list/",
    response_model=List[StockOnHandResponse],
    summary="List active Stock on Hand records (Paginated)"
)
def list_rm_soh(
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """
    Retrieves active SOH baseline records with pagination to prevent
    loading millions of records into memory at once.
    """
    service = StockOnHandService(db)
    return service.all_rm_soh(limit=limit, offset=offset)


@router.get(
    "/list/historical/",
    response_model=List[HistoricalStockOnHandResponse],
    summary="List historical computed Stock on Hand snapshots"
)
def get_historical_stock_on_hand(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    mat_code: Optional[str] = Query(None, description="Raw Material Code (or 'all')"),
    location: Optional[str] = Query(None, description="Warehouse Name (or 'all')"),
    status: Optional[str] = Query(None, description="Quality Status Name (or 'all')"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """
    Retrieves computed historical SOH snapshots matching filter parameters.
    Includes pagination to maintain fast response times across the LAN.
    """
    service = StockOnHandService(db)
    return service.get_historical_stock_on_hand(
        date_from=date_from,
        date_to=date_to,
        mat_code=mat_code,
        location=location,
        status_name=status,
        limit=limit,
        offset=offset
    )


@router.put(
    "/update/{rm_soh_id}/",
    summary="Update a Stock on Hand entry"
)
def update_rm_soh(
    rm_soh_id: UUID,
    payload: StockOnHandUpdate,
    db: Session = Depends(get_db)
):
    """Modifies an existing SOH entry."""
    service = StockOnHandService(db)
    return service.update_rm_soh(rm_soh_id, payload)


@router.delete(
    "/delete/{rm_soh_id}/",
    summary="Soft-delete a Stock on Hand entry"
)
def delete_rm_soh(
    rm_soh_id: UUID,
    db: Session = Depends(get_db)
):
    """Marks an SOH baseline row as deleted."""
    service = StockOnHandService(db)
    return service.soft_delete_rm_soh(rm_soh_id)


@router.put(
    "/restore/{rm_soh_id}/",
    summary="Restore a soft-deleted Stock on Hand entry"
)
def restore_rm_soh(
    rm_soh_id: UUID,
    db: Session = Depends(get_db)
):
    """Reactivates a previously soft-deleted SOH entry."""
    service = StockOnHandService(db)
    return service.restore_rm_soh(rm_soh_id)


@router.post(
    "/import_stock_data/",
    summary="Batch import Stock on Hand from encrypted/unencrypted Excel"
)
def import_stock_data(
    file: UploadFile = File(...),
    password: Optional[str] = Query(None, description="Password if spreadsheet is encrypted"),
    db: Session = Depends(get_db)
):
    """
    High-performance batch importer.
    Pre-caches all lookups in memory and batch-saves all rows in one atomic commit.
    """
    content = file.file.read()
    service = StockOnHandService(db)
    return service.import_rm_soh(content, password)