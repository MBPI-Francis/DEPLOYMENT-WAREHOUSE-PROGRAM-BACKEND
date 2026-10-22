"""
API Router for Form Entries Adjustment Endpoints.

Provides dedicated routes for adjusting past transactions across all five categories:
- POST /create/receiving_form/
- POST /create/outgoing_form/
- POST /create/preparation_form/
- POST /create/transfer_form/
- POST /create/change_status_form/
- GET /list/
- GET /list/deleted/
- GET /list/historical/
- PUT /update/{form_type}/{adjustment_parent_id}/
- DELETE /delete/{adjustment_form_id}/
- PUT /restore/{adjustment_form_id}/
- GET /entry_validation/
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_adjustment_form.v1_form_entries.schemas import (
    AdjustmentFormResponse,
    ReceivingAdjustmentCreate,
    OutgoingAdjustmentCreate,
    PreparationAdjustmentCreate,
    TransferAdjustmentCreate,
    ChangeStatusAdjustmentCreate,
    ReceivingAdjustmentUpdate,
    OutgoingAdjustmentUpdate,
    PreparationAdjustmentUpdate,
    TransferAdjustmentUpdate,
    ChangeStatusAdjustmentUpdate
)
from api_rm_inv.api_adjustment_form.v1_form_entries.service import AdjustmentFormService

router = APIRouter(prefix="/adjustments/form-entries", tags=["Adjustments - Form Entries"])


# ===========================================================================
# 1. Specialized Creation Endpoints
# ===========================================================================

@router.post(
    "/create/receiving_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for a Receiving Report"
)
def create_receiving_adjustment(
    payload: ReceivingAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Corrects historical human errors on past receiving reports."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "receiving form", request, current_user)


@router.post(
    "/create/outgoing_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for an Outgoing Report"
)
def create_outgoing_adjustment(
    payload: OutgoingAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Corrects historical human errors on past outgoing reports."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "outgoing form", request, current_user)


@router.post(
    "/create/preparation_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for a Preparation Form"
)
def create_preparation_adjustment(
    payload: PreparationAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Corrects historical human errors on past preparation forms."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "preparation form", request, current_user)


@router.post(
    "/create/transfer_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for a Transfer Form"
)
def create_transfer_adjustment(
    payload: TransferAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Corrects historical human errors on past transfer forms."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "transfer form", request, current_user)


@router.post(
    "/create/change_status_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for a Change Status (Held) Form"
)
def create_change_status_adjustment(
    payload: ChangeStatusAdjustmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Corrects historical human errors on past quality change forms."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "change status form", request, current_user)


# ===========================================================================
# 2. Ledger Queries
# ===========================================================================

@router.get(
    "/list/",
    response_model=List[Dict[str, Any]],
    summary="List active form adjustments (Paginated)"
)
def read_adjustment_form(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves all active, un-cleared form adjustments for desktop grid display."""
    service = AdjustmentFormService(db)
    return service.get_adjustment_form(limit=limit, offset=offset)


@router.get(
    "/list/deleted/",
    response_model=List[Dict[str, Any]],
    summary="List soft-deleted form adjustments (Paginated)"
)
def read_deleted_adjustment_form(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves soft-deleted form adjustments for audit recovery."""
    service = AdjustmentFormService(db)
    return service.get_deleted_adjustment_form(limit=limit, offset=offset)


@router.get(
    "/list/historical/",
    response_model=List[Dict[str, Any]],
    summary="List historical computed form adjustments"
)
def read_historical_adjustment_form(
    record_id: Optional[UUID] = Query(None, description="Filter by specific record ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    rm_code: Optional[str] = Query(None, description="Filter by Material Code"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """Retrieves computed historical form adjustments with pagination."""
    service = AdjustmentFormService(db)
    return service.get_historical_adjustment_form(
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
        rm_code=rm_code,
        limit=limit,
        offset=offset
    )


# ===========================================================================
# 3. Specialized Updates
# ===========================================================================

@router.put(
    "/update/receiving_form/{adjustment_parent_id}/",
    summary="Update a Receiving Report adjustment"
)
def update_receiving_adjustment(
    adjustment_parent_id: UUID,
    payload: ReceivingAdjustmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "receiving form", request, current_user)


@router.put(
    "/update/outgoing_form/{adjustment_parent_id}/",
    summary="Update an Outgoing Report adjustment"
)
def update_outgoing_adjustment(
    adjustment_parent_id: UUID,
    payload: OutgoingAdjustmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "outgoing form", request, current_user)


@router.put(
    "/update/preparation_form/{adjustment_parent_id}/",
    summary="Update a Preparation Form adjustment"
)
def update_preparation_adjustment(
    adjustment_parent_id: UUID,
    payload: PreparationAdjustmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "preparation form", request, current_user)


@router.put(
    "/update/transfer_form/{adjustment_parent_id}/",
    summary="Update a Transfer Form adjustment"
)
def update_transfer_adjustment(
    adjustment_parent_id: UUID,
    payload: TransferAdjustmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "transfer form", request, current_user)


@router.put(
    "/update/change_status_form/{adjustment_parent_id}/",
    summary="Update a Change Status Form adjustment"
)
def update_change_status_adjustment(
    adjustment_parent_id: UUID,
    payload: ChangeStatusAdjustmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "change status form", request, current_user)


@router.delete(
    "/delete/{adjustment_form_id}/",
    summary="Soft-delete a form adjustment"
)
def delete_adjustment_form(
    adjustment_form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AdjustmentFormService(db)
    return service.soft_delete_adjustment_form(adjustment_form_id, request, current_user)


@router.put(
    "/restore/{adjustment_form_id}/",
    summary="Restore a soft-deleted form adjustment"
)
def restore_adjustment_form(
    adjustment_form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = AdjustmentFormService(db)
    return service.restore_adjustment_form(adjustment_form_id, request, current_user)


@router.get(
    "/entry_validation/",
    summary="Pre-validate if an adjustment would cause negative stock"
)
def validate_adjustment_form(
    form: str = Query(..., description="Form category ('outgoing', 'receiving', 'preparation', 'transfer', 'change status')"),
    incorrect_record_id: UUID = Query(..., description="UUID of the original incorrect record"),
    rm_id: UUID = Query(..., description="UUID of the raw material"),
    warehouse_id: UUID = Query(..., description="UUID of the warehouse"),
    entered_qty: Decimal = Query(..., description="New corrected quantity being proposed"),
    status_id: UUID = Query(..., description="UUID of the quality status"),
    db: Session = Depends(get_db)
):
    service = AdjustmentFormService(db)
    return service.validate_adjustment_form(
        form=form.strip().lower(),
        incorrect_record_id=incorrect_record_id,
        rm_id=rm_id,
        warehouse_id=warehouse_id,
        entered_qty=entered_qty,
        status_id=status_id
    )