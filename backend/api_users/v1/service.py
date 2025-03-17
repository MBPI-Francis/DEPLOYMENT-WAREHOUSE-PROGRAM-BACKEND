from backend.api_users.v1.exceptions import UserNotFoundException, UserCreateException
from backend.api_users.v1.schemas import UserCreate, UserUpdate
from uuid import UUID
from backend.api_users.v1.crud import UserCRUD
from backend.api_users.v1.main import AppService



# These are the code for the business logic like calculation etc.
class UserService(AppService):
    def create_user(self, item: UserCreate):
        try:
            user_item = UserCRUD(self.db).create_user(item)

        except Exception as e:
            raise UserCreateException(detail=f"Error: {str(e)}")


        return user_item

    def get_user(self):
        try:
            user_item = UserCRUD(self.db).get_user()

        except Exception as e:
            raise UserNotFoundException(detail=f"Error: {str(e)}")
        return user_item

    # This is the service/business logic in updating the department.
    def update_user(self, user_id: UUID, user_update: UserUpdate):
        user = UserCRUD(self.db).update_user(user_id, user_update)
        return user

    # This is the service/business logic in soft deleting the department.
    def deactivate_user(self, user_id: UUID):
        user = UserCRUD(self.db).deactivate_user(user_id)
        return user


    # This is the service/business logic in soft restoring the department.
    def restore_user(self, user_id: UUID):
        user = UserCRUD(self.db).restore_user(user_id)
        return user