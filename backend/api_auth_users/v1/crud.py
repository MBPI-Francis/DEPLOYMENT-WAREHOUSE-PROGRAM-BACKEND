from backend.api_auth_users.v1.exceptions import UserAuthNotFoundException, UserAuthDeactivatedException
from backend.api_users.v1.models import User
from backend.api_users.v1.main import AppCRUD, AppService

class UserAuth(AppCRUD):
    def auth_user(self, user_name: str, password: str):
        try:
            user = self.db.query(User).filter(User.user_name == user_name, User.password == password).first()
            if user.is_active:
                return user
            else:
                raise UserAuthDeactivatedException(detail="The user account is deactivated. Please talk to the system admin if this is a problem.")
        except:
            raise UserAuthNotFoundException()

