from fastapi import HTTPException


class UserCreateException(HTTPException):
    def __init__(self, detail="User creation failed"):
        super().__init__(status_code=500, detail=detail)

class UserNotFoundException(HTTPException):
    def __init__(self, detail="User not found"):
        super().__init__(status_code=404, detail=detail)


class UserUpdateException(HTTPException):
    def __init__(self, detail: str = "User update failed"):
        super().__init__(status_code=400, detail=detail)


class UserDeactivateException(HTTPException):
    def __init__(self, detail: str = "User deactivation failed"):
        super().__init__(status_code=400, detail=detail)


class UserRestoreException(HTTPException):
    def __init__(self, detail: str = "User restoration failed"):
        super().__init__(status_code=400, detail=detail)