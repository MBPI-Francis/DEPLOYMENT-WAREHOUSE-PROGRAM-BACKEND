"""
API Router for Inventory Reports and Excel Exports.

All endpoints use synchronous 'def' so heavy database queries and Excel generation
run in FastAPI's worker thread pool, preventing LAN request stalls.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_reports.v1.schemas import FormEntryResponse
from api_rm_inv.api_reports.v1.service import FormEntryService

router = APIRouter(prefix="/api/v1/rm/reports", tags=["Reports"])


@router.get(
    "/form-entries/",
    response_model=List[Dict[str, Any]],
    summary="List unified form entries log (Paginated)"
)
def get_form_entries(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    mat_code: Optional[str] = Query(None, description="Material Code (or 'all')"),
    document_type: Optional[str] = Query(None, description="Document Type (e.g. 'receiving_form_report')"),
    location: Optional[str] = Query(None, description="Warehouse Number/Name (or 'all')"),
    status: Optional[str] = Query(None, description="Quality Status (or 'all')"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip for pagination"),
    db: Session = Depends(get_db)
):
    """
    Queries schema_whrm.view_form_entries_log with multi-field filtering
    and pagination to maintain fast response times on large ledgers.
    """
    service = FormEntryService(db)
    return service.get_form_entries(
        date_from=date_from,
        date_to=date_to,
        mat_code=mat_code,
        document_type=document_type,
        location=location,
        status=status,
        limit=limit,
        offset=offset
    )


@router.get(
    "/form-entries/export-to-file/",
    summary="Export form entries and automated daily pivot summary to Excel (.xlsx)"
)
def export_form_entries_to_file(
    request: Request,
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    mat_code: Optional[str] = Query(None, description="Material Code"),
    document_type: Optional[str] = Query(None, description="Document Type"),
    location: Optional[str] = Query(None, description="Warehouse Location"),
    status: Optional[str] = Query(None, description="Quality Status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Streams an automated two-sheet Excel file (.xlsx) with constant-memory optimization:
    - Sheet 1: Detailed individual transaction entries.
    - Sheet 2: Daily Material Pivot Table summarizing net movements by day.
    """
    service = FormEntryService(db)
    excel_buffer = service.export_form_entries_to_excel_file(
        request=request,
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        mat_code=mat_code,
        document_type=document_type,
        location=location,
        status=status,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Warehouse_Movement_Report_{timestamp}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )