# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import datetime, date
from typing import List

class StockOnHandBase(BaseModel):
    rm_code_id: UUID
    warehouse_id: UUID
    status_id: Optional[UUID] = None
    rm_soh: float
    stock_recalculation_count: int


class StockOnHandCreate(StockOnHandBase):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None
    description: Optional[str] = None
    
class StockOnHandUpdate(StockOnHandBase):
    rm_soh: Optional[str] = None
    description: Optional[str] = None


class StockOnHandCreateBulk(BaseModel):
    items: List[StockOnHandCreate]


class StockOnHandResponse(StockOnHandBase):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None
    description: Optional[str] = None


    class Config:
        from_attributes = True


# class HistoricalStockOnHandResponse(BaseModel):
#     wh_id: UUID
#     wh_name: str
#     wh_number: int
#     rm_id: UUID
#     rm_code: str
#     qty: float
#     stock_change_date: datetime
#     status_name: str
#     status_id: UUID
#     date_computed: date
#
#     class Config:
#         from_attributes = True

class HistoricalStockOnHandResponse(BaseModel):
    wh_id: UUID
    wh_name: str
    wh_number: Optional[int] # Assuming wh_number might be optional/nullable
    rm_id: UUID
    rm_code: str
    qty: float
    stock_change_date: Optional[datetime] # Assuming this might be optional/nullable
    status_name: Optional[str] # Assuming status_name might be optional/nullable (from outerjoin)
    status_id: Optional[UUID] # Assuming status_id might be optional/nullable (from outerjoin)
    date_computed: datetime

    class Config:
        # For Pydantic v2+, use 'from_attributes = True'
        # For Pydantic v1, use 'orm_mode = True'
        from_attributes = True

