"""
Data Access Layer (CRUD) for Inventory Reports.

Executes parameterized queries against schema_whrm.view_form_entries_log
with pagination and fast dictionary mapping for large historical datasets.
Strictly read-only and free of HTTP exceptions.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import text

from core.base import BaseRepository


class FormEntryCRUD(BaseRepository):
    """Repository handling read queries against unified form entry views."""

    def get_form_entries(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        mat_code: Optional[str] = None,
        document_type: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves paginated form entries matching multi-field filter criteria.
        Converts rows via mappings() for high serialization throughput.
        """
        query = """
            SELECT
                date_encoded,
                date_reported,
                document_type,
                document_number,
                mat_code,
                qty,
                whse_no,
                status
            FROM schema_whrm.view_form_entries_log
            WHERE is_deleted = FALSE
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}

        if date_from and date_to:
            query += " AND date_reported BETWEEN :date_from AND :date_to"
            params["date_from"] = date_from
            params["date_to"] = date_to
        elif date_from:
            query += " AND date_reported >= :date_from"
            params["date_from"] = date_from
        elif date_to:
            query += " AND date_reported <= :date_to"
            params["date_to"] = date_to

        if mat_code and mat_code.strip().lower() != "all":
            query += " AND UPPER(mat_code) = :mat_code"
            params["mat_code"] = mat_code.strip().upper()

        if document_type and document_type.strip().lower() != "all":
            clean_doc = document_type.strip().lower()
            if clean_doc == "adjustment_form_entries":
                query += " AND document_type LIKE :document_type"
                params["document_type"] = "adjustment_form_%correct"
            else:
                query += " AND document_type = :document_type"
                params["document_type"] = clean_doc

        if location and location.strip().lower() != "all":
            query += " AND whse_no = :whse_no"
            params["whse_no"] = location.strip()

        if status and status.strip().lower() != "all":
            query += " AND LOWER(status) = :status"
            params["status"] = status.strip().lower()

        query += " ORDER BY date_reported DESC, date_encoded DESC LIMIT :limit OFFSET :offset"

        result = self.db.execute(text(query), params)
        return [dict(row) for row in result.mappings().all()]

    def get_form_entries_for_export(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        mat_code: Optional[str] = None,
        document_type: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        max_rows: int = 50000
    ) -> List[Dict[str, Any]]:
        """
        Retrieves raw dictionary records optimized for streaming into Pandas/Excel.
        Enforces a maximum row ceiling to guarantee memory safety.
        """
        query = """
            SELECT
                date_encoded,
                date_reported,
                document_type,
                document_number,
                mat_code,
                qty,
                whse_no,
                status
            FROM schema_whrm.view_form_entries_log
            WHERE is_deleted = FALSE
        """
        params: Dict[str, Any] = {"max_rows": max_rows}

        if date_from and date_to:
            query += " AND date_reported BETWEEN :date_from AND :date_to"
            params["date_from"] = date_from
            params["date_to"] = date_to
        elif date_from:
            query += " AND date_reported >= :date_from"
            params["date_from"] = date_from
        elif date_to:
            query += " AND date_reported <= :date_to"
            params["date_to"] = date_to

        if mat_code and mat_code.strip().lower() != "all":
            query += " AND UPPER(mat_code) = :mat_code"
            params["mat_code"] = mat_code.strip().upper()

        if document_type and document_type.strip().lower() != "all":
            clean_doc = document_type.strip().lower()
            if clean_doc == "adjustment_form_entries":
                query += " AND document_type LIKE :document_type"
                params["document_type"] = "adjustment_form_%correct"
            else:
                query += " AND document_type = :document_type"
                params["document_type"] = clean_doc

        if location and location.strip().lower() != "all":
            query += " AND whse_no = :whse_no"
            params["whse_no"] = location.strip()

        if status and status.strip().lower() != "all":
            query += " AND LOWER(status) = :status"
            params["status"] = status.strip().lower()

        query += " ORDER BY date_reported ASC, mat_code ASC LIMIT :max_rows"

        result = self.db.execute(text(query), params)
        return [dict(row) for row in result.mappings().all()]