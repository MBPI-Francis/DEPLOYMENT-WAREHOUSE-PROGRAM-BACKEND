"""
Pydantic Schemas for Inventory Reports.

Provides serialization and commercial 2-decimal rounding for form entry ledgers
and audit trail logs across all warehouse transaction types.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _quantize_two_places(value: Optional[Decimal]) -> Optional[Decimal]:
    """Rounds values to exactly 2 decimal places using half-up commercial rounding."""
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class FormEntryResponse(BaseModel):
    """
    Unified representation of a transaction ledger entry across all forms:
    Receiving, Outgoing, Preparation, Transfers, Change Status, and Adjustments.
    """
    model_config = ConfigDict(from_attributes=True, coerce_numbers_to_str=True)

    date_encoded: date = Field(..., description="Date record was created in the system")
    date_reported: date = Field(..., description="Physical transaction date reported on the paper form")
    document_type: str = Field(..., description="Originating document type (e.g. 'receiving_form_report')")
    document_number: str = Field(..., description="Document tracking reference number")
    mat_code: str = Field(..., description="Raw material code")
    qty: Decimal = Field(..., description="Quantity delta (positive for stock added, negative for stock deducted)")
    whse_no: str = Field(..., description="Warehouse facility identifier")
    status: str = Field(..., description="Quality status classification")

    @field_validator("qty", mode="before")
    @classmethod
    def round_qty(cls, v):
        return _quantize_two_places(v)