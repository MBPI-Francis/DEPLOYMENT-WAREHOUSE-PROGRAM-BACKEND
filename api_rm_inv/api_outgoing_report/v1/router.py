"""
API Router for Outgoing Report Endpoints (v2).

All endpoints use synchronous 'def' so database I/O runs in FastAPI's
worker thread pool, preventing concurrent LAN clients from blocking the event loop.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from api_rm_inv.api_outgoing_report.v1.schemas import (
    OutgoingFormCreate,
    OutgoingFormUpdate,
    OutgoingFormResponse
)
from api_rm_inv.api_outgoing_report.v1.service import TempOutgoingReportService

router = APIRouter(prefix="/api/v1/rm/outgoing-reports", tags=["Outgoing Reports"])


@router.post(
    "/create/",
    response_model=OutgoingFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an outbound material dispatch",
    responses={
        422: {"description": "Insufficient warehouse stock or invalid business keys"}
    }
)
def create_outgoing_report(
    payload: OutgoingFormCreate,
    db: Session = Depends(get_db)
):
    """
    Records material or supplies dispatched out of the plant.
    Validates stock availability in schema_whrm.view_adjusted_ending_balance.
    Accepts human business keys: rm_code, wh_number, status_name.
    """
    service = TempOutgoingReportService(db)
    return service.create_outgoing_report(payload)


@router.get(
    "/list/",
    response_model=List[OutgoingFormResponse],
    summary="List active outgoing reports"
)
def read_outgoing_report(db: Session = Depends(get_db)):
    """Retrieves all active, non-cleared outgoing reports for desktop grid display."""
    service = TempOutgoingReportService(db)
    return service.get_outgoing_report()


@router.get(
    "/list/deleted/",
    response_model=List[OutgoingFormResponse],
    summary="List soft-deleted outgoing reports"
)
def read_deleted_outgoing_report(db: Session = Depends(get_db)):
    """Retrieves soft-deleted outgoing reports for auditing and recovery."""
    service = TempOutgoingReportService(db)
    return service.get_deleted_outgoing_report()


@router.get(
    "/list/historical/",
    response_model=List[OutgoingFormResponse],
    summary="List historical computed outgoing reports"
)
def read_historical_outgoing_report(
    record_id: Optional[UUID] = Query(None, description="Filter by specific record ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    rm_code: Optional[str] = Query(None, description="Filter by Material Code"),
    warehouse_name: Optional[str] = Query(None, description="Filter by Warehouse Name"),
    status_name: Optional[str] = Query(None, description="Filter by Status Category"),
    outgoing_type: Optional[str] = Query(None, description="Filter by type ('RM' or 'SUPPLY')"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """
    Retrieves computed historical outgoing reports with multi-field filtering
    and pagination (defaults to 50 rows) to keep response times fast across the LAN.
    """
    service = TempOutgoingReportService(db)
    return service.get_historical_outgoing_report(
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
        rm_code=rm_code,
        warehouse_name=warehouse_name,
        status_name=status_name,
        outgoing_type=outgoing_type,
        limit=limit,
        offset=offset
    )


@router.put(
    "/update/{outgoing_report_id}/",
    response_model=List[OutgoingFormResponse],
    summary="Update an existing outgoing report",
    responses={
        404: {"description": "Outgoing report not found"},
        422: {"description": "Insufficient warehouse stock"}
    }
)
def update_outgoing_report(
    outgoing_report_id: UUID,
    payload: OutgoingFormUpdate,
    db: Session = Depends(get_db)
):
    """Modifies an existing outgoing report with stock re-validation."""
    service = TempOutgoingReportService(db)
    return service.update_outgoing_report(outgoing_report_id, payload)


@router.delete(
    "/delete/{outgoing_report_id}/",
    response_model=List[OutgoingFormResponse],
    summary="Soft-delete an outgoing report"
)
def delete_outgoing_report(
    outgoing_report_id: UUID,
    db: Session = Depends(get_db)
):
    """Marks an outgoing report as deleted without breaking inventory ledger balances."""
    service = TempOutgoingReportService(db)
    return service.soft_delete_outgoing_report(outgoing_report_id)


@router.put(
    "/restore/{outgoing_report_id}/",
    response_model=List[OutgoingFormResponse],
    summary="Restore a soft-deleted outgoing report"
)
def restore_outgoing_report(
    outgoing_report_id: UUID,
    db: Session = Depends(get_db)
):
    """Reactivates a previously soft-deleted outgoing report after re-validating stock availability."""
    service = TempOutgoingReportService(db)
    return service.restore_outgoing_report(outgoing_report_id)