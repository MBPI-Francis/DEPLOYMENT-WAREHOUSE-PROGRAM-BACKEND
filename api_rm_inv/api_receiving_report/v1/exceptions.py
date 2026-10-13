from fastapi import HTTPException


class TempReceivingReportCreateException(HTTPException):
    def __init__(self, detail="Temp Receiving Report creation failed"):
        super().__init__(status_code=500, detail=detail)

class TempReceivingReportNotFoundException(HTTPException):
    def __init__(self, detail="Temp Receiving Report not found"):
        super().__init__(status_code=404, detail=detail)

class TempReceivingReportUpdateException(HTTPException):
    def __init__(self, detail: str = "Temp Receiving Report update failed"):
        super().__init__(status_code=400, detail=detail)


class TempReceivingReportSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Temp Receiving Report soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class TempReceivingReportRestoreException(HTTPException):
    def __init__(self, detail: str = "Temp Receiving Report restore failed"):
        super().__init__(status_code=400, detail=detail)