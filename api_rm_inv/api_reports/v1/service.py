"""
Business Service Layer for Inventory Reports.

Coordinates paginated report queries and high-speed two-sheet Excel workbook generation:
- Sheet 1: Detailed Data (All transaction line items)
- Sheet 2: Daily RM Summary (Pivot table aggregating net consumption/movement by material and day)
Includes constant-memory streaming and export auditing.
"""

from io import BytesIO
from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime
from fastapi import Request
from sqlalchemy.orm import Session

from core.base import BaseService
from core.logger import AuditLogger
from shared.users.models import User
from api_rm_inv.api_reports.v1.crud import FormEntryCRUD


class FormEntryService(BaseService):
    """Business service coordinating inventory reports and Excel data pivots."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = FormEntryCRUD(db)

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
        """Retrieves paginated ledger entries for the PyQt6 reporting grid."""
        return self.crud.get_form_entries(
            date_from=date_from,
            date_to=date_to,
            mat_code=mat_code,
            document_type=document_type,
            location=location,
            status=status,
            limit=limit,
            offset=offset
        )

    def export_form_entries_to_excel_file(
        self,
        request: Request,
        current_user: User,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        mat_code: Optional[str] = None,
        document_type: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
    ) -> BytesIO:
        """
        Streams database records into a Pandas DataFrame to generate
        a two-sheet Excel file with detailed logs and an automated daily pivot table.
        Uses constant-memory streaming mode to prevent RAM bloat.
        """
        raw_data = self.crud.get_form_entries_for_export(
            date_from=date_from,
            date_to=date_to,
            mat_code=mat_code,
            document_type=document_type,
            location=location,
            status=status,
            max_rows=50000
        )

        excel_buffer = BytesIO()

        if not raw_data:
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                pd.DataFrame({"Message": ["No data found for the selected filters."]}).to_excel(
                    writer, index=False, sheet_name="No Data"
                )
            excel_buffer.seek(0)
            return excel_buffer

        df_detailed = pd.DataFrame(raw_data)

        # -------------------------------------------------------------------
        # Automated Daily RM Summary Pivot Table Generation
        # -------------------------------------------------------------------
        df_detailed['date_reported'] = pd.to_datetime(df_detailed['date_reported'], errors='coerce')
        df_valid_dates = df_detailed.dropna(subset=['date_reported']).copy()

        if df_valid_dates.empty:
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                pd.DataFrame({"Message": ["No valid date entries found for aggregation."]}).to_excel(
                    writer, index=False, sheet_name="No Valid Dates"
                )
            excel_buffer.seek(0)
            return excel_buffer

        # Convert Decimal values to numeric floats for vectorized aggregation
        df_valid_dates['qty'] = pd.to_numeric(df_valid_dates['qty'], errors='coerce').fillna(0.0)
        df_valid_dates['Date'] = df_valid_dates['date_reported'].dt.strftime('%m/%d/%Y')

        df_long = df_valid_dates.groupby(['mat_code', 'Date'])['qty'].sum().reset_index()

        df_pivot = df_long.pivot_table(
            index='mat_code',
            columns='Date',
            values='qty',
            fill_value=0.0
        ).sort_index(ascending=True)

        sorted_cols = pd.to_datetime(df_pivot.columns, format='%m/%d/%Y', errors='coerce').sort_values().dropna()
        sorted_col_names = sorted_cols.strftime('%m/%d/%Y').tolist()
        df_pivot = df_pivot[sorted_col_names].reset_index()

        # -------------------------------------------------------------------
        # Write Excel Workbook with Constant-Memory Optimization
        # -------------------------------------------------------------------
        writer_options = {"constant_memory": True}
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter", engine_kwargs={"options": writer_options}) as writer:
            # Sheet 1: Detailed Logs
            df_detailed.to_excel(writer, index=False, sheet_name="Detailed Data")

            # Sheet 2: Daily Material Pivot
            df_pivot.to_excel(writer, index=False, sheet_name="Daily RM Summary")

            workbook = writer.book
            if 'Daily RM Summary' in writer.sheets:
                summary_sheet = writer.sheets['Daily RM Summary']
                summary_sheet.set_column(0, 0, 20)
                for col_idx in range(1, len(df_pivot.columns)):
                    summary_sheet.set_column(col_idx, col_idx, 14)

            if 'Detailed Data' in writer.sheets:
                detail_sheet = writer.sheets['Detailed Data']
                detail_sheet.set_column('A:H', 18)

        # -------------------------------------------------------------------
        # Audit Log Recording for Data Export Event
        # -------------------------------------------------------------------
        try:
            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="EXPORT",
                table_name="view_form_entries_log",
                record_id=current_user.id,
                payload={
                    "records_exported": len(df_detailed),
                    "date_from": date_from,
                    "date_to": date_to,
                    "mat_code": mat_code,
                    "document_type": document_type
                }
            )
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"[AUDIT WARNING] Report export audit failed: {str(e)}")

        excel_buffer.seek(0)
        return excel_buffer