"""
API Router for Receiving Report Endpoints.

All endpoints use synchronous 'def' so database I/O runs inside FastAPI's
worker thread pool, preventing multi-workstation queries from blocking the event loop.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from api_rm_inv.api_receiving_report.v1.schemas import (
    TempReceivingReportCreate,
    TempReceivingReportUpdate,
    TempReceivingReportResponse
)
from api_rm_inv.api_receiving_report.v1.service import TempReceivingReportService

router = APIRouter(prefix="/api/v1/rm/receiving-reports", tags=["Receiving Reports"])


@router.post(
    "/create/",
    response_model=TempReceivingReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new receiving report entry"
)
def create_receiving_report(
    payload: TempReceivingReportCreate,
    db: Session = Depends(get_db)
):
    """
    Records an incoming shipment of raw materials.
    Accepts human business keys: rm_code, wh_number, and status_name.
    """
    service = TempReceivingReportService(db)
    return service.create_receiving_report(payload)


@router.get(
    "/list/",
    response_model=List[TempReceivingReportResponse],
    summary="List active receiving reports"
)
def get_receiving_report(db: Session = Depends(get_db)):
    """Retrieves all active, non-cleared receiving reports for the desktop UI table."""
    service = TempReceivingReportService(db)
    return service.get_receiving_report()


@router.get(
    "/list/deleted/",
    response_model=List[TempReceivingReportResponse],
    summary="List soft-deleted receiving reports"
)
def get_deleted_receiving_report(db: Session = Depends(get_db)):
    """Retrieves all soft-deleted receiving reports for audit and recovery."""
    service = TempReceivingReportService(db)
    return service.get_deleted_receiving_report()


@router.get(
    "/list/historical/",
    response_model=List[TempReceivingReportResponse],
    summary="List historical computed receiving reports"
)
def get_historical_receiving_report(
    record_id: Optional[UUID] = Query(None, description="Optional UUID to filter a specific historical report"),
    db: Session = Depends(get_db)
):
    """Retrieves reports that have already been computed into historical closing balances."""
    service = TempReceivingReportService(db)
    return service.get_historical_receiving_report(record_id)


@router.put(
    "/update/{receiving_report_id}/",
    response_model=List[TempReceivingReportResponse],
    summary="Update an existing receiving report"
)
def update_receiving_report(
    receiving_report_id: UUID,
    payload: TempReceivingReportUpdate,
    db: Session = Depends(get_db)
):
    """Modifies an existing receiving report and returns the refreshed active list."""
    service = TempReceivingReportService(db)
    return service.update_receiving_report(receiving_report_id, payload)


@router.delete(
    "/delete/{receiving_report_id}/",
    response_model=List[TempReceivingReportResponse],
    summary="Soft-delete a receiving report"
)
def delete_receiving_report(
    receiving_report_id: UUID,
    db: Session = Depends(get_db)
):
    """Marks a report as deleted without breaking historical ledger balances."""
    service = TempReceivingReportService(db)
    return service.soft_delete_receiving_report(receiving_report_id)


@router.put(
    "/restore/{receiving_report_id}/",
    response_model=List[TempReceivingReportResponse],
    summary="Restore a soft-deleted receiving report"
)
def restore_receiving_report(
    receiving_report_id: UUID,
    db: Session = Depends(get_db)
):
    """Reactivates a previously soft-deleted receiving report."""
    service = TempReceivingReportService(db)
    return service.restore_receiving_report(receiving_report_id)