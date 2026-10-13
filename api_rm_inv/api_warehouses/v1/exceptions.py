from fastapi import HTTPException


class WarehouseCreateException(HTTPException):
    def __init__(self, detail="Warehouse creation failed"):
        super().__init__(status_code=500, detail=detail)

class WarehouseNotFoundException(HTTPException):
    def __init__(self, detail="Warehouse not found"):
        super().__init__(status_code=404, detail=detail)


class WarehouseUpdateException(HTTPException):
    def __init__(self, detail: str = "Warehouse update failed"):
        super().__init__(status_code=400, detail=detail)


class WarehouseSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Warehouse soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class WarehouseRestoreException(HTTPException):
    def __init__(self, detail: str = "Warehouse restore failed"):
        super().__init__(status_code=400, detail=detail)