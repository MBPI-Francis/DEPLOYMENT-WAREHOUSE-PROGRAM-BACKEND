from typing import Optional

from fastapi import APIRouter, Depends
from backend.api_preparation_form.v1.schemas import TempPreparationFormCreate, TempPreparationFormUpdate, TempPreparationFormResponse, TempPreparationForm
from backend.api_preparation_form.v1.service import TempPreparationFormService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/preparation_forms/v1")

@router.post("/create/", response_model=TempPreparationForm)
async def create_preparation_form(preparation_form: TempPreparationFormCreate, db: get_db = Depends()):
    result = TempPreparationFormService(db).create_preparation_form(preparation_form)
    return result

@router.get("/list/", response_model=list[TempPreparationFormResponse])
async def read_preparation_form(db: get_db = Depends()):
    result = TempPreparationFormService(db).get_preparation_form()
    return result

@router.get("/list/deleted/", response_model=list[TempPreparationFormResponse])
async def read_deleted_preparation_form(db: get_db = Depends()):
    result = TempPreparationFormService(db).get_deleted_preparation_form()
    return result

@router.get("/list/historical/", response_model=list[TempPreparationFormResponse])
async def read_historical_preparation_form(record_id: Optional[str] = None, db: get_db = Depends()):
    result = TempPreparationFormService(db).get_historical_preparation_form(record_id)
    return result

@router.put("/update/{preparation_form_id}/", response_model=list[TempPreparationFormResponse])
async def update_preparation_form(preparation_form_id: UUID, preparation_form_update: TempPreparationFormUpdate, db: get_db = Depends()):
    result = TempPreparationFormService(db).update_preparation_form(preparation_form_id, preparation_form_update)
    return result

@router.put("/restore/{preparation_form_id}/", response_model=TempPreparationFormResponse)
async def restore_preparation_form(preparation_form_id: UUID,  db: get_db = Depends()):
    result = TempPreparationFormService(db).restore_preparation_form(preparation_form_id)
    return result

@router.delete("/delete/{preparation_form_id}/", response_model=list[TempPreparationFormResponse])
async def delete_preparation_form(preparation_form_id: UUID, db: get_db = Depends()):
    result = TempPreparationFormService(db).soft_delete_preparation_form(preparation_form_id)
    return result

