from pydantic_core import to_jsonable_python

from backend.api_status.v1.models import Status
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_stock_on_hand.v1.exceptions import (StockOnHandCreateException,
                                                     StockOnHandNotFoundException,
                                                     StockOnHandUpdateException,
                                                     StockOnHandSoftDeleteException,
                                                     StockOnHandRestoreException
                                                     )
from backend.api_stock_on_hand.v1.main import AppService
from backend.api_stock_on_hand.v1.schemas import StockOnHandCreate, StockOnHandUpdate
from uuid import UUID
import io
import pandas as pd
from backend.api_warehouses.v1.models import Warehouse
from backend.api_stock_on_hand.v1.crud import StockOnHandCRUD




# These are the code for the business logic like calculation etc.
class StockOnHandService(AppService):
    def create_rm_soh(self, item: StockOnHandCreate):
        try:
            rm_soh_item = StockOnHandCRUD(self.db).create_rm_soh(item)

        except Exception as e:
            raise StockOnHandCreateException(detail=f"Error: {str(e)}")

        return rm_soh_item

    def all_rm_soh(self):
        try:
            rm_soh_item = StockOnHandCRUD(self.db).all_rm_soh()

        except Exception as e:
            raise StockOnHandNotFoundException(detail=f"Error: {str(e)}")
        return rm_soh_item

    # Still not sure what is this about
    def get_historical_stock_on_hand(self, date_computed):
        try:
            rm_soh_item = StockOnHandCRUD(self.db).get_historical_stock_on_hand(date_computed)

        except Exception as e:
            raise StockOnHandNotFoundException(detail=f"Error: {str(e)}")
        return rm_soh_item



    # Still not sure what is this about
    # def get_rm_soh(self, warehouse_id: UUID, rm_code_id: UUID):
    #     try:
    #         rm_soh_item = TempReceivingReportCRUD(self.db).get_latest_soh_record(warehouse_id, rm_code_id)
    #
    #     except Exception as e:
    #         raise StockOnHandNotFoundException(detail=f"Error: {str(e)}")
    #     return rm_soh_item

    # This is the service/business logic in updating the rm_soh.
    def update_rm_soh(self, rm_soh_id: UUID, rm_soh_update: StockOnHandUpdate):
        rm_soh = StockOnHandCRUD(self.db).update_rm_soh(rm_soh_id, rm_soh_update)
        return rm_soh

    # This is the service/business logic in soft deleting the rm_soh.
    def soft_delete_rm_soh(self, rm_soh_id: UUID):
        rm_soh = StockOnHandCRUD(self.db).soft_delete_rm_soh(rm_soh_id)
        return rm_soh


    # This is the service/business logic in soft restoring the rm_soh.
    def restore_rm_soh(self, rm_soh_id: UUID):
        rm_soh = StockOnHandCRUD(self.db).restore_rm_soh(rm_soh_id)
        return rm_soh



    def import_rm_soh(self, content):

        # Convert bytes to a BytesIO stream
        excel_data = io.BytesIO(content)

        try:
            # Convert the incoming items to SQLAlchemy model instances

            def get_rm_code_id(rm_code):
                # Remove any leading or trailing whitespace from rm_code
                raw_mat = rm_code.strip().upper()


                rm_code_record = self.db.query(RawMaterial.id).filter(RawMaterial.rm_code == raw_mat).first()
                return rm_code_record.id if rm_code_record else None

            def get_status_id(status_name):
                status_record = self.db.query(Status.id).filter(Status.name == status_name).first()
                return status_record.id if status_record else None


            def get_warehouse_id(warehouse_name):
                # Map sheet names to warehouse numbers
                warehouse_mapping = {
                    "whse1": 1,
                    "whse2": 2,
                    "whse4": 4,
                }

                # Get the warehouse number corresponding to the sheet name
                warehouse_number = warehouse_mapping.get(warehouse_name.lower())

                if warehouse_number:
                    # Query the database using the warehouse number
                    warehouse_record = self.db.query(Warehouse.id).filter(
                        Warehouse.wh_number == warehouse_number).first()
                    return warehouse_record.id if warehouse_record else None
                return None

            # Read the Excel file into a pandas DataFrame
            df = pd.read_excel(excel_data, sheet_name=None, engine='openpyxl', header=0)

            # Process each sheet
            for sheet_name, data in df.items():
                if sheet_name in ['WHSE1', 'WHSE2', 'WHSE4']:

                    # Rename columns manually based on observed structure
                    data.columns = ["A", "B", "C", "D", "E", "F", "G"]  # Adjust as needed

                    # Process specific columns (A, E, F) for each warehouse sheet
                    for _, row in data.iterrows():

                        rm_code = row.get('A', None)  # Use .get() to avoid KeyErrors
                        total = row.get('E', 0)  # Default to 0 if missing
                        status = row.get('F', None)  # Default to 'Unknown' if missing


                        # Convert the status into good if they are blank in the excel
                        if pd.isna(status):
                            status = "good"


                        # Get relevant IDs
                        rm_code_id = get_rm_code_id(rm_code)
                        status_id = get_status_id(status)
                        warehouse_id = get_warehouse_id(sheet_name.lower())

                        # Insert the data into the StockOnHand table
                        StockOnHandCRUD(self.db).import_rm_soh(rm_code_id, total, status_id, warehouse_id)

        except Exception as e:
            raise StockOnHandCreateException(detail=f"Error: {str(e)}")






