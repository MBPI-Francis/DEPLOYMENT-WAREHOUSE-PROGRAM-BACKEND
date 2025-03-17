
from backend.api_auth_users.v1.exceptions import UserAuthNotFoundException
from backend.api_users.v1.main import AppService
from backend.api_auth_users.v1.crud import UserAuth


# These are the code for the business logic like calculation etc.
class AuthUserService(AppService):
    def auth_user(self, user_name: str, password: str):
        try:
            user_item = UserAuth(self.db).auth_user(user_name, password)

        except Exception as e:
            raise UserAuthNotFoundException(detail=f"Error: {str(e)}")
        return user_item


