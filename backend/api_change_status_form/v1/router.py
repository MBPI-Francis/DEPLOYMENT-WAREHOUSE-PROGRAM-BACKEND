from fastapi import APIRouter, Depends
from backend.api_change_status_form.v1.schemas import TempHeldFormCreate, TempHeldFormUpdate, TempHeldFormResponse, TempHeldForm
from backend.api_change_status_form.v1.service import TempHeldFormService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/change_status_form/v1_spillage")

@router.post("/create/", response_model=TempHeldForm)
async def create_held_form(held_form: TempHeldFormCreate, db: get_db = Depends()):
    result = TempHeldFormService(db).create_held_form(held_form)
    return result

@router.get("/list/", response_model=list[TempHeldFormResponse])
async def read_held_form(db: get_db = Depends()):
    result = TempHeldFormService(db).get_held_form()
    return result


@router.get("/list/deleted/", response_model=list[TempHeldFormResponse])
async def read_deleted_held_form(db: get_db = Depends()):
    result = TempHeldFormService(db).get_deleted_held_form()
    return result


@router.get("/list/historical/", response_model=list[TempHeldFormResponse])
async def read_historical_held_form(db: get_db = Depends()):
    result = TempHeldFormService(db).get_historical_held_form()
    return result

@router.put("/update/{held_form_id}/", response_model=list[TempHeldFormResponse])
async def update_held_form(held_form_id: UUID, held_form_update: TempHeldFormUpdate, db: get_db = Depends()):
    result = TempHeldFormService(db).update_held_form(held_form_id, held_form_update)
    return result

@router.put("/restore/{held_form_id}/", response_model=TempHeldFormResponse)
async def restore_held_form(held_form_id: UUID,  db: get_db = Depends()):
    result = TempHeldFormService(db).restore_held_form(held_form_id)
    return result

@router.delete("/delete/{held_form_id}/", response_model=list[TempHeldFormResponse])
async def delete_held_form(held_form_id: UUID, db: get_db = Depends()):
    result = TempHeldFormService(db).soft_delete_held_form(held_form_id)
    return result

