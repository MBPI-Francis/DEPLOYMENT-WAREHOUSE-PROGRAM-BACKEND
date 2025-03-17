from backend.api_preparation_form.v1.exceptions import (TempPreparationFormNotFoundException,
                                                        TempPreparationFormUpdateException,
                                                        TempPreparationFormSoftDeleteException,
                                                        TempPreparationFormRestoreException
                                                        )
from backend.api_preparation_form.v1.main import AppCRUD
from backend.api_preparation_form.v1.models import TempPreparationForm
from backend.api_preparation_form.v1.schemas import TempPreparationFormCreate, TempPreparationFormUpdate
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_warehouses.v1.models import Warehouse
from backend.api_status.v1.models import Status
from sqlalchemy import or_
from uuid import UUID


# These are the code for the app to communicate to the database
class TempPreparationFormCRUD(AppCRUD):

    def create_preparation_form(self, preparation_form: TempPreparationFormCreate):

        preparation_form_item = TempPreparationForm(rm_code_id=preparation_form.rm_code_id,
                                                    warehouse_id=preparation_form.warehouse_id,
                                                    ref_number=preparation_form.ref_number,
                                                    preparation_date=preparation_form.preparation_date,
                                                    qty_prepared=preparation_form.qty_prepared,
                                                    qty_return=preparation_form.qty_return,
                                                    status_id=preparation_form.status_id
                                                    )

        self.db.add(preparation_form_item)
        self.db.commit()
        self.db.refresh(preparation_form_item)
        return preparation_form_item

    def get_preparation_form(self):

        """
             Join StockOnHand, TempPreparationForm, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                TempPreparationForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempPreparationForm.qty_prepared,
                TempPreparationForm.qty_return,
                TempPreparationForm.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempPreparationForm.preparation_date,
                TempPreparationForm.created_at,
                TempPreparationForm.updated_at,
                TempPreparationForm.date_computed

            )

            .join(RawMaterial, TempPreparationForm.rm_code_id == RawMaterial.id)  # Join TempPreparationForm with RawMaterial
            .join(Warehouse, TempPreparationForm.warehouse_id == Warehouse.id)  # Join TempPreparationForm with Warehouse
            .join(Status, TempPreparationForm.status_id == Status.id)
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                or_(
                    TempPreparationForm.is_cleared.is_(None),  # NULL check for is_cleared
                    TempPreparationForm.is_cleared == False  # False check for is_cleared
                ),
                or_(
                    TempPreparationForm.is_deleted.is_(None),  # NULL check for is_deleted
                    TempPreparationForm.is_deleted == False  # False check for is_deleted
                )
            )
        )

        # Return All the result
        return stmt.all()

    def get_deleted_preparation_form(self):

        """
             Join StockOnHand, TempPreparationForm, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                TempPreparationForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempPreparationForm.qty_prepared,
                TempPreparationForm.qty_return,
                TempPreparationForm.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempPreparationForm.preparation_date,
                TempPreparationForm.created_at,
                TempPreparationForm.updated_at,
                TempPreparationForm.date_computed

            )

            .join(RawMaterial, TempPreparationForm.rm_code_id == RawMaterial.id)  # Join TempPreparationForm with RawMaterial
            .join(Warehouse, TempPreparationForm.warehouse_id == Warehouse.id)  # Join TempPreparationForm with Warehouse
            .join(Status, TempPreparationForm.status_id == Status.id)
            .filter(
                    TempPreparationForm.is_deleted == True  # False check for is_deleted
            )
        )

        # Return All the result
        return stmt.all()

    def get_historical_preparation_form(self):

        """
             Join StockOnHand, TempPreparationForm, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                TempPreparationForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempPreparationForm.qty_prepared,
                TempPreparationForm.qty_return,
                TempPreparationForm.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempPreparationForm.preparation_date,
                TempPreparationForm.created_at,
                TempPreparationForm.updated_at,
                TempPreparationForm.date_computed

            )

            .join(RawMaterial, TempPreparationForm.rm_code_id == RawMaterial.id)  # Join TempPreparationForm with RawMaterial
            .join(Warehouse, TempPreparationForm.warehouse_id == Warehouse.id)  # Join TempPreparationForm with Warehouse
            .join(Status, TempPreparationForm.status_id == Status.id)
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                #     TempPreparationForm.is_cleared == True,  # False check for is_cleared
                    TempPreparationForm.date_computed.is_not(None)
                ,
                or_(
                    TempPreparationForm.is_deleted.is_(None),  # NULL check for is_deleted
                    TempPreparationForm.is_deleted == False  # False check for is_deleted
                )

            )
        )

        # Return All the result
        return stmt.all()



    def update_preparation_form(self, preparation_form_id: UUID, preparation_form_update: TempPreparationFormUpdate):
        try:
            preparation_form = self.db.query(TempPreparationForm).filter(TempPreparationForm.id == preparation_form_id).first()
            if not preparation_form or preparation_form.is_deleted:
                raise TempPreparationFormNotFoundException(detail="Preparation Form not found or already deleted.")

            for key, value in preparation_form_update.dict(exclude_unset=True).items():
                setattr(preparation_form, key, value)
            self.db.commit()
            self.db.refresh(preparation_form)
            return self.get_preparation_form()

        except Exception as e:
            raise TempPreparationFormUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_preparation_form(self, preparation_form_id: UUID):
        try:
            preparation_form = self.db.query(TempPreparationForm).filter(TempPreparationForm.id == preparation_form_id).first()
            if not preparation_form or preparation_form.is_deleted:
                raise TempPreparationFormNotFoundException(detail="Preparation Form not found or already deleted.")

            preparation_form.is_deleted = True
            self.db.commit()
            self.db.refresh(preparation_form)
            return self.get_preparation_form()

        except Exception as e:
            raise TempPreparationFormSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_preparation_form(self, preparation_form_id: UUID):
        try:
            preparation_form = self.db.query(TempPreparationForm).filter(TempPreparationForm.id == preparation_form_id).first()
            if not preparation_form or not preparation_form.is_deleted:
                raise TempPreparationFormNotFoundException(detail="Preparation Form not found or already restored.")

            preparation_form.is_deleted = False
            self.db.commit()
            self.db.refresh(preparation_form)
            return preparation_form

        except Exception as e:
            raise TempPreparationFormRestoreException(detail=f"Error: {str(e)}")

