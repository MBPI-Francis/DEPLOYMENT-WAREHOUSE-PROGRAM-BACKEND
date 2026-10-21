"""
API Router for Quality Status Change (Held Form) Endpoints.

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
from api_rm_inv.api_change_status_form.v1.schemas import (
    TempHeldFormCreate,
    TempHeldFormUpdate,
    TempHeldFormResponse
)
from api_rm_inv.api_change_status_form.v1.service import TempHeldFormService

router = APIRouter(prefix="/api/v1/rm/change-status-forms", tags=["Change Status Forms"])


@router.post(
    "/create/",
    response_model=TempHeldFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a quality status reclassification",
    responses={
        422: {"description": "Insufficient stock or identical current/new status"}
    }
)
def create_held_form(
    payload: TempHeldFormCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reclassifies material quality (e.g., from 'held : contaminated' to 'good').
    Validates available stock against schema_whrm.view_adjusted_ending_balance.
    """
    service = TempHeldFormService(db)
    return service.create_held_form(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[Dict[str, Any]],
    summary="List active status change forms (Paginated)"
)
def read_held_form(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves all active, non-cleared status changes for desktop UI tables."""
    service = TempHeldFormService(db)
    return service.get_held_form(limit=limit, offset=offset)


@router.get(
    "/list/deleted/",
    response_model=List[Dict[str, Any]],
    summary="List soft-deleted status change forms (Paginated)"
)
def read_deleted_held_form(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves soft-deleted status change records for audit recovery."""
    service = TempHeldFormService(db)
    return service.get_deleted_held_form(limit=limit, offset=offset)


@router.get(
    "/list/historical/",
    response_model=List[Dict[str, Any]],
    summary="List historical computed status change forms"
)
def read_historical_held_form(
    record_id: Optional[UUID] = Query(None, description="Filter by specific record ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    rm_code: Optional[str] = Query(None, description="Filter by Material Code"),
    warehouse_name: Optional[str] = Query(None, description="Filter by Warehouse Name"),
    current_status_name: Optional[str] = Query(None, description="Filter by Origin Status"),
    new_status_name: Optional[str] = Query(None, description="Filter by Destination Status"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """Retrieves computed historical status changes matching filter criteria with pagination."""
    service = TempHeldFormService(db)
    return service.get_historical_held_form(
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
        rm_code=rm_code,
        warehouse_name=warehouse_name,
        current_status_name=current_status_name,
        new_status_name=new_status_name,
        limit=limit,
        offset=offset
    )


@router.put(
    "/update/{held_form_id}/",
    response_model=TempHeldFormResponse,
    summary="Update an existing status change form"
)
def update_held_form(
    held_form_id: UUID,
    payload: TempHeldFormUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates an existing entry, re-validating stock availability before committing."""
    service = TempHeldFormService(db)
    return service.update_held_form(held_form_id, payload, request, current_user)


@router.delete(
    "/delete/{held_form_id}/",
    summary="Soft-delete a status change form"
)
def delete_held_form(
    held_form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks a status change as deleted without corrupting ledger calculations."""
    service = TempHeldFormService(db)
    return service.soft_delete_held_form(held_form_id, request, current_user)


@router.put(
    "/restore/{held_form_id}/",
    summary="Restore a soft-deleted status change form"
)
def restore_held_form(
    held_form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reactivates a previously soft-deleted status change entry."""
    service = TempHeldFormService(db)
    return service.restore_held_form(held_form_id, request, current_user)