from fastapi import HTTPException


class TempHeldFormCreateException(HTTPException):
    def __init__(self, detail="Held Form creation failed"):
        super().__init__(status_code=500, detail=detail)

class TempHeldFormNotFoundException(HTTPException):
    def __init__(self, detail="Held Form not found"):
        super().__init__(status_code=404, detail=detail)

class TempHeldFormUpdateException(HTTPException):
    def __init__(self, detail: str = "Held Form update failed"):
        super().__init__(status_code=400, detail=detail)


class TempHeldFormSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Held Form soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class TempHeldFormRestoreException(HTTPException):
    def __init__(self, detail: str = "Held Form restore failed"):
        super().__init__(status_code=400, detail=detail)