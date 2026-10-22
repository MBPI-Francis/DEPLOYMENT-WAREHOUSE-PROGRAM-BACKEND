"""
API Router for Spillage Adjustment Form Endpoints.

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
from api_rm_inv.api_adjustment_form.v1_spillage.schemas import (
    AdjustmentFormCreate,
    AdjustmentFormUpdate,
    AdjustmentFormResponse
)
from api_rm_inv.api_adjustment_form.v1_spillage.service import AdjustmentFormService

router = APIRouter(prefix="/adjustments/spillage", tags=["Adjustments - Spillage"])


@router.post(
    "/create/",
    response_model=AdjustmentFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a chemical spillage or physical loss",
    responses={
        422: {"description": "Insufficient warehouse stock or invalid business keys"}
    }
)
def create_adjustment_form(
    payload: AdjustmentFormCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Records physical spillage loss from a warehouse.
    Validates stock availability in schema_whrm.view_adjusted_ending_balance.
    """
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[Dict[str, Any]],
    summary="List active spillage forms (Paginated)"
)
def read_adjustment_form(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves all active, non-cleared spillage entries for desktop UI tables."""
    service = AdjustmentFormService(db)
    return service.get_adjustment_form(limit=limit, offset=offset)


@router.get(
    "/list/deleted/",
    response_model=List[Dict[str, Any]],
    summary="List soft-deleted spillage forms (Paginated)"
)
def read_deleted_adjustment_form(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves soft-deleted spillage records for audit recovery."""
    service = AdjustmentFormService(db)
    return service.get_deleted_adjustment_form(limit=limit, offset=offset)


@router.get(
    "/list/historical/",
    response_model=List[Dict[str, Any]],
    summary="List historical computed spillage forms"
)
def read_historical_adjustment_form(
    record_id: Optional[UUID] = Query(None, description="Filter by specific record ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    rm_code: Optional[str] = Query(None, description="Filter by Material Code"),
    warehouse_name: Optional[str] = Query(None, description="Filter by Warehouse Name"),
    status_name: Optional[str] = Query(None, description="Filter by Status Category"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """Retrieves computed historical spillage records with multi-field filtering and pagination."""
    service = AdjustmentFormService(db)
    return service.get_historical_adjustment_form(
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
        rm_code=rm_code,
        warehouse_name=warehouse_name,
        status_name=status_name,
        limit=limit,
        offset=offset
    )


@router.put(
    "/update/{adjustment_form_id}/",
    response_model=AdjustmentFormResponse,
    summary="Update an existing spillage form",
    responses={
        404: {"description": "Spillage record not found"},
        422: {"description": "Insufficient warehouse stock"}
    }
)
def update_adjustment_form(
    adjustment_form_id: UUID,
    payload: AdjustmentFormUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Modifies an existing spillage record with live stock re-validation."""
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_form_id, payload, request, current_user)


@router.delete(
    "/delete/{adjustment_form_id}/",
    summary="Soft-delete a spillage form"
)
def delete_adjustment_form(
    adjustment_form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks a spillage record as deleted without breaking inventory ledger calculations."""
    service = AdjustmentFormService(db)
    return service.soft_delete_adjustment_form(adjustment_form_id, request, current_user)


@router.put(
    "/restore/{adjustment_form_id}/",
    summary="Restore a soft-deleted spillage form"
)
def restore_adjustment_form(
    adjustment_form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reactivates a previously soft-deleted spillage record after re-validating stock availability."""
    service = AdjustmentFormService(db)
    return service.restore_adjustment_form(adjustment_form_id, request, current_user)