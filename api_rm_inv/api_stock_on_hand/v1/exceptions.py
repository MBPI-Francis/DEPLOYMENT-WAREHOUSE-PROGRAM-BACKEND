from fastapi import HTTPException


class StockOnHandCreateException(HTTPException):
    def __init__(self, detail="Raw Material' SOH creation failed"):
        super().__init__(status_code=500, detail=detail)

class StockOnHandNotFoundException(HTTPException):
    def __init__(self, detail="Raw Material' SOH not found"):
        super().__init__(status_code=404, detail=detail)


class StockOnHandUpdateException(HTTPException):
    def __init__(self, detail: str = "Raw Material' SOH update failed"):
        super().__init__(status_code=400, detail=detail)


class StockOnHandSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Raw Material' SOH soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class StockOnHandRestoreException(HTTPException):
    def __init__(self, detail: str = "Raw Material' SOH restore failed"):
        super().__init__(status_code=400, detail=detail)