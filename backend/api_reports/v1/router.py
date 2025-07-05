from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.api_reports.v1.service import FormEntryService
from backend.api_reports.v1.schemas import FormEntryResponse
from backend.settings.database import get_db

router = APIRouter(prefix="/reports/v1")


@router.get("/form-entries/", response_model=List[FormEntryResponse])
def get_form_entries(
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    mat_code: Optional[str] = Query(None, description="Material Code (or 'all')"),
    document_type: Optional[str] = Query(None, description="Document Type (or 'all')"),
    db: Session = Depends(get_db)
):
    result = FormEntryService(db).get_form_entries(
        date_from=date_from,
        date_to=date_to,
        mat_code=mat_code,
        document_type=document_type,
    )

    return result