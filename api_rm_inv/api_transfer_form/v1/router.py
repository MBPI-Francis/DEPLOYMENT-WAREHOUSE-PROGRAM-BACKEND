"""
API Router for Transfer Form Endpoints.

All endpoints use synchronous 'def' so database I/O executes in FastAPI's
worker thread pool, preventing multi-workstation queries from blocking the event loop.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from api_rm_inv.api_transfer_form.v1.schemas import (
    TempTransferFormCreate,
    TempTransferFormUpdate,
    TempTransferFormResponse
)
from api_rm_inv.api_transfer_form.v1.service import TempTransferFormService

router = APIRouter(prefix="/api/v1/rm/transfer-forms", tags=["Transfer Forms"])


@router.post(
    "/create/",
    response_model=TempTransferFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an internal warehouse transfer",
    responses={
        422: {"description": "Insufficient origin warehouse stock or identical origin/destination"}
    }
)
def create_transfer_form(
    payload: TempTransferFormCreate,
    db: Session = Depends(get_db)
):
    """
    Records stock moving between two warehouses.
    Validates that the Origin Warehouse has sufficient available stock in
    schema_whrm.view_adjusted_ending_balance before proceeding.
    """
    service = TempTransferFormService(db)
    return service.create_transfer_form(payload)


@router.put(
    "/update/{transfer_form_id}/",
    response_model=List[TempTransferFormResponse],
    summary="Update an existing transfer form",
    responses={
        404: {"description": "Transfer form record not found"},
        422: {"description": "Insufficient origin warehouse stock or invalid parameters"}
    }
)
def update_transfer_form(
    transfer_form_id: UUID,
    payload: TempTransferFormUpdate,
    db: Session = Depends(get_db)
):
    """Modifies an existing transfer record with stock availability re-validation."""
    service = TempTransferFormService(db)
    return service.update_transfer_form(transfer_form_id, payload)


@router.get(
    "/list/",
    response_model=List[TempTransferFormResponse],
    summary="List active transfer forms"
)
def read_transfer_form(db: Session = Depends(get_db)):
    """Retrieves all active, non-cleared transfers for the desktop UI table."""
    service = TempTransferFormService(db)
    return service.get_transfer_form()


@router.get(
    "/list/deleted/",
    response_model=List[TempTransferFormResponse],
    summary="List soft-deleted transfer forms"
)
def read_deleted_transfer_form(db: Session = Depends(get_db)):
    """Retrieves soft-deleted transfer forms for audit and recovery."""
    service = TempTransferFormService(db)
    return service.get_deleted_transfer_form()


@router.get(
    "/list/historical/",
    response_model=List[TempTransferFormResponse],
    summary="List historical computed transfer forms"
)
def read_historical_transfer_form(
    record_id: Optional[UUID] = Query(None, description="Filter by specific record ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    rm_code: Optional[str] = Query(None, description="Filter by Material Code"),
    from_warehouse_name: Optional[str] = Query(None, description="Filter by Origin Warehouse Name"),
    to_warehouse_name: Optional[str] = Query(None, description="Filter by Destination Warehouse Name"),
    status_name: Optional[str] = Query(None, description="Filter by Status Category"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return (defaults to 50)"),
    offset: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """
    Retrieves computed historical transfers matching multi-field filter parameters.
    Uses pagination (defaults to 50 records) to maintain high performance over the LAN.
    """
    service = TempTransferFormService(db)
    return service.get_historical_transfer_form(
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
        rm_code=rm_code,
        from_warehouse_name=from_warehouse_name,
        to_warehouse_name=to_warehouse_name,
        status_name=status_name,
        limit=limit,
        offset=offset
    )



@router.delete(
    "/delete/{transfer_form_id}/",
    response_model=List[TempTransferFormResponse],
    summary="Soft-delete a transfer form"
)
def delete_transfer_form(
    transfer_form_id: UUID,
    db: Session = Depends(get_db)
):
    """Marks a transfer as deleted without breaking ledger calculations."""
    service = TempTransferFormService(db)
    return service.soft_delete_transfer_form(transfer_form_id)


@router.put(
    "/restore/{transfer_form_id}/",
    response_model=List[TempTransferFormResponse],
    summary="Restore a soft-deleted transfer form"
)
def restore_transfer_form(
    transfer_form_id: UUID,
    db: Session = Depends(get_db)
):
    """Reactivates a previously soft-deleted transfer record."""
    service = TempTransferFormService(db)
    return service.restore_transfer_form(transfer_form_id)