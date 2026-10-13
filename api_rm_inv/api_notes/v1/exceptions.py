from fastapi import HTTPException


class NotesCreateException(HTTPException):
    def __init__(self, detail="Temporary Notes creation failed"):
        super().__init__(status_code=500, detail=detail)

class NotesNotFoundException(HTTPException):
    def __init__(self, detail="Temporary Notes not found"):
        super().__init__(status_code=404, detail=detail)


class NotesUpdateException(HTTPException):
    def __init__(self, detail: str = "Temporary Notes update failed"):
        super().__init__(status_code=400, detail=detail)


class NotesSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Temporary Notes soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class NotesRestoreException(HTTPException):
    def __init__(self, detail: str = "Temporary Notes restore failed"):
        super().__init__(status_code=400, detail=detail)