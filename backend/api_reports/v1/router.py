# from fastapi import APIRouter, Depends, Query
# from sqlalchemy.orm import Session
# from typing import List, Optional
# from backend.api_reports.v1.service import FormEntryService
# from backend.api_reports.v1.schemas import FormEntryResponse
# from backend.settings.database import get_db
#
# router = APIRouter(prefix="/api/reports/v1")
#
#
# @router.get("/form-entries/", response_model=List[FormEntryResponse])
# def get_form_entries(
#     date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
#     date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
#     mat_code: Optional[str] = Query(None, description="Material Code (or 'all')"),
#     document_type: Optional[str] = Query(None, description="Document Type (or 'all')"),
#     location: Optional[str] = Query(None, description="Warehouse Location (or 'all')"),
#     status: Optional[str] = Query(None, description="Raw Material Status (or 'all')"),
#     db: Session = Depends(get_db)
# ):
#     result = FormEntryService(db).get_form_entries(
#         date_from=date_from,
#         date_to=date_to,
#         mat_code=mat_code,
#         document_type=document_type,
#         location=location,
#         status=status
#     )
#
#     return result
#
# @router.get("/form-entries/export-to-file/")
# def export_form_entries_to_file(
#     date_from: Optional[str] = Query(None),
#     date_to: Optional[str] = Query(None),
#     mat_code: Optional[str] = Query(None),
#     document_type: Optional[str] = Query(None),
#     location: Optional[str] = Query(None),
#     status: Optional[str] = Query(None),
#     db: Session = Depends(get_db),
# ):
#     file_path = FormEntryService(db).export_form_entries_to_excel_file(
#         date_from=date_from,
#         date_to=date_to,
#         mat_code=mat_code,
#         document_type=document_type,
#         location=location,
#         status=status,
#     )
#
#     return {"message": "Exported successfully", "file_path": file_path}


from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.api_reports.v1.service import FormEntryService
from backend.api_reports.v1.schemas import FormEntryResponse
from backend.settings.database import get_db
from fastapi.responses import StreamingResponse # Import StreamingResponse
from starlette.background import BackgroundTask # Potentially useful for cleanup (though BytesIO often handles itself)
from datetime import datetime # For filename suggestion

router = APIRouter(prefix="/api/reports/v1")


@router.get("/form-entries/", response_model=List[FormEntryResponse])
def get_form_entries(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    mat_code: Optional[str] = Query(None, description="Material Code (or 'all')"),
    document_type: Optional[str] = Query(None, description="Document Type (or 'all')"),
    location: Optional[str] = Query(None, description="Warehouse Location (or 'all')"),
    status: Optional[str] = Query(None, description="Raw Material Status (or 'all')"),
    db: Session = Depends(get_db)
):
    result = FormEntryService(db).get_form_entries(
        date_from=date_from,
        date_to=date_to,
        mat_code=mat_code,
        document_type=document_type,
        location=location,
        status=status
    )

    return result

@router.get("/form-entries/export-to-file/")
def export_form_entries_to_file(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    mat_code: Optional[str] = Query(None),
    document_type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    excel_buffer = FormEntryService(db).export_form_entries_to_excel_file(
        date_from=date_from,
        date_to=date_to,
        mat_code=mat_code,
        document_type=document_type,
        location=location,
        status=status,
    )

    # Suggest a filename to the client
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Warehouse_Report_{timestamp}.xlsx"

    return StreamingResponse(
        excel_buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
        # You can add a BackgroundTask here if you need to close the buffer,
        # though BytesIO often handles itself when the response is consumed.
        # background=BackgroundTask(excel_buffer.close)
    )
