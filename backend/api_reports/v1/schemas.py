
from pydantic import BaseModel
from typing import Optional
from datetime import date


class FormEntryResponse(BaseModel):
    date_encoded: date
    date_reported: date
    document_type: str
    document_number: str
    mat_code: str
    qty: float
    whse_no: str
    status: str
    is_deleted: Optional[bool]
    is_cleared: Optional[bool]
    is_computed: str

    class Config:
        from_attributes = True