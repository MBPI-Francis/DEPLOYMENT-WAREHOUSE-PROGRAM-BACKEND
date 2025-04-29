from sqlalchemy.exc import IntegrityError
from backend.api_raw_materials.v1.schemas import RawMaterialCreate
from backend.api_raw_materials.v1.crud import RawMaterialCRUD
from backend.api_status.v1.models import Status
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_stock_on_hand.v1.exceptions import (StockOnHandCreateException,
                                                     StockOnHandNotFoundException,
                                                     )
from backend.api_stock_on_hand.v1.main import AppService
from backend.api_stock_on_hand.v1.schemas import StockOnHandCreate, StockOnHandUpdate
from uuid import UUID
import io
import pandas as pd
from backend.api_warehouses.v1.models import Warehouse
from backend.api_stock_on_hand.v1.crud import StockOnHandCRUD
from fastapi import HTTPException
import msoffcrypto
from sqlalchemy import text



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



    def import_rm_soh(self, content, password):

        # Convert bytes to a BytesIO stream
        excel_data = io.BytesIO(content)
        office_file = msoffcrypto.OfficeFile(excel_data)
        decrypted_excel = io.BytesIO()

        # Check if file is encrypted
        if office_file.is_encrypted():
            try:
                office_file.load_key(password="maranatha101")  # Attempt decryption using the content of the password
                office_file.decrypt(decrypted_excel)
                office_file.decrypt(decrypted_excel)  # Write decrypted content to a new BytesIO object
                df = pd.read_excel(decrypted_excel, sheet_name=None, engine='openpyxl', header=0)
            except Exception:
                raise HTTPException(status_code=400, detail="Incorrect password. Unable to import the Excel file.")

        else:
            # If there is no password, the panda will read it
            df = pd.read_excel(excel_data, sheet_name=None, engine='openpyxl', header=0)

        try:

            try:
                def get_rm_code_id(rm_code):
                    # This code removes any leading or trailing whitespace and converts to uppercase
                    raw_mat = rm_code.strip().upper()

                    # This code checks if the raw material exists
                    rm_code_record = self.db.query(RawMaterial.id).filter(RawMaterial.rm_code == raw_mat).first()

                    if rm_code_record:
                        return rm_code_record.id  # It returns the existing raw material ID

                    # If raw material does not exist, create it
                    new_raw_material_data = RawMaterialCreate(
                        rm_code=raw_mat,  # Ensure rm_code is set (mandatory)
                        rm_name=raw_mat,  # Assuming rm_name is the same as rm_code
                        description="Auto-generated raw material",  # Provide a default description
                        created_by_id=None,  # Replace with actual user ID if needed
                        updated_by_id=None
                    )

                    # Instantiate the RawMaterialCRUD class
                    raw_material_crud = RawMaterialCRUD(self.db)

                    try:
                        new_raw_material = raw_material_crud.create_raw_material(new_raw_material_data)
                        return new_raw_material.id
                    except IntegrityError:
                        self.db.rollback()
                        raise HTTPException(status_code=500, detail="Error while creating raw material.")


                def get_latest_count():
                    # Get the largest stock recalculation count
                    existing_query = text("""SELECT MAX(stock_recalculation_count) AS largest_modification 
                                            FROM tbl_stock_on_hand;
                                            """)

                    largest_count = self.db.execute(
                        existing_query).fetchone()  # or .fetchall() if expecting multiple rows
                    if largest_count[0]:
                        new_stock_recalculation_count = largest_count[0] + 1
                    else:
                        new_stock_recalculation_count = 1

                    return new_stock_recalculation_count

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

                # Get the latest count
                latest_count = get_latest_count()

                # Process each sheet
                for sheet_name, data in df.items():
                    if sheet_name in ['WHSE1', 'WHSE2', 'WHSE4']:

                        # Extract the date from the column header (first column name)
                        snapshot_date = None
                        try:
                            raw_value = str(data.columns[0]).strip()  # Get the first column header as a string
                            snapshot_date = pd.to_datetime(raw_value, errors='coerce').date()  # Convert to date

                            if pd.isna(snapshot_date):
                                raise ValueError(
                                    f"Invalid date format in column header: {raw_value}")  # Raise error for debugging

                        except Exception as e:
                            raise HTTPException(status_code=400,
                                                detail=f"Invalid date format in column header of {sheet_name}: {str(e)}")

                        # Rename columns manually (shift column names down since the first row is actual data)
                        data.columns = data.iloc[0]  # Set first row as column headers
                        data = data[0:].reset_index(drop=True)  # Drop first row and reset index

                        # Check the number of columns and assign column names accordingly
                        if len(data.columns) == 6:
                            data.columns = ["A", "B", "C", "D", "E", "F"]  # Adjust for 6 columns
                        elif len(data.columns) == 7:
                            data.columns = ["A", "B", "C", "D", "E", "F", "G"]  # Adjust for 7 columns
                        else:
                            raise ValueError(
                                f"Unexpected number of columns in WHSE# sheet in the Excel File: {len(data.columns)}")  # Raise an error if the column count is neither 6 nor 7

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
                            StockOnHandCRUD(self.db).import_rm_soh(rm_code_id, total, status_id, warehouse_id, snapshot_date, latest_count)

            except HTTPException as e:
                raise e  # Pass FastAPI errors directly

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")





