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



# The below version is working
# from io import BytesIO
# import pandas as pd
# from backend.api_reports.v1.main import AppService
# from backend.api_reports.v1.crud import FormEntryCRUD
# from typing import List, Optional
# from backend.api_reports.v1.schemas import FormEntryResponse
# # Removed os and Path imports as we're no longer saving to disk on the server
# # from pathlib import Path
# # from datetime import datetime
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
#     ) -> BytesIO: # Changed return type to BytesIO
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
#         # Create an in-memory binary stream
#         excel_buffer = BytesIO()
#
#         # Export to Excel file in memory
#         with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
#             df.to_excel(writer, index=False, sheet_name="FormEntries")
#
#         # Rewind the buffer to the beginning
#         excel_buffer.seek(0)
#         return excel_buffer


# This is also working this is the Version 3 Where it has summary sheet
# from io import BytesIO
# import pandas as pd
# from backend.api_reports.v1.main import AppService
# from backend.api_reports.v1.crud import FormEntryCRUD
# from typing import List, Optional
# from backend.api_reports.v1.schemas import FormEntryResponse
# from datetime import datetime # Import datetime for date formatting
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
#     ) -> BytesIO:
#         # Get detailed data
#         form_entries = self.get_form_entries(
#             date_from=date_from,
#             date_to=date_to,
#             mat_code=mat_code,
#             document_type=document_type,
#             location=location,
#             status=status,
#         )
#
#         if not form_entries:
#             # Handle case where no data is found for export
#             # You might want to return an empty buffer or raise an exception
#             excel_buffer = BytesIO()
#             with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
#                 pd.DataFrame({"Message": ["No data found for the selected filters."]}) \
#                   .to_excel(writer, index=False, sheet_name="No Data")
#             excel_buffer.seek(0)
#             return excel_buffer
#
#         # Convert list of Pydantic models to list of dictionaries
#         data = [entry.dict() for entry in form_entries]
#         df_detailed = pd.DataFrame(data)
#
#         # --- New Feature: Compute sum by RM and Day ---
#
#         # 1. Ensure 'date_reported' is a datetime object for proper grouping
#         #    Pydantic's datetime conversion might already handle this, but it's good to be explicit
#         df_detailed['date_reported'] = pd.to_datetime(df_detailed['date_reported'])
#
#         # 2. Group by mat_code and date (day part only) and sum the 'qty'
#         #    Use .dt.date to get just the date part (YYYY-MM-DD) from the datetime objects
#         df_summary = df_detailed.groupby(['mat_code', df_detailed['date_reported'].dt.date])['qty'].sum().reset_index()
#
#         # 3. Rename the sum column for clarity
#         df_summary = df_summary.rename(columns={'qty': 'Total QTY for Day'})
#         df_summary = df_summary.rename(columns={'date_reported': 'Date'}) # Rename for consistency
#
#
#         # Create an in-memory binary stream
#         excel_buffer = BytesIO()
#
#         # Export both DataFrames to Excel file on separate sheets
#         with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
#             # Write the detailed data to the first sheet
#             df_detailed.to_excel(writer, index=False, sheet_name="Detailed Data")
#
#             # Write the summary data to a second sheet
#             df_summary.to_excel(writer, index=False, sheet_name="Daily RM Summary")
#
#         # Rewind the buffer to the beginning before returning
#         excel_buffer.seek(0)
#         return excel_buffer


