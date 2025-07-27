from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.api_transfer_form.v1.schemas import TempTransferFormCreate, TempTransferFormUpdate, TempTransferFormResponse, TempTransferForm
from backend.api_transfer_form.v1.service import TempTransferFormService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/transfer_forms/v1")

@router.post("/create/", response_model=TempTransferForm)
async def create_transfer_form(transfer_form: TempTransferFormCreate, db: get_db = Depends()):
    result = TempTransferFormService(db).create_transfer_form(transfer_form)
    return result

@router.get("/list/", response_model=list[TempTransferFormResponse])
async def read_transfer_form(db: get_db = Depends()):
    result = TempTransferFormService(db).get_transfer_form()
    return result

@router.get("/list/deleted/", response_model=list[TempTransferFormResponse])
async def read_deleted_transfer_form(db: get_db = Depends()):
    result = TempTransferFormService(db).get_deleted_transfer_form()
    return result



@router.get("/list/historical/", response_model=List[TempTransferFormResponse])
async def read_historical_transfer_form(
    record_id: Optional[UUID] = Query(None, description="Filter by specific record ID"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD) for transfer_date"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD) for transfer_date"),
    rm_code: Optional[str] = Query(None, description="Filter by Raw Material Code (e.g., 'RM001')"),
    from_warehouse_name: Optional[str] = Query(None, description="Filter by From Warehouse Name"),
    to_warehouse_name: Optional[str] = Query(None, description="Filter by To Warehouse Name"),
    status_name: Optional[str] = Query(None, description="Filter by Status Name (e.g., 'Approved')"),
    db: Session = Depends(get_db)
):
    result = TempTransferFormService(db).get_historical_transfer_form(
        record_id=record_id,
        date_from=date_from,
        date_to=date_to,
        rm_code=rm_code,
        from_warehouse_name=from_warehouse_name,
        to_warehouse_name=to_warehouse_name,
        status_name=status_name,
    )
    return result

@router.put("/update/{transfer_form_id}/", response_model=list[TempTransferFormResponse])
async def update_transfer_form(transfer_form_id: UUID, transfer_form_update: TempTransferFormUpdate, db: get_db = Depends()):
    result = TempTransferFormService(db).update_transfer_form(transfer_form_id, transfer_form_update)
    return result

@router.put("/restore/{transfer_form_id}/", response_model=TempTransferFormResponse)
async def restore_transfer_form(transfer_form_id: UUID,  db: get_db = Depends()):
    result = TempTransferFormService(db).restore_transfer_form(transfer_form_id)
    return result

@router.delete("/delete/{transfer_form_id}/", response_model=list[TempTransferFormResponse])
async def delete_transfer_form(transfer_form_id: UUID, db: get_db = Depends()):
    result = TempTransferFormService(db).soft_delete_transfer_form(transfer_form_id)
    return result

