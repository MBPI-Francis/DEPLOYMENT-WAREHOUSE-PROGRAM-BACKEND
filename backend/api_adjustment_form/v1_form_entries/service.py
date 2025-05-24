from backend.api_adjustment_form.v1_form_entries.exceptions import AdjustmentFormCreateException, AdjustmentFormNotFoundException
from backend.api_adjustment_form.v1_form_entries.main import AppService
from backend.api_adjustment_form.v1_form_entries.schemas import AdjustmentFormCreate, AdjustmentFormUpdate
from uuid import UUID
from backend.api_adjustment_form.v1_form_entries.crud import AdjustmentFormCRUD



# These are the code for the business logic like calculation etc.
class AdjustmentFormService(AppService):
    def create_adjustment_form(self, item: AdjustmentFormCreate, form: str):
        try:
            adjustment_form_item = AdjustmentFormCRUD(self.db).create_adjustment_form(item, form)

        except Exception as e:
            raise AdjustmentFormCreateException(detail=f"Error: {str(e)}")


        return adjustment_form_item

    def get_adjustment_form(self):
        try:
            adjustment_form_item = AdjustmentFormCRUD(self.db).get_adjustment_form()

        except Exception as e:
            raise AdjustmentFormNotFoundException(detail=f"Error: {str(e)}")
        return adjustment_form_item

    def get_deleted_adjustment_form(self):
        try:
            adjustment_form_item = AdjustmentFormCRUD(self.db).get_deleted_adjustment_form()

        except Exception as e:
            raise AdjustmentFormNotFoundException(detail=f"Error: {str(e)}")
        return adjustment_form_item

    def get_historical_adjustment_form(self):
        try:
            adjustment_form_item = AdjustmentFormCRUD(self.db).get_historical_adjustment_form()

        except Exception as e:
            raise AdjustmentFormNotFoundException(detail=f"Error: {str(e)}")
        return adjustment_form_item

    # This is the service/business logic in updating the adjustment_form.
    def update_adjustment_form(self, adjustment_form_id: UUID, adjustment_form_update: AdjustmentFormUpdate):
        adjustment_form = AdjustmentFormCRUD(self.db).update_adjustment_form(adjustment_form_id, adjustment_form_update)
        return adjustment_form

    # This is the service/business logic in soft deleting the adjustment_form.
    def soft_delete_adjustment_form(self, adjustment_form_id: UUID):
        adjustment_form = AdjustmentFormCRUD(self.db).soft_delete_adjustment_form(adjustment_form_id)
        return adjustment_form


    # This is the service/business logic in soft restoring the adjustment_form.
    def restore_adjustment_form(self, adjustment_form_id: UUID):
        adjustment_form = AdjustmentFormCRUD(self.db).restore_adjustment_form(adjustment_form_id)
        return adjustment_form





