from typing import Optional

from fastapi import APIRouter, Depends
from backend.api_supplies_outgoing_report.v1.schemas import SuppliesOutgoingFormCreate, SuppliesOutgoingFormUpdate, SuppliesOutgoingFormResponse, SuppliesOutgoingForm
from backend.api_supplies_outgoing_report.v1.service import SuppliesOutgoingFormService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/supplies_outgoing_reports/v1")

@router.post("/create/", response_model=SuppliesOutgoingForm)
async def create_outgoing_report(outgoing_report: SuppliesOutgoingFormCreate, db: get_db = Depends()):
    result = SuppliesOutgoingFormService(db).create_outgoing_report(outgoing_report)
    return result

@router.get("/list/", response_model=list[SuppliesOutgoingFormResponse])
async def read_outgoing_report(db: get_db = Depends()):
    result = SuppliesOutgoingFormService(db).get_outgoing_report()
    return result

@router.get("/list/deleted/", response_model=list[SuppliesOutgoingFormResponse])
async def read_deleted_outgoing_report(db: get_db = Depends()):
    result = SuppliesOutgoingFormService(db).get_deleted_outgoing_report()
    return result

@router.get("/list/historical/", response_model=list[SuppliesOutgoingFormResponse])
async def read_historical_outgoing_report(record_id: Optional[str] = None, db: get_db = Depends()):
    result = SuppliesOutgoingFormService(db).get_historical_outgoing_report(record_id)
    return result

@router.put("/update/{outgoing_report_id}/", response_model=list[SuppliesOutgoingFormResponse])
async def update_outgoing_report(outgoing_report_id: UUID, outgoing_report_update: SuppliesOutgoingFormUpdate, db: get_db = Depends()):
    result = SuppliesOutgoingFormService(db).update_outgoing_report(outgoing_report_id, outgoing_report_update)
    return result

@router.put("/restore/{outgoing_report_id}/", response_model=SuppliesOutgoingFormResponse)
async def restore_outgoing_report(outgoing_report_id: UUID,  db: get_db = Depends()):
    result = SuppliesOutgoingFormService(db).restore_outgoing_report(outgoing_report_id)
    return result

@router.delete("/delete/{outgoing_report_id}/", response_model=list[SuppliesOutgoingFormResponse])
async def delete_outgoing_report(outgoing_report_id: UUID, db: get_db = Depends()):
    result = SuppliesOutgoingFormService(db).soft_delete_outgoing_report(outgoing_report_id)
    return result

