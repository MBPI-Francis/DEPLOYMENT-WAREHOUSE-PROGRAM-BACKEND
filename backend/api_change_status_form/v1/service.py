from backend.api_change_status_form.v1.exceptions import TempHeldFormCreateException, TempHeldFormNotFoundException
from backend.api_change_status_form.v1.main import AppService
from backend.api_change_status_form.v1.schemas import TempHeldFormCreate, TempHeldFormUpdate
from uuid import UUID
from .crud import TempHeldFormCRUD


# These are the code for the business logic like calculation etc.
class TempHeldFormService(AppService):
    def create_held_form(self, item: TempHeldFormCreate):
        try:
            held_form_item = TempHeldFormCRUD(self.db).create_held_form(item)

        except Exception as e:
            raise TempHeldFormCreateException(detail=f"Error: {str(e)}")


        return held_form_item

    def get_held_form(self):
        try:
            held_form_item = TempHeldFormCRUD(self.db).get_held_form()

        except Exception as e:
            raise TempHeldFormNotFoundException(detail=f"Error: {str(e)}")
        return held_form_item


    def get_deleted_held_form(self):
        try:
            held_form_item = TempHeldFormCRUD(self.db).get_deleted_held_form()

        except Exception as e:
            raise TempHeldFormNotFoundException(detail=f"Error: {str(e)}")
        return held_form_item


    def get_historical_held_form(self):
        try:
            held_form_item = TempHeldFormCRUD(self.db).get_historical_held_form()

        except Exception as e:
            raise TempHeldFormNotFoundException(detail=f"Error: {str(e)}")
        return held_form_item

    # This is the service/business logic in updating the change_status_form.
    def update_held_form(self, held_form_id: UUID, held_form_update: TempHeldFormUpdate):
        held_form = TempHeldFormCRUD(self.db).update_held_form(held_form_id, held_form_update)
        return held_form

    # This is the service/business logic in soft deleting the change_status_form.
    def soft_delete_held_form(self, held_form_id: UUID):
        held_form = TempHeldFormCRUD(self.db).soft_delete_held_form(held_form_id)
        return held_form


    # This is the service/business logic in soft restoring the change_status_form.
    def restore_held_form(self, held_form_id: UUID):
        held_form = TempHeldFormCRUD(self.db).restore_held_form(held_form_id)
        return held_form





