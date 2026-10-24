"""
API Router for Supplies Outgoing Report Endpoints.

All endpoints use synchronous 'def' to allow threadpool concurrency
across LAN workstations and include limit/offset pagination.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_supplies_outgoing_report.v1.schemas import (
    SuppliesOutgoingFormCreate,
    SuppliesOutgoingFormUpdate,
    SuppliesOutgoingFormResponse
)
from api_rm_inv.api_supplies_outgoing_report.v1.service import SuppliesOutgoingFormService

router = APIRouter(prefix="/supplies-outgoing-reports", tags=["Supplies Outgoing Reports"])


@router.post(
    "/create/",
    response_model=SuppliesOutgoingFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a supplies dispatch",
    responses={
        422: {"description": "Insufficient warehouse stock or invalid business keys"}
    }
)
def create_outgoing_report(
    payload: SuppliesOutgoingFormCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Records warehouse supplies dispatched out with live stock validation."""
    service = SuppliesOutgoingFormService(db)
    return service.create_outgoing_report(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[Dict[str, Any]],
    summary="List active supplies outgoing reports (Paginated)"
)
def read_outgoing_report(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated active, non-cleared supplies outgoing reports."""
    service = SuppliesOutgoingFormService(db)
    return service.get_outgoing_report(limit=limit, offset=offset)


@router.get(
    "/list/deleted/",
    response_model=List[Dict[str, Any]],
    summary="List soft-deleted supplies outgoing reports (Paginated)"
)
def read_deleted_outgoing_report(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated soft-deleted supplies outgoing reports."""
    service = SuppliesOutgoingFormService(db)
    return service.get_deleted_outgoing_report(limit=limit, offset=offset)


@router.get(
    "/list/historical/",
    response_model=List[Dict[str, Any]],
    summary="List historical computed supplies outgoing reports"
)
def read_historical_outgoing_report(
    record_id: Optional[UUID] = Query(None, description="Optional record UUID filter"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves computed historical supplies records with pagination."""
    service = SuppliesOutgoingFormService(db)
    return service.get_historical_outgoing_report(record_id=record_id, limit=limit, offset=offset)


@router.put(
    "/update/{outgoing_report_id}/",
    response_model=SuppliesOutgoingFormResponse,
    summary="Update a supplies outgoing report"
)
def update_outgoing_report(
    outgoing_report_id: UUID,
    payload: SuppliesOutgoingFormUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates an existing supplies dispatch with stock re-validation."""
    service = SuppliesOutgoingFormService(db)
    return service.update_outgoing_report(outgoing_report_id, payload, request, current_user)


@router.delete(
    "/delete/{outgoing_report_id}/",
    summary="Soft-delete a supplies outgoing report"
)
def delete_outgoing_report(
    outgoing_report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks a supplies outgoing report as deleted without corrupting ledger balances."""
    service = SuppliesOutgoingFormService(db)
    return service.soft_delete_outgoing_report(outgoing_report_id, request, current_user)


@router.put(
    "/restore/{outgoing_report_id}/",
    summary="Restore a soft-deleted supplies outgoing report"
)
def restore_outgoing_report(
    outgoing_report_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reactivates a previously soft-deleted supplies outgoing report."""
    service = SuppliesOutgoingFormService(db)
    return service.restore_outgoing_report(outgoing_report_id, request, current_user)