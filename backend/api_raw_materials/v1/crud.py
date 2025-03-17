from backend.api_raw_materials.v1.exceptions import (RawMaterialNotFoundException,
                                                     RawMaterialUpdateException,
                                                     RawMaterialSoftDeleteException,
                                                     RawMaterialRestoreException
                                                     )
from backend.api_raw_materials.v1.main import AppCRUD
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_raw_materials.v1.schemas import RawMaterialCreate, RawMaterialUpdate
from backend.api_users.v1.models import User
from sqlalchemy.sql import func
from uuid import UUID
from sqlalchemy.exc import IntegrityError


# These are the code for the app to communicate to the database
class RawMaterialCRUD(AppCRUD):
    def create_raw_material(self, raw_material: RawMaterialCreate):
        # Normalize the input: Remove spaces and convert to uppercase
        normalized_rm_code = raw_material.rm_code.replace(" ", "").upper()

        # Check if an existing raw material has the same normalized rm_code
        existing_rm = self.db.query(RawMaterial).filter(
            func.replace(func.upper(RawMaterial.rm_code), " ", "") == normalized_rm_code
        ).first()

        if existing_rm:
            raise Exception(status_code=400, detail="Raw material code already exists.")


        else:
            # If no duplicate, proceed with creation
            raw_material_item = RawMaterial(
                rm_code=raw_material.rm_code,
                description=raw_material.description,
                rm_name=raw_material.rm_name,
                updated_by_id=raw_material.updated_by_id,
                created_by_id=raw_material.created_by_id
            )

            try:
                self.db.add(raw_material_item)
                self.db.commit()
                self.db.refresh(raw_material_item)
                return raw_material_item
            except IntegrityError:
                self.db.rollback()
                raise Exception(status_code=500, detail="Error while creating raw material.")

    def import_raw_material(self, rm_code):
        # Insert data into the StockOnHand table
        new_raw_material = RawMaterial(
            rm_code=rm_code
        )
        self.db.add(new_raw_material)
        self.db.commit()
        self.db.refresh(new_raw_material)

    def all_raw_material(self):
        raw_material_item = self.db.query(RawMaterial).all()
        if raw_material_item:
            return raw_material_item
        return []

    def all_transformed_raw_material(self):
        # Join tables
        stmt = (
            self.db.query(
                RawMaterial.id.label("id"),
                RawMaterial.rm_code,
                RawMaterial.created_at,
                RawMaterial.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")

            )
            .outerjoin(User,
                       User.id == RawMaterial.created_by_id)  # Left join StockOnHand with ReceivingReport

        )

        # Return All the result
        return stmt.all()

    def get_raw_material(self, rm_code):

        computed_detail_item = (
            self.db.query(RawMaterial).filter(
                RawMaterial.rm_code == rm_code
            ).first()
        )
        if computed_detail_item:
            return computed_detail_item
        return None


    def update_raw_material(self, rm_id: UUID, raw_material_update: RawMaterialUpdate):
        try:
            raw_material = self.db.query(RawMaterial).filter(RawMaterial.id == rm_id).first()
            if not raw_material or raw_material.is_deleted:
                raise RawMaterialNotFoundException(detail="Raw Material not found or already deleted.")

            for key, value in raw_material_update.dict(exclude_unset=True).items():
                setattr(raw_material, key, value)
            self.db.commit()
            self.db.refresh(raw_material)
            return raw_material

        except Exception as e:
            raise RawMaterialUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_raw_material(self, rm_id: UUID):
        try:
            raw_material = self.db.query(RawMaterial).filter(RawMaterial.id == rm_id).first()
            if not raw_material or raw_material.is_deleted:
                raise RawMaterialNotFoundException(detail="Raw Material not found or already deleted.")

            raw_material.is_deleted = True
            self.db.commit()
            self.db.refresh(raw_material)
            return raw_material

        except Exception as e:
            raise RawMaterialSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_raw_material(self, rm_id: UUID):
        try:
            raw_material = self.db.query(RawMaterial).filter(RawMaterial.id == rm_id).first()
            if not raw_material or not raw_material.is_deleted:
                raise RawMaterialNotFoundException(detail="Raw Material not found or already restored.")

            raw_material.is_deleted = False
            self.db.commit()
            self.db.refresh(raw_material)
            return raw_material

        except Exception as e:
            raise RawMaterialRestoreException(detail=f"Error: {str(e)}")