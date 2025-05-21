from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api_transfer_form.v1.schemas import TempTransferFormCreate, TempTransferFormUpdate, TempTransferFormResponse, TempTransferForm
from backend.api_transfer_form.v1.service import TempTransferFormService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/transfer_forms/v1_spillage")

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

@router.get("/list/historical/", response_model=list[TempTransferFormResponse])
async def read_historical_transfer_form(db: get_db = Depends()):
    result = TempTransferFormService(db).get_historical_transfer_form()
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

