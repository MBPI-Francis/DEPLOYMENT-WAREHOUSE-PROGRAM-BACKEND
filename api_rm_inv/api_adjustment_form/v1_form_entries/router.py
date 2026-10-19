"""
API Router for Form Entries Adjustment Endpoints.

Provides dedicated routes for adjusting past transactions:
- POST /create/receiving_form/
- POST /create/outgoing_form/
- POST /create/preparation_form/
- POST /create/transfer_form/
- POST /create/change_status_form/
- GET /list/
- GET /list/deleted/
- GET /list/historical/
- PUT /update/{adjustment_form_id}/
- DELETE /delete/{adjustment_form_id}/
- PUT /restore/{adjustment_form_id}/
- GET /entry_validation/
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from api_rm_inv.api_adjustment_form.v1_form_entries.schemas import (
    AdjustmentFormResponse, ReceivingAdjustmentCreate, OutgoingAdjustmentCreate, PreparationAdjustmentCreate,
    TransferAdjustmentCreate, ChangeStatusAdjustmentCreate, ReceivingAdjustmentUpdate, OutgoingAdjustmentUpdate,
    PreparationAdjustmentUpdate, TransferAdjustmentUpdate, ChangeStatusAdjustmentUpdate
)
from api_rm_inv.api_adjustment_form.v1_form_entries.service import AdjustmentFormService

router = APIRouter(prefix="/api/v1/rm/adjustments/form-entries", tags=["Adjustments - Form Entries"])


# ===========================================================================
# 1. Specialized Creation Endpoints
# ===========================================================================

@router.post(
    "/create/receiving_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for a Receiving Report"
)
def create_receiving_adjustment(
    payload: ReceivingAdjustmentCreate,  # <-- Dedicated clean schema!
    db: Session = Depends(get_db)
):
    """Corrects historical human errors on past receiving reports."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "receiving form")


@router.post(
    "/create/outgoing_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for an Outgoing Report"
)
def create_outgoing_adjustment(
    payload: OutgoingAdjustmentCreate,  # <-- Dedicated clean schema!
    db: Session = Depends(get_db)
):
    """Corrects historical human errors on past outgoing reports."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "outgoing form")


@router.post(
    "/create/preparation_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for a Preparation Form"
)
def create_preparation_adjustment(
    payload: PreparationAdjustmentCreate,  # <-- Dedicated clean schema!
    db: Session = Depends(get_db)
):
    """Corrects historical human errors on past preparation forms."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "preparation form")


@router.post(
    "/create/transfer_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for a Transfer Form"
)
def create_transfer_adjustment(
    payload: TransferAdjustmentCreate,  # <-- Dedicated clean schema!
    db: Session = Depends(get_db)
):
    """Corrects historical human errors on past transfer forms."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "transfer form")


@router.post(
    "/create/change_status_form/",
    status_code=status.HTTP_201_CREATED,
    summary="Record an adjustment correction for a Change Status (Held) Form"
)
def create_change_status_adjustment(
    payload: ChangeStatusAdjustmentCreate,  # <-- Dedicated clean schema!
    db: Session = Depends(get_db)
):
    """Corrects historical human errors on past quality change forms."""
    service = AdjustmentFormService(db)
    return service.create_adjustment_form(payload, "change status form")


# ===========================================================================
# 2. Ledger Queries & Maintenance
# ===========================================================================

@router.get(
    "/list/",
    response_model=List[AdjustmentFormResponse],
    summary="List active form adjustments"
)
def read_adjustment_form(db: Session = Depends(get_db)):
    """Retrieves all active, un-cleared form adjustments for desktop grid display."""
    service = AdjustmentFormService(db)
    return service.get_adjustment_form()


@router.get(
    "/list/deleted/",
    response_model=List[AdjustmentFormResponse],
    summary="List soft-deleted form adjustments"
)
def read_deleted_adjustment_form(db: Session = Depends(get_db)):
    """Retrieves soft-deleted form adjustments for audit recovery."""
    service = AdjustmentFormService(db)
    return service.get_deleted_adjustment_form()


@router.get(
    "/list/historical/",
    response_model=List[AdjustmentFormResponse],
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
    """
    Retrieves computed historical form adjustments with pagination
    (default 50 rows) to keep response times fast across the LAN.
    """
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
# 3. UPDATE
# ===========================================================================

@router.put(
    "/update/receiving_form/{adjustment_parent_id}/",
    summary="Update a Receiving Report adjustment"
)
def update_receiving_adjustment(
    adjustment_parent_id: UUID,
    payload: ReceivingAdjustmentUpdate,
    db: Session = Depends(get_db)
):
    """Updates an existing Receiving Report correction."""
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "receiving form")


@router.put(
    "/update/outgoing_form/{adjustment_parent_id}/",
    summary="Update an Outgoing Report adjustment"
)
def update_outgoing_adjustment(
    adjustment_parent_id: UUID,
    payload: OutgoingAdjustmentUpdate,
    db: Session = Depends(get_db)
):
    """Updates an existing Outgoing Report correction."""
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "outgoing form")


@router.put(
    "/update/preparation_form/{adjustment_parent_id}/",
    summary="Update a Preparation Form adjustment"
)
def update_preparation_adjustment(
    adjustment_parent_id: UUID,
    payload: PreparationAdjustmentUpdate,
    db: Session = Depends(get_db)
):
    """Updates an existing Preparation Form correction."""
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "preparation form")


@router.put(
    "/update/transfer_form/{adjustment_parent_id}/",
    summary="Update a Transfer Form adjustment"
)
def update_transfer_adjustment(
    adjustment_parent_id: UUID,
    payload: TransferAdjustmentUpdate,
    db: Session = Depends(get_db)
):
    """Updates an existing Transfer Form correction."""
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "transfer form")


@router.put(
    "/update/change_status_form/{adjustment_parent_id}/",
    summary="Update a Change Status Form adjustment"
)
def update_change_status_adjustment(
    adjustment_parent_id: UUID,
    payload: ChangeStatusAdjustmentUpdate,
    db: Session = Depends(get_db)
):
    """Updates an existing Change Status Form correction."""
    service = AdjustmentFormService(db)
    return service.update_adjustment_form(adjustment_parent_id, payload, "change status form")


@router.delete(
    "/delete/{adjustment_form_id}/",
    response_model=List[AdjustmentFormResponse],
    summary="Soft-delete a form adjustment"
)
def delete_adjustment_form(
    adjustment_form_id: UUID,
    db: Session = Depends(get_db)
):
    """Marks a correction line as deleted without breaking historical ledger balances."""
    service = AdjustmentFormService(db)
    return service.soft_delete_adjustment_form(adjustment_form_id)


@router.put(
    "/restore/{adjustment_form_id}/",
    response_model=AdjustmentFormResponse,
    summary="Restore a soft-deleted form adjustment"
)
def restore_adjustment_form(
    adjustment_form_id: UUID,
    db: Session = Depends(get_db)
):
    """Reactivates a previously soft-deleted correction entry."""
    service = AdjustmentFormService(db)
    return service.restore_adjustment_form(adjustment_form_id)


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
    """
    Simulates applying the correction against view_adjusted_ending_balance
    to verify that the change will not drive the warehouse into a negative stock deficit.
    """
    service = AdjustmentFormService(db)
    return service.validate_adjustment_form(
        form=form.strip().lower(),
        incorrect_record_id=incorrect_record_id,
        rm_id=rm_id,
        warehouse_id=warehouse_id,
        entered_qty=entered_qty,
        status_id=status_id
    )