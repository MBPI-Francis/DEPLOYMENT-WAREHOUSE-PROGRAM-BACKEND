from backend.api_users.v1.exceptions import UserNotFoundException, UserCreateException, \
    UserUpdateException, UserRestoreException, UserDeactivateException
from backend.api_users.v1.models import User
from backend.api_users.v1.schemas import UserCreate, UserUpdate
from uuid import UUID
from backend.api_users.v1.main import AppCRUD


class UserCRUD(AppCRUD):
    def create_user(self, user: UserCreate):
        user_item = User(user_name=user.user_name,
                               first_name=user.first_name,
                               last_name=user.last_name,
                               password=user.password,
                               department_id=user.department_id,
                               created_by_id = user.created_by_id,
                               updated_by_id = user.updated_by_id,
                                is_superuser=user.is_superuser,
                                is_reguser=user.is_reguser
                                 )
        self.db.add(user_item)
        self.db.commit()
        self.db.refresh(user_item)
        return user_item

    def get_user(self):
        user_item = self.db.query(User).all()
        if user_item:
            return user_item
        return []


    def update_user(self, user_id: UUID, user_update: UserUpdate):
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_active:
                raise UserNotFoundException(detail="User not found or deactivated.")

            for key, value in user_update.dict(exclude_unset=True).items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
            return user

        except Exception as e:
            raise UserUpdateException(detail=f"Error: {str(e)}")

    def deactivate_user(self, user_id: UUID):
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or user.is_active:
                raise UserNotFoundException(detail="User not found or already deactivated.")

            user.is_active = False
            self.db.commit()
            self.db.refresh(user)
            return user

        except Exception as e:
            raise UserDeactivateException(detail=f"Error: {str(e)}")


    def restore_user(self, user_id: UUID):
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or user.is_active:
                raise UserNotFoundException(detail="User not found or already in active state.")

            user.is_active = True
            self.db.commit()
            self.db.refresh(user)
            return user

        except Exception as e:
            raise UserRestoreException(detail=f"Error: {str(e)}")
