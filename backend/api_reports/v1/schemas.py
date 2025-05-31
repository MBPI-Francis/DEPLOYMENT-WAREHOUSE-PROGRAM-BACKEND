# Schemas serialize and validate data. Below are the codes for defining Pydantic Schemas

from pydantic import BaseModel
from decimal import Decimal


class DeviationReportResponse(BaseModel):
    rm: str
    francis_qty: Decimal
    jarick_qty: Decimal
    deviation: Decimal


