from fastapi import HTTPException


class TempOutgoingReportCreateException(HTTPException):
    def __init__(self, detail="Temp Outgoing Report creation failed"):
        super().__init__(status_code=500, detail=detail)

class TempOutgoingReportNotFoundException(HTTPException):
    def __init__(self, detail="Temp Outgoing Report not found"):
        super().__init__(status_code=404, detail=detail)

class TempOutgoingReportUpdateException(HTTPException):
    def __init__(self, detail: str = "Temp Outgoing Report update failed"):
        super().__init__(status_code=400, detail=detail)


class TempOutgoingReportSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Temp Outgoing Report soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class TempOutgoingReportRestoreException(HTTPException):
    def __init__(self, detail: str = "Temp Outgoing Report restore failed"):
        super().__init__(status_code=400, detail=detail)