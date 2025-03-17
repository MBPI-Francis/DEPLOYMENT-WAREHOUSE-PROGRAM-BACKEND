from fastapi import HTTPException


class UserAuthException(HTTPException):
    def __init__(self, detail="User authentication failed"):
        super().__init__(status_code=500, detail=detail)

class UserAuthNotFoundException(HTTPException):
    def __init__(self, detail="Login credential doesn't exist. Please enter a valid login credentials"):
        super().__init__(status_code=404, detail=detail)

class UserAuthDeactivatedException(HTTPException):
    def __init__(self, detail="The user account is currently in inactive state. Please contact the system admin for reactivation of the acccount"):
        super().__init__(status_code=404, detail=detail)