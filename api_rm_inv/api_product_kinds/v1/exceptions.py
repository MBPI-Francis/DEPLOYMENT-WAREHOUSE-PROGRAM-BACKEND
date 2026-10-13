from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi import HTTPException


class ProductKindCreateException(HTTPException):
    def __init__(self, detail="Product Kind creation failed"):
        super().__init__(status_code=500, detail=detail)

class ProductKindNotFoundException(HTTPException):
    def __init__(self, detail="Product Kind not found"):
        super().__init__(status_code=404, detail=detail)


class ProductKindUpdateException(HTTPException):
    def __init__(self, detail: str = "Product Kind update failed"):
        super().__init__(status_code=400, detail=detail)


class ProductKindSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Product Kind soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class ProductKindRestoreException(HTTPException):
    def __init__(self, detail: str = "Product Kind restore failed"):
        super().__init__(status_code=400, detail=detail)