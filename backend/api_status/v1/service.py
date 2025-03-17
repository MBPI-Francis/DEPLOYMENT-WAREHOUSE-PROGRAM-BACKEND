from backend.api_status.v1.exceptions import StatusCreateException, StatusNotFoundException, \
    StatusUpdateException, StatusSoftDeleteException, StatusRestoreException
from backend.api_status.v1.main import AppCRUD, AppService
from backend.api_status.v1.models import Status
from backend.api_status.v1.schemas import StatusCreate, StatusUpdate
from backend.api_users.v1.models import User
from sqlalchemy.sql import func
from uuid import UUID


# These are the code for the app to communicate to the database
class StatusCRUD(AppCRUD):
    def create_status(self, status: StatusCreate):
        status_item = Status(name=status.name,
                                   description=status.description,
                                   updated_by_id=status.updated_by_id,
                                   created_by_id=status.created_by_id)
        self.db.add(status_item)
        self.db.commit()
        self.db.refresh(status_item)
        return status_item

    def get_status(self):
        status_item = self.db.query(Status).all()
        if status_item:
            return status_item
        return []

    # FIX THIS ERROR. THIS HAS ERROR
    def get_status_by_name(self, name):
        status = (
            self.db.query(Status.id, Status.name)
            .filter(Status.name == name)
            .first()
        )

        if status:
            # Filter only required fields
            filtered_status = {
                "id": status.id,
                "name": status.name,
            }

            return filtered_status


        return []  # Return None if no match is found

    
    
    def all_transformed_status(self):
        # Join tables
        stmt = (
            self.db.query(
                Status.id,
                Status.name,
                Status.description,
                Status.created_at,
                Status.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .outerjoin(User,
                       User.id == Status.created_by_id)  # Left join StockOnHand with ReceivingReport
        )

        # Return All the result
        return stmt.all()


    def update_status(self, status_id: UUID, status_update: StatusUpdate):
        try:
            status = self.db.query(Status).filter(Status.id == status_id).first()
            if not status or status.is_deleted:
                raise StatusNotFoundException(detail="Drop List not found or already deleted.")

            for key, value in status_update.dict(exclude_unset=True).items():
                setattr(status, key, value)
            self.db.commit()
            self.db.refresh(status)
            return status

        except Exception as e:
            raise StatusUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_status(self, status_id: UUID):
        try:
            status = self.db.query(Status).filter(Status.id == status_id).first()
            if not status or status.is_deleted:
                raise StatusNotFoundException(detail="Drop List not found or already deleted.")

            status.is_deleted = True
            self.db.commit()
            self.db.refresh(status)
            return status

        except Exception as e:
            raise StatusSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_status(self, status_id: UUID):
        try:
            status = self.db.query(Status).filter(Status.id == status_id).first()
            if not status or not status.is_deleted:
                raise StatusNotFoundException(detail="Drop List not found or already restored.")

            status.is_deleted = False
            self.db.commit()
            self.db.refresh(status)
            return status

        except Exception as e:
            raise StatusRestoreException(detail=f"Error: {str(e)}")


# These are the code for the business logic like calculation etc.
class StatusService(AppService):
    def create_status(self, item: StatusCreate):
        try:
            status_item = StatusCRUD(self.db).create_status(item)

        except Exception as e:
            raise StatusCreateException(detail=f"Error: {str(e)}")


        return status_item

    def get_status(self):
        try:
            status_item = StatusCRUD(self.db).get_status()

        except Exception as e:
            raise StatusNotFoundException(detail=f"Error: {str(e)}")
        return status_item


    def get_status_by_name(self, name):
        try:
            status_item = StatusCRUD(self.db).get_status_by_name(name)

            if not status_item:
                raise StatusNotFoundException(detail="Status not found.")

            return status_item

        except Exception as e:
            raise StatusNotFoundException(detail=f"Error: {str(e)}")

    
    
    def all_transformed_status(self):
        try:
            warehouse_item = StatusCRUD(self.db).all_transformed_status()

        except Exception as e:
            raise StatusNotFoundException(detail=f"Error: {str(e)}")
        return warehouse_item

    # This is the service/business logic in updating the status.
    def update_status(self, status_id: UUID, status_update: StatusUpdate):
        status = StatusCRUD(self.db).update_status(status_id, status_update)
        return status

    # This is the service/business logic in soft deleting the status.
    def soft_delete_status(self, status_id: UUID):
        status = StatusCRUD(self.db).soft_delete_status(status_id)
        return status


    # This is the service/business logic in soft restoring the status.
    def restore_status(self, status_id: UUID):
        status = StatusCRUD(self.db).restore_status(status_id)
        return status





