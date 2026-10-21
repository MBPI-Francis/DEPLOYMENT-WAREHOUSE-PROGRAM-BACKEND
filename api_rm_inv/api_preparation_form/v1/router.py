"""
API Router for Preparation Form Module.

Provides:
1. Traveler Integration:
   - GET /worksheet
   - GET /by-lot/{prod_lot_no}
   - POST /confirm-and-deduct
2. Ledger Maintenance CRUD:
   - POST /create/
   - GET /list/
   - GET /list/deleted/
   - GET /list/historical/
   - PUT /update/{preparation_form_id}/
   - DELETE /delete/{preparation_form_id}/
   - PUT /restore/{preparation_form_id}/
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_preparation_form.v1.schemas import (
    PrepLookupResponse,
    PrepFormSubmissionRequest,
    PrepSubmissionResponse,
    TempPreparationFormCreate,
    TempPreparationFormUpdate,
    TempPreparationFormResponse,
)
from api_rm_inv.api_preparation_form.v1.service import PrepIntegrationService

router = APIRouter(prefix="/api/v1/rm/preparation-forms", tags=["Preparation Forms"])


# ===========================================================================
# 1. Traveler Integration Endpoints
# ===========================================================================

@router.get(
    "/worksheet",
    response_model=PrepLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Flexible lookup by Lot No, Prep Form No, or Product ID"
)
def get_worksheet(
    prod_lot_no: Optional[str] = Query(None, description="Production Lot Number"),
    prep_form_no: Optional[str] = Query(None, description="Preparation Form Number"),
    prod_id: Optional[str] = Query(None, description="Product Recipe ID"),
    db: Session = Depends(get_db)
):
    """Pulls line items from schema_whprep for the PyQt6 traveler table."""
    service = PrepIntegrationService(db)
    return service.get_worksheet(prod_lot_no=prod_lot_no, prep_form_no=prep_form_no, prod_id=prod_id)


@router.get(
    "/by-lot/{prod_lot_no}",
    response_model=PrepLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct lookup by Lot Number (backward compatible)"
)
def get_worksheet_by_lot(
    prod_lot_no: str,
    db: Session = Depends(get_db)
):
    """Legacy route matching by exact production lot number."""
    service = PrepIntegrationService(db)
    return service.get_worksheet(prod_lot_no=prod_lot_no)


@router.post(
    "/confirm-and-deduct",
    response_model=PrepSubmissionResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm floor actuals and deduct from inventory"
)
def confirm_and_deduct(
    payload: PrepFormSubmissionRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Executes atomic commit updating schema_whprep and inserting into schema_whrm."""
    service = PrepIntegrationService(db)
    return service.confirm_and_deduct_inventory(payload, request, current_user)


# ===========================================================================
# 2. Ledger Maintenance Endpoints
# ===========================================================================

@router.post(
    "/create/",
    response_model=TempPreparationFormResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a preparation deduction entry"
)
def create_preparation_form(
    payload: TempPreparationFormCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a preparation deduction row and records an audit log atomically."""
    service = PrepIntegrationService(db)
    return service.create_preparation_entry(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[Dict[str, Any]],
    summary="List active preparation deduction entries (Paginated)"
)
def read_active_preparation_forms(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated active, non-cleared deduction records."""
    service = PrepIntegrationService(db)
    return service.get_active_preparation_list(limit=limit, offset=offset)


@router.get(
    "/list/deleted/",
    response_model=List[Dict[str, Any]],
    summary="List soft-deleted preparation deduction entries (Paginated)"
)
def read_deleted_preparation_forms(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated soft-deleted records for auditing or restoration."""
    service = PrepIntegrationService(db)
    return service.get_deleted_preparation_list(limit=limit, offset=offset)


@router.get(
    "/list/historical/",
    response_model=List[Dict[str, Any]],
    summary="List historical computed preparation forms (Paginated)"
)
def read_historical_preparation_forms(
    record_id: Optional[str] = Query(None, description="Optional UUID to filter single historical row"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves historical records that have already been computed into ending balances."""
    service = PrepIntegrationService(db)
    return service.get_historical_preparation_list(record_id=record_id, limit=limit, offset=offset)


@router.put(
    "/update/{preparation_form_id}/",
    response_model=TempPreparationFormResponse,
    summary="Update an existing preparation form entry"
)
def update_preparation_form(
    preparation_form_id: UUID,
    payload: TempPreparationFormUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates fields on an existing deduction entry and records an audit log atomically."""
    service = PrepIntegrationService(db)
    return service.update_preparation_entry(preparation_form_id, payload, request, current_user)


@router.delete(
    "/delete/{preparation_form_id}/",
    summary="Soft-delete a preparation form entry"
)
def delete_preparation_form(
    preparation_form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft-deletes an entry and records the audit trail atomically."""
    service = PrepIntegrationService(db)
    return service.soft_delete_preparation_entry(preparation_form_id, request, current_user)


@router.put(
    "/restore/{preparation_form_id}/",
    summary="Restore a soft-deleted preparation form entry"
)
def restore_preparation_form(
    preparation_form_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restores a soft-deleted entry and records the audit trail atomically."""
    service = PrepIntegrationService(db)
    return service.restore_preparation_entry(preparation_form_id, request, current_user)