from backend.api_reports.v1.main import AppService
from backend.api_reports.v1.crud import FormEntryCRUD
from typing import List, Optional
from backend.api_reports.v1.schemas import FormEntryResponse


class FormEntryService(AppService):

    def get_form_entries(
        self,
        date_from: Optional[str],
        date_to: Optional[str],
        mat_code: Optional[str],
        document_type: Optional[str],
    ) -> List[FormEntryResponse]:

        form_entries = FormEntryCRUD(self.db).get_form_entries(
            date_from=date_from,
            date_to=date_to,
            mat_code=mat_code,
            document_type=document_type,
        )

        return form_entries