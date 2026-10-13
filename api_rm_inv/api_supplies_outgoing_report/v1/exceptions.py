from fastapi import HTTPException


class SuppliesOutgoingReportCreateException(HTTPException):
    def __init__(self, detail="Supplies Outgoing Report creation failed"):
        super().__init__(status_code=500, detail=detail)

class SuppliesOutgoingReportNotFoundException(HTTPException):
    def __init__(self, detail="Supplies Outgoing Report not found"):
        super().__init__(status_code=404, detail=detail)

class SuppliesOutgoingReportUpdateException(HTTPException):
    def __init__(self, detail: str = "Supplies Outgoing Report update failed"):
        super().__init__(status_code=400, detail=detail)


class SuppliesOutgoingReportSoftDeleteException(HTTPException):
    def __init__(self, detail: str = "Supplies Outgoing Report soft delete failed"):
        super().__init__(status_code=400, detail=detail)


class SuppliesOutgoingReportRestoreException(HTTPException):
    def __init__(self, detail: str = "Supplies Outgoing Report restore failed"):
        super().__init__(status_code=400, detail=detail)