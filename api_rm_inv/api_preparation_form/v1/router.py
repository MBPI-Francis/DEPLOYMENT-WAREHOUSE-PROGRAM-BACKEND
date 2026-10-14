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

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from api_rm_inv.api_preparation_form.v1.schemas import (
    PrepLookupResponse,
    PrepFormSubmissionRequest,
    PrepSubmissionResponse,
    TempPreparationFormCreate,
    TempPreparationFormUpdate,
    TempPreparationFormResponse,
)
from api_rm_inv.api_preparation_form.v1.service import PrepIntegrationService

# Note: Mounting both prefixes ensures zero downtime for legacy desktop clients
router = APIRouter(prefix="/api/v1/rm/preparation-forms", tags=["Preparation Forms"])


# ===========================================================================
# 1. Traveler Integration Endpoints (Preserved Exactly As Working)
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
    db: Session = Depends(get_db)
):
    """Executes atomic commit updating schema_whprep and inserting into schema_whrm."""
    service = PrepIntegrationService(db)
    return service.confirm_and_deduct_inventory(payload)


# ===========================================================================
# 2. Ledger Maintenance Endpoints (Restored & Upgraded CRUD)
# ===========================================================================

@router.post(
    "/create/",
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a preparation deduction entry"
)
def create_preparation_form(
    payload: TempPreparationFormCreate,
    db: Session = Depends(get_db)
):
    """Creates a preparation deduction row. Accepts human codes (rm_code, wh_number, status_name)."""
    service = PrepIntegrationService(db)
    result = service.create_preparation_entry(payload)
    return {"message": "Preparation deduction recorded successfully.", "id": result.id, "ref_number": result.ref_number}


@router.get(
    "/list/",
    response_model=List[TempPreparationFormResponse],
    summary="List active preparation deduction entries"
)
def read_active_preparation_forms(db: Session = Depends(get_db)):
    """Retrieves all active, non-cleared deduction records for desktop preparation tables."""
    service = PrepIntegrationService(db)
    return service.get_active_preparation_list()


@router.get(
    "/list/deleted/",
    response_model=List[TempPreparationFormResponse],
    summary="List soft-deleted preparation deduction entries"
)
def read_deleted_preparation_forms(db: Session = Depends(get_db)):
    """Retrieves all soft-deleted records for auditing or restoration."""
    service = PrepIntegrationService(db)
    return service.get_deleted_preparation_list()


@router.get(
    "/list/historical/",
    response_model=List[TempPreparationFormResponse],
    summary="List historical computed preparation forms"
)
def read_historical_preparation_forms(
    record_id: Optional[str] = Query(None, description="Optional UUID to filter single historical row"),
    db: Session = Depends(get_db)
):
    """Retrieves historical records that have already been computed into ending balances."""
    service = PrepIntegrationService(db)
    return service.get_historical_preparation_list(record_id)


@router.put(
    "/update/{preparation_form_id}/",
    response_model=List[TempPreparationFormResponse],
    summary="Update an existing preparation form entry"
)
def update_preparation_form(
    preparation_form_id: UUID,
    payload: TempPreparationFormUpdate,
    db: Session = Depends(get_db)
):
    """Updates fields on an existing deduction entry and returns the refreshed active list."""
    service = PrepIntegrationService(db)
    return service.update_preparation_entry(preparation_form_id, payload)


@router.delete(
    "/delete/{preparation_form_id}/",
    response_model=List[TempPreparationFormResponse],
    summary="Soft-delete a preparation form entry"
)
def delete_preparation_form(
    preparation_form_id: UUID,
    db: Session = Depends(get_db)
):
    """Soft-deletes an entry and returns the refreshed active list."""
    service = PrepIntegrationService(db)
    return service.soft_delete_preparation_entry(preparation_form_id)


@router.put(
    "/restore/{preparation_form_id}/",
    response_model=List[TempPreparationFormResponse],
    summary="Restore a soft-deleted preparation form entry"
)
def restore_preparation_form(
    preparation_form_id: UUID,
    db: Session = Depends(get_db)
):
    """Restores a soft-deleted entry and returns the refreshed active list."""
    service = PrepIntegrationService(db)
    return service.restore_preparation_entry(preparation_form_id)