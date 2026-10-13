from fastapi import HTTPException


class AdjustmentFormCreateException(HTTPException):
    def __init__(self, detail="Adjustment Form Record creation failed"):
        super().__init__(status_code=500, detail=detail)

class AdjustmentFormNotFoundException(HTTPException):
    def __init__(self, detail="Adjustment Form Record not found"):
        super().__init__(status_code=404, detail=detail)

class AdjustmentFormUpdateException(HTTPException):
    def __init__(self, detail: str = "Adjustment Form Record update failed"):
        super().__init__(status_code=400, detail=detail)


class AdjustmentFormSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Adjustment Form Record soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class AdjustmentFormRestoreException(HTTPException):
    def __init__(self, detail: str = "Adjustment Form Record restore failed"):
        super().__init__(status_code=400, detail=detail)