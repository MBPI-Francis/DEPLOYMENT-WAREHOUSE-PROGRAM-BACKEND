from backend.api_transfer_form.v1.exceptions import TempTransferFormCreateException, TempTransferFormNotFoundException
from backend.api_transfer_form.v1.main import AppService
from backend.api_transfer_form.v1.schemas import TempTransferFormCreate, TempTransferFormUpdate
from uuid import UUID
from backend.api_transfer_form.v1.crud import TempTransferFormCRUD



# These are the code for the business logic like calculation etc.
class TempTransferFormService(AppService):
    def create_transfer_form(self, item: TempTransferFormCreate):
        try:
            transfer_form_item = TempTransferFormCRUD(self.db).create_transfer_form(item)

        except Exception as e:
            raise TempTransferFormCreateException(detail=f"Error: {str(e)}")


        return transfer_form_item

    def get_transfer_form(self):
        try:
            transfer_form_item = TempTransferFormCRUD(self.db).get_transfer_form()

        except Exception as e:
            raise TempTransferFormNotFoundException(detail=f"Error: {str(e)}")
        return transfer_form_item


    def get_deleted_transfer_form(self):
        try:
            transfer_form_item = TempTransferFormCRUD(self.db).get_deleted_transfer_form()

        except Exception as e:
            raise TempTransferFormNotFoundException(detail=f"Error: {str(e)}")
        return transfer_form_item


    def get_historical_transfer_form(self):
        try:
            transfer_form_item = TempTransferFormCRUD(self.db).get_historical_transfer_form()

        except Exception as e:
            raise TempTransferFormNotFoundException(detail=f"Error: {str(e)}")
        return transfer_form_item

    # This is the service/business logic in updating the transfer_form.
    def update_transfer_form(self, transfer_form_id: UUID, transfer_form_update: TempTransferFormUpdate):
        transfer_form = TempTransferFormCRUD(self.db).update_transfer_form(transfer_form_id, transfer_form_update)
        return transfer_form


    # This is the service/business logic in soft deleting the transfer_form.
    def soft_delete_transfer_form(self, transfer_form_id: UUID):
        transfer_form = TempTransferFormCRUD(self.db).soft_delete_transfer_form(transfer_form_id)
        return transfer_form


    # This is the service/business logic in soft restoring the transfer_form.
    def restore_transfer_form(self, transfer_form_id: UUID):
        transfer_form = TempTransferFormCRUD(self.db).restore_transfer_form(transfer_form_id)
        return transfer_form





