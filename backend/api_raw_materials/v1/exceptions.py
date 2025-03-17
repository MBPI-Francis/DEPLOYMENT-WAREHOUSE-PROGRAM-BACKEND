from fastapi import HTTPException


class RawMaterialCreateException(HTTPException):
    def __init__(self, detail="Raw Material creation failed"):
        super().__init__(status_code=500, detail=detail)

class RawMaterialNotFoundException(HTTPException):
    def __init__(self, detail="Raw Material not found"):
        super().__init__(status_code=404, detail=detail)


class RawMaterialUpdateException(HTTPException):
    def __init__(self, detail: str = "Raw Material update failed"):
        super().__init__(status_code=400, detail=detail)


class RawMaterialSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Raw Material soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class RawMaterialRestoreException(HTTPException):
    def __init__(self, detail: str = "Raw Material restore failed"):
        super().__init__(status_code=400, detail=detail)