from io import BytesIO
import pandas as pd
from backend.api_reports.v1.main import AppService
from backend.api_reports.v1.crud import FormEntryCRUD
from typing import List, Optional
from backend.api_reports.v1.schemas import FormEntryResponse
from datetime import datetime # Import datetime for date formatting


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
    ) -> BytesIO:
        # Get detailed data
        form_entries = self.get_form_entries(
            date_from=date_from,
            date_to=date_to,
            mat_code=mat_code,
            document_type=document_type,
            location=location,
            status=status,
        )

        if not form_entries:
            # Handle case where no data is found for export
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                pd.DataFrame({"Message": ["No data found for the selected filters."]}) \
                  .to_excel(writer, index=False, sheet_name="No Data")
            excel_buffer.seek(0)
            return excel_buffer

        # Convert list of Pydantic models to list of dictionaries
        data = [entry.dict() for entry in form_entries]
        df_detailed = pd.DataFrame(data)

        # --- New Feature: Compute sum by RM and Day in Pivot Table format ---

        # 1. Ensure 'date_reported' is a datetime object for proper grouping and formatting
        #    Use errors='coerce' to turn unparseable dates into NaT (Not a Time)
        df_detailed['date_reported'] = pd.to_datetime(df_detailed['date_reported'], errors='coerce')

        # Drop rows where 'date_reported' became NaT, as they cannot be grouped by date
        df_detailed.dropna(subset=['date_reported'], inplace=True)

        if df_detailed.empty:
            # Handle case where all dates were invalid or all rows dropped
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                pd.DataFrame({"Message": ["No valid date entries found for aggregation."]}) \
                  .to_excel(writer, index=False, sheet_name="No Valid Dates")
            excel_buffer.seek(0)
            return excel_buffer

        # 2. Create the long format summary
        df_long_summary = df_detailed.groupby(['mat_code', df_detailed['date_reported'].dt.date])['qty'].sum().reset_index()

        # 3. Rename the date column in the long summary for clarity before pivoting
        df_long_summary = df_long_summary.rename(columns={'date_reported': 'Date'})

        # 4. Format the 'Date' column to 'MM/DD/YYYY' string format, as these will be column headers
        #    Use .apply() to call strftime on each datetime.date object
        df_long_summary['Date'] = df_long_summary['Date'].apply(lambda x: x.strftime('%m/%d/%Y'))


        # 5. Pivot the table:
        df_pivot_summary = df_long_summary.pivot_table(
            index='mat_code',
            columns='Date',
            values='qty', # Use 'qty' as it's the column directly from groupby sum
            fill_value=0
        )

        # 6. Sort by mat_code (index)
        df_pivot_summary = df_pivot_summary.sort_index(ascending=True)

        # 7. Sort date columns chronologically.
        #    Convert column names (date strings) back to datetime objects for sorting,
        #    then convert them back to 'MM/DD/YYYY' string format for final column order.
        #    Also added errors='coerce' and dropna for robustness in column name conversion.
        sorted_date_cols = pd.to_datetime(df_pivot_summary.columns, format='%m/%d/%Y', errors='coerce').sort_values()
        sorted_date_cols = sorted_date_cols.dropna() # Remove any NaT results from parsing column names
        sorted_date_col_names = sorted_date_cols.strftime('%m/%d/%Y').tolist()
        df_pivot_summary = df_pivot_summary[sorted_date_col_names]

        # 8. Reset index to make 'mat_code' a regular column
        df_pivot_summary = df_pivot_summary.reset_index()


        # Create an in-memory binary stream
        excel_buffer = BytesIO()

        # Export both DataFrames to Excel file on separate sheets
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            # Write the detailed data to the first sheet
            df_detailed.to_excel(writer, index=False, sheet_name="Detailed Data")

            # Write the pivot summary data to a second sheet
            df_pivot_summary.to_excel(writer, index=False, sheet_name="Daily RM Summary")

            # Optional: Adjust column widths for better readability (using xlsxwriter engine features)
            workbook = writer.book
            if 'Daily RM Summary' in writer.sheets: # Check if sheet exists before trying to format
                summary_sheet = writer.sheets['Daily RM Summary']

                # Set width for 'mat_code' column
                summary_sheet.set_column(0, 0, 20) # Column A (index 0)

                # Set width for all date columns
                # Iterate through actual columns of the *written* DataFrame, skipping the first (mat_code)
                for i, col_name in enumerate(df_pivot_summary.columns[1:]):
                    summary_sheet.set_column(i + 1, i + 1, 12) # Columns B onwards (index i+1)


        # Rewind the buffer to the beginning before returning
        excel_buffer.seek(0)
        return excel_buffer