# from io import BytesIO
#
# import pandas as pd
#
# from backend.api_reports.v1.main import AppService
# from backend.api_reports.v1.crud import FormEntryCRUD
# from typing import List, Optional
# from backend.api_reports.v1.schemas import FormEntryResponse
# import os
# from pathlib import Path
# from datetime import datetime
#
#
# class FormEntryService(AppService):
#
#     def get_form_entries(
#         self,
#         date_from: Optional[str],
#         date_to: Optional[str],
#         mat_code: Optional[str],
#         document_type: Optional[str],
#         location: Optional[str],
#         status: Optional[str],
#     ) -> List[FormEntryResponse]:
#
#         form_entries = FormEntryCRUD(self.db).get_form_entries(
#             date_from=date_from,
#             date_to=date_to,
#             mat_code=mat_code,
#             document_type=document_type,
#             location=location,
#             status=status
#         )
#
#         return form_entries
#
#
#     def export_form_entries_to_excel_file(
#         self,
#         date_from: Optional[str] = None,
#         date_to: Optional[str] = None,
#         mat_code: Optional[str] = None,
#         document_type: Optional[str] = None,
#         location: Optional[str] = None,
#         status: Optional[str] = None,
#     ) -> str:
#         # Create desktop export folder
#         desktop_path = Path.home() / "Desktop"
#         export_folder = desktop_path / "Warehouse Reports"
#         export_folder.mkdir(parents=True, exist_ok=True)
#
#         # File path with timestamp
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         file_path = export_folder / f"form_entries_{timestamp}.xlsx"
#
#         # Get data
#         form_entries = self.get_form_entries(
#             date_from=date_from,
#             date_to=date_to,
#             mat_code=mat_code,
#             document_type=document_type,
#             location=location,
#             status=status,
#         )
#         data = [entry.dict() for entry in form_entries]
#         df = pd.DataFrame(data)
#
#         # Export to Excel file
#         with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
#             df.to_excel(writer, index=False, sheet_name="FormEntries")
#
#         return str(file_path)


from io import BytesIO
import pandas as pd
from backend.api_reports.v1.main import AppService
from backend.api_reports.v1.crud import FormEntryCRUD
from typing import List, Optional
from backend.api_reports.v1.schemas import FormEntryResponse
# Removed os and Path imports as we're no longer saving to disk on the server
# from pathlib import Path
# from datetime import datetime


class FormEntryService(AppService):

    def get_form_entries(
        self,
        date_from: Optional[str],
        date_to: Optional[str],
        mat_code: Optional[str],
        document_type: Optional[str],
        location: Optional[str],
        status: Optional[str],
    ) -> List[FormEntryResponse]:

        form_entries = FormEntryCRUD(self.db).get_form_entries(
            date_from=date_from,
            date_to=date_to,
            mat_code=mat_code,
            document_type=document_type,
            location=location,
            status=status
        )

        return form_entries


    def export_form_entries_to_excel_file(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        mat_code: Optional[str] = None,
        document_type: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BytesIO: # Changed return type to BytesIO
        # Get data
        form_entries = self.get_form_entries(
            date_from=date_from,
            date_to=date_to,
            mat_code=mat_code,
            document_type=document_type,
            location=location,
            status=status,
        )
        data = [entry.dict() for entry in form_entries]
        df = pd.DataFrame(data)

        # Create an in-memory binary stream
        excel_buffer = BytesIO()

        # Export to Excel file in memory
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="FormEntries")

        # Rewind the buffer to the beginning
        excel_buffer.seek(0)
        return excel_buffer

