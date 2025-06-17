from backend.api_preparation_form.v1.exceptions import TempPreparationFormCreateException, TempPreparationFormNotFoundException
from backend.api_preparation_form.v1.main import AppService
from backend.api_preparation_form.v1.schemas import TempPreparationFormCreate, TempPreparationFormUpdate
from uuid import UUID
from .crud import TempPreparationFormCRUD

# These are the code for the business logic like calculation etc.
class TempPreparationFormService(AppService):
    def create_preparation_form(self, item: TempPreparationFormCreate):
        try:
            preparation_form_item = TempPreparationFormCRUD(self.db).create_preparation_form(item)

        except Exception as e:
            raise TempPreparationFormCreateException(detail=f"Error: {str(e)}")


        return preparation_form_item


    def get_preparation_form(self):
        try:
            preparation_form_item = TempPreparationFormCRUD(self.db).get_preparation_form()

        except Exception as e:
            raise TempPreparationFormNotFoundException(detail=f"Error: {str(e)}")
        return preparation_form_item


    def get_deleted_preparation_form(self):
        try:
            preparation_form_item = TempPreparationFormCRUD(self.db).get_deleted_preparation_form()

        except Exception as e:
            raise TempPreparationFormNotFoundException(detail=f"Error: {str(e)}")
        return preparation_form_item


    def get_historical_preparation_form(self, record_id):
        try:
            preparation_form_item = TempPreparationFormCRUD(self.db).get_historical_preparation_form(record_id)

        except Exception as e:
            raise TempPreparationFormNotFoundException(detail=f"Error: {str(e)}")
        return preparation_form_item


    # This is the service/business logic in updating the preparation_form.
    def update_preparation_form(self, preparation_form_id: UUID, preparation_form_update: TempPreparationFormUpdate):
        preparation_form = TempPreparationFormCRUD(self.db).update_preparation_form(preparation_form_id, preparation_form_update)
        return preparation_form

    # This is the service/business logic in soft deleting the preparation_form.
    def soft_delete_preparation_form(self, preparation_form_id: UUID):
        preparation_form = TempPreparationFormCRUD(self.db).soft_delete_preparation_form(preparation_form_id)
        return preparation_form


    # This is the service/business logic in soft restoring the preparation_form.
    def restore_preparation_form(self, preparation_form_id: UUID):
        preparation_form = TempPreparationFormCRUD(self.db).restore_preparation_form(preparation_form_id)
        return preparation_form





