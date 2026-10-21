"""
API Router for Stock on Hand Module.

All endpoints use synchronous 'def' to allow threadpool concurrency
across LAN workstations and include limit/offset pagination.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, File, UploadFile, status, Request, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initializes an SOH baseline row and records the audit log atomically."""
    service = StockOnHandService(db)
    return service.create_rm_soh(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[Dict[str, Any]],
    summary="List active Stock on Hand records (Paginated)"
)
def list_rm_soh(
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated active SOH baseline records."""
    service = StockOnHandService(db)
    return service.all_rm_soh(limit=limit, offset=offset)


@router.get(
    "/list/historical/",
    response_model=List[Dict[str, Any]],
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
    """Retrieves computed historical SOH snapshots with pagination."""
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Modifies an existing SOH entry and records an audit log atomically."""
    service = StockOnHandService(db)
    return service.update_rm_soh(rm_soh_id, payload, request, current_user)


@router.delete(
    "/delete/{rm_soh_id}/",
    summary="Soft-delete a Stock on Hand entry"
)
def delete_rm_soh(
    rm_soh_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks an SOH baseline row as deleted atomically."""
    service = StockOnHandService(db)
    return service.soft_delete_rm_soh(rm_soh_id, request, current_user)


@router.put(
    "/restore/{rm_soh_id}/",
    summary="Restore a soft-deleted Stock on Hand entry"
)
def restore_rm_soh(
    rm_soh_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reactivates a previously soft-deleted SOH entry atomically."""
    service = StockOnHandService(db)
    return service.restore_rm_soh(rm_soh_id, request, current_user)


@router.post(
    "/import_stock_data/",
    summary="Batch import Stock on Hand from encrypted/unencrypted Excel"
)
def import_stock_data(
    request: Request,
    file: UploadFile = File(...),
    password: Optional[str] = Query(None, description="Password if spreadsheet is encrypted"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """High-performance batch importer with memory bounds and atomic audit trail."""
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB boundary
    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 25MB limit."
        )

    service = StockOnHandService(db)
    return service.import_rm_soh(content, request, current_user, password)