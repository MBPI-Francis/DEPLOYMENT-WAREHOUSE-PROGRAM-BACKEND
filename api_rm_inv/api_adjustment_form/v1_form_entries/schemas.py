# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import date, datetime



class AdjustmentForm(BaseModel):

    # Common fields for all the forms
    ref_number: str = Field(max_length=50, description="The reference number of the Adjustment Form")
    adjustment_date: date
    referenced_date: date
    adjustment_type: str = Field(max_length=50, description="The type of adjustment")
    responsible_person: Optional[str] = None


    # Fields for both Receiving and Outgoing Form
    rm_code_id: UUID
    warehouse_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    qty_kg: Optional[float] = None

    # Fields for Preparation Form
    qty_prepared: Optional[float] = None
    qty_return: Optional[float] = None

    # Fields for Transfer Form
    from_warehouse_id: Optional[UUID] = None
    to_warehouse_id: Optional[UUID] = None


    # Fields for Change Status Form
    current_status_id: Optional[UUID] = None
    new_status_id: Optional[UUID] = None


    # FORM IDs
    incorrect_receiving_id: Optional[UUID] = None
    incorrect_outgoing_id: Optional[UUID] = None
    incorrect_preparation_id: Optional[UUID] = None
    incorrect_transfer_id: Optional[UUID] = None
    incorrect_change_status_id: Optional[UUID] = None

class AdjustmentFormCreate(AdjustmentForm):
    created_by_id: Optional[UUID] = None
    updated_by_id: Optional[UUID] = None


class AdjustmentFormUpdate(AdjustmentForm):
    pass


class AdjustmentFormResponse(BaseModel):
    id: UUID
    adjustment_parent_id: UUID
    incorrect_preparation_id: Optional[UUID] = None
    incorrect_receiving_id: Optional[UUID] = None
    incorrect_outgoing_id: Optional[UUID] = None
    incorrect_transfer_id: Optional[UUID] = None
    incorrect_change_status_id: Optional[UUID] = None

    ref_number: str
    adjustment_type: str
    responsible_person: Optional[str] = None
    raw_material: str
    qty_kg: Optional[float] = None

    qty_prepared: Optional[float] = None
    qty_return: Optional[float] = None



    wh_name: Optional[str] = None
    from_warehouse: Optional[str] = None
    to_warehouse: Optional[str] = None

    status: Optional[str] = None
    current_status: Optional[str] = None
    new_status: Optional[str] = None


    adjustment_date: date
    referenced_date: date


    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    date_computed: Optional[date] = None


    class Config:
        from_attributes = True
