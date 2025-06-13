from typing import Optional

from fastapi import APIRouter, Depends
from backend.api_outgoing_report.v1.schemas import OutgoingFormCreate, OutgoingFormUpdate, OutgoingFormResponse, OutgoingForm
from backend.api_outgoing_report.v1.service import TempOutgoingReportService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/outgoing_reports/v1")

@router.post("/create/", response_model=OutgoingForm)
async def create_outgoing_report(outgoing_report: OutgoingFormCreate, db: get_db = Depends()):
    result = TempOutgoingReportService(db).create_outgoing_report(outgoing_report)
    return result

@router.get("/list/", response_model=list[OutgoingFormResponse])
async def read_outgoing_report(db: get_db = Depends()):
    result = TempOutgoingReportService(db).get_outgoing_report()
    return result

@router.get("/list/deleted/", response_model=list[OutgoingFormResponse])
async def read_deleted_outgoing_report(db: get_db = Depends()):
    result = TempOutgoingReportService(db).get_deleted_outgoing_report()
    return result

@router.get("/list/historical/", response_model=list[OutgoingFormResponse])
async def read_historical_outgoing_report(record_id: Optional[str] = None, db: get_db = Depends()):
    result = TempOutgoingReportService(db).get_historical_outgoing_report(record_id)
    return result

@router.put("/update/{outgoing_report_id}/", response_model=list[OutgoingFormResponse])
async def update_outgoing_report(outgoing_report_id: UUID, outgoing_report_update: OutgoingFormUpdate, db: get_db = Depends()):
    result = TempOutgoingReportService(db).update_outgoing_report(outgoing_report_id, outgoing_report_update)
    return result

@router.put("/restore/{outgoing_report_id}/", response_model=OutgoingFormResponse)
async def restore_outgoing_report(outgoing_report_id: UUID,  db: get_db = Depends()):
    result = TempOutgoingReportService(db).restore_outgoing_report(outgoing_report_id)
    return result

@router.delete("/delete/{outgoing_report_id}/", response_model=list[OutgoingFormResponse])
async def delete_outgoing_report(outgoing_report_id: UUID, db: get_db = Depends()):
    result = TempOutgoingReportService(db).soft_delete_outgoing_report(outgoing_report_id)
    return result

