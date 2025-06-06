from fastapi import APIRouter, Depends
from backend.api_adjustment_form.v1_spillage.schemas import AdjustmentFormCreate, AdjustmentFormUpdate, AdjustmentFormResponse, SpillageAdjustmentForm
from backend.api_adjustment_form.v1_spillage.service import AdjustmentFormService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/adjustment_form/spillage/v1")

@router.post("/create/", response_model=SpillageAdjustmentForm)
async def create_adjustment_form(adjustment_form: AdjustmentFormCreate, db: get_db = Depends()):
    result = AdjustmentFormService(db).create_adjustment_form(adjustment_form)
    return result

@router.get("/list/", response_model=list[AdjustmentFormResponse])
async def read_adjustment_form(db: get_db = Depends()):
    result = AdjustmentFormService(db).get_adjustment_form()
    return result

@router.get("/list/deleted/", response_model=list[AdjustmentFormResponse])
async def read_deleted_adjustment_form(db: get_db = Depends()):
    result = AdjustmentFormService(db).get_deleted_adjustment_form()
    return result

@router.get("/list/historical/", response_model=list[AdjustmentFormResponse])
async def read_historical_adjustment_form(db: get_db = Depends()):
    result = AdjustmentFormService(db).get_historical_adjustment_form()
    return result

@router.put("/update/{adjustment_form_id}/", response_model=list[AdjustmentFormResponse])
async def update_adjustment_form(adjustment_form_id: UUID, adjustment_form_update: AdjustmentFormUpdate, db: get_db = Depends()):
    result = AdjustmentFormService(db).update_adjustment_form(adjustment_form_id, adjustment_form_update)
    return result

@router.put("/restore/{adjustment_form_id}/", response_model=AdjustmentFormResponse)
async def restore_adjustment_form(adjustment_form_id: UUID,  db: get_db = Depends()):
    result = AdjustmentFormService(db).restore_adjustment_form(adjustment_form_id)
    return result

@router.delete("/delete/{adjustment_form_id}/", response_model=list[AdjustmentFormResponse])
async def delete_adjustment_form(adjustment_form_id: UUID, db: get_db = Depends()):
    result = AdjustmentFormService(db).soft_delete_adjustment_form(adjustment_form_id)
    return result

