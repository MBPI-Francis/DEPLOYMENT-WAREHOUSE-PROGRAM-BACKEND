from backend.api_reports.v1.main import AppCRUD
from backend.api_reports.v1.schemas import FormEntryResponse
from sqlalchemy import text
from typing import List, Optional

class FormEntryCRUD(AppCRUD):
    def get_form_entries(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        mat_code: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> List[FormEntryResponse]:

        query = """
            SELECT
                date_encoded,
                date_reported,
                document_type,
                document_number,
                mat_code,
                qty,
                whse_no,
                status,
                is_deleted,
                is_cleared,
                is_computed
            FROM view_form_entries_log
            WHERE 1 = 1
        """

        params = {}

        if date_from and date_to:
            query += " AND date_reported BETWEEN :date_from AND :date_to"
            params["date_from"] = date_from
            params["date_to"] = date_to

        if mat_code and mat_code.lower() != "all" and mat_code.strip() != "":
            query += " AND mat_code = :mat_code"
            params["mat_code"] = mat_code

        if document_type and document_type.lower() != "all" and document_type.strip() != "":
            query += " AND document_type = :document_type"
            params["document_type"] = document_type

        result = self.db.execute(text(query), params)
        rows = result.fetchall()

        return [
            FormEntryResponse(
                date_encoded=row.date_encoded,
                date_reported=row.date_reported,
                document_type=row.document_type,
                document_number=row.document_number,
                mat_code=row.mat_code,
                qty=row.qty,
                whse_no=row.whse_no,
                status=row.status,
                is_deleted=row.is_deleted,
                is_cleared=row.is_cleared,
                is_computed=row.is_computed,
            )
            for row in rows
        ]