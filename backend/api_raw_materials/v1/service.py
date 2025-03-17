from backend.api_raw_materials.v1.exceptions import RawMaterialCreateException, RawMaterialNotFoundException
from backend.api_raw_materials.v1.main import AppService
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_raw_materials.v1.schemas import RawMaterialCreate, RawMaterialUpdate
from uuid import UUID
import io
import pandas as pd
from backend.api_raw_materials.v1.crud import RawMaterialCRUD

# These are the code for the business logic like calculation etc.
class RawMaterialService(AppService):
    def create_raw_material(self, item: RawMaterialCreate):
        try:
            raw_material_item = RawMaterialCRUD(self.db).create_raw_material(item)

        except Exception as e:
            raise RawMaterialCreateException(detail=f"Error: {str(e)}")

        return raw_material_item

    def all_raw_material(self):
        try:
            raw_material_item = RawMaterialCRUD(self.db).all_raw_material()

        except Exception as e:
            raise RawMaterialNotFoundException(detail=f"Error: {str(e)}")
        return raw_material_item

    def all_transformed_raw_material(self):
        try:
            raw_material_item = RawMaterialCRUD(self.db).all_transformed_raw_material()

        except Exception as e:
            raise RawMaterialNotFoundException(detail=f"Error: {str(e)}")
        return raw_material_item



    def get_raw_material(self, rm_code: str):
        try:
            raw_material_item = RawMaterialCRUD(self.db).get_raw_material(rm_code)

        except Exception as e:
            raise RawMaterialNotFoundException(detail=f"Error: {str(e)}")
        return raw_material_item


    # This is the service/business logic in updating the raw_material.
    def update_raw_material(self, rm_id: UUID, raw_material_update: RawMaterialUpdate):
        raw_material = RawMaterialCRUD(self.db).update_raw_material(rm_id, raw_material_update)
        return raw_material

    # This is the service/business logic in soft deleting the raw_material.
    def soft_delete_raw_material(self, rm_id: UUID):
        raw_material = RawMaterialCRUD(self.db).soft_delete_raw_material(rm_id)
        return raw_material


    # This is the service/business logic in soft restoring the raw_material.
    def restore_raw_material(self, rm_id: UUID):
        raw_material = RawMaterialCRUD(self.db).restore_raw_material(rm_id)
        return raw_material

    def import_raw_material(self, content):
        # Convert bytes to a BytesIO stream
        excel_data = io.BytesIO(content)

        # Read the Excel file
        df = pd.read_excel(excel_data, engine='openpyxl')

        # Check if the required "rm_code" column exists and is the only column
        if list(df.columns) != ["rm_code"]:
            raise ValueError("Invalid file format. The Excel file must contain only one column named 'rm_code'.")

        # Get existing rm_codes from the database
        existing_rm_codes = {item.rm_code for item in self.db.query(RawMaterial.rm_code).all()}

        # Track successful and skipped inserts
        success_count = 0
        skipped_count = 0

        # Process each row
        for _, row in df.iterrows():
            rm_code = str(row["rm_code"]).strip()  # Ensure it's a string and remove whitespace

            if rm_code in existing_rm_codes:
                skipped_count += 1  # Skip existing rm_codes
                continue

            try:
                new_raw_material = RawMaterial(rm_code=rm_code)
                self.db.add(new_raw_material)
                self.db.commit()
                success_count += 1
                existing_rm_codes.add(rm_code)  # Add to existing set to prevent further duplicates
            except Exception:
                self.db.rollback()

        return {
            "message": "Data import completed.",
            "successful_inserts": success_count,
            "skipped_duplicates": skipped_count,
        }



