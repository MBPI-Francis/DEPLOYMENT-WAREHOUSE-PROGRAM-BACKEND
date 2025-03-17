from fastapi import HTTPException

class TempPreparationFormCreateException(HTTPException):
    def __init__(self, detail="Temp Preparation Form creation failed"):
        super().__init__(status_code=500, detail=detail)

class TempPreparationFormNotFoundException(HTTPException):
    def __init__(self, detail="Temp Preparation Form not found"):
        super().__init__(status_code=404, detail=detail)

class TempPreparationFormUpdateException(HTTPException):
    def __init__(self, detail: str = "Temp Preparation Form update failed"):
        super().__init__(status_code=400, detail=detail)


class TempPreparationFormSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Temp Preparation Form soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class TempPreparationFormRestoreException(HTTPException):
    def __init__(self, detail: str = "Temp Preparation Form restore failed"):
        super().__init__(status_code=400, detail=detail)