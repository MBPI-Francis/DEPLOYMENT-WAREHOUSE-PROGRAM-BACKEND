from backend.api_adjustment_form.v1_spillage.exceptions import (AdjustmentFormNotFoundException,
                                                                AdjustmentFormUpdateException,
                                                                AdjustmentFormSoftDeleteException,
                                                                AdjustmentFormRestoreException
                                                                )
from backend.api_status.v1.models import Status
from backend.api_adjustment_form.v1_spillage.main import AppCRUD
from backend.api_adjustment_form.v1_spillage.models import SpillageAdjustmentForm
from backend.api_adjustment_form.v1_spillage.schemas import AdjustmentFormCreate, AdjustmentFormUpdate
from uuid import UUID
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_warehouses.v1.models import Warehouse
from sqlalchemy import or_, desc


# These are the code for the app to communicate to the database
class AdjustmentFormCRUD(AppCRUD):


    def create_adjustment_form(self, adjustment_form: AdjustmentFormCreate):

        adjustment_form_item = SpillageAdjustmentForm(
                                            rm_code_id=adjustment_form.rm_code_id,
                                            warehouse_id=adjustment_form.warehouse_id,
                                            ref_number=adjustment_form.ref_number,
                                            reference_date=adjustment_form.reference_date,
                                            adjustment_date=adjustment_form.adjustment_date,
                                            qty_kg=adjustment_form.qty_kg,
                                            status_id = adjustment_form.status_id,
                                            incident_date=adjustment_form.incident_date,
                                            spillage_form_number=adjustment_form.spillage_form_number,
                                            responsible_person=adjustment_form.responsible_person,
                                            )


        self.db.add(adjustment_form_item)
        self.db.commit()
        self.db.refresh(adjustment_form_item)
        # return self.get_adjustment_form()
        return adjustment_form_item

    def get_adjustment_form(self):
        """
             Join StockOnHand, OutgoingReport, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                SpillageAdjustmentForm.id,
                RawMaterial.rm_code.label("raw_material"),
                SpillageAdjustmentForm.qty_kg,
                SpillageAdjustmentForm.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                SpillageAdjustmentForm.adjustment_date,
                SpillageAdjustmentForm.reference_date,
                SpillageAdjustmentForm.spillage_form_number,
                SpillageAdjustmentForm.responsible_person,
                SpillageAdjustmentForm.incident_date,
                SpillageAdjustmentForm.created_at,
                SpillageAdjustmentForm.updated_at,
                SpillageAdjustmentForm.date_computed

            )

            .join(RawMaterial, SpillageAdjustmentForm.rm_code_id == RawMaterial.id)  # Join SpillageAdjustmentForm with RawMaterial
            .join(Warehouse, SpillageAdjustmentForm.warehouse_id == Warehouse.id)  # Join SpillageAdjustmentForm with Warehouse
            .join(Status, SpillageAdjustmentForm.status_id == Status.id)
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                or_(
                    SpillageAdjustmentForm.is_cleared.is_(None),  # NULL check for is_cleared
                    SpillageAdjustmentForm.is_cleared == False  # False check for is_cleared
                ),
                or_(
                    SpillageAdjustmentForm.is_deleted.is_(None),  # NULL check for is_deleted
                    SpillageAdjustmentForm.is_deleted == False  # False check for is_deleted
                )
            )

            .order_by(desc(SpillageAdjustmentForm.created_at))  # Order from newest to oldest
        )

        # Return All the result
        return stmt.all()

    def get_deleted_adjustment_form(self):
        """
             Join StockOnHand, OutgoingReport, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                SpillageAdjustmentForm.id,
                RawMaterial.rm_code.label("raw_material"),
                SpillageAdjustmentForm.qty_kg,
                SpillageAdjustmentForm.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                SpillageAdjustmentForm.adjustment_date,
                SpillageAdjustmentForm.reference_date,
                SpillageAdjustmentForm.spillage_form_number,
                SpillageAdjustmentForm.responsible_person,
                SpillageAdjustmentForm.incident_date,
                SpillageAdjustmentForm.created_at,
                SpillageAdjustmentForm.updated_at,
                SpillageAdjustmentForm.date_computed

            )

            .join(RawMaterial, SpillageAdjustmentForm.rm_code_id == RawMaterial.id)  # Join SpillageAdjustmentForm with RawMaterial
            .join(Warehouse, SpillageAdjustmentForm.warehouse_id == Warehouse.id)  # Join SpillageAdjustmentForm with Warehouse
            .join(Status, SpillageAdjustmentForm.status_id == Status.id)
            .filter(
                    SpillageAdjustmentForm.is_cleared == True,  # False check for is_cleared
                    SpillageAdjustmentForm.is_deleted == True  # False check for is_deleted
            )
        )

        # Return All the result
        return stmt.all()

    def get_historical_adjustment_form(self):
        """
             Join StockOnHand, OutgoingReport, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                SpillageAdjustmentForm.id,
                RawMaterial.rm_code.label("raw_material"),
                SpillageAdjustmentForm.qty_kg,
                SpillageAdjustmentForm.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                SpillageAdjustmentForm.adjustment_date,
                SpillageAdjustmentForm.reference_date,
                SpillageAdjustmentForm.spillage_form_number,
                SpillageAdjustmentForm.responsible_person,
                SpillageAdjustmentForm.incident_date,
                SpillageAdjustmentForm.created_at,
                SpillageAdjustmentForm.updated_at,
                SpillageAdjustmentForm.date_computed

            )

            .join(RawMaterial, SpillageAdjustmentForm.rm_code_id == RawMaterial.id)  # Join SpillageAdjustmentForm with RawMaterial
            .join(Warehouse, SpillageAdjustmentForm.warehouse_id == Warehouse.id)  # Join SpillageAdjustmentForm with Warehouse
            .join(Status, SpillageAdjustmentForm.status_id == Status.id)
            .filter(
                    # SpillageAdjustmentForm.is_cleared == True,  # False check for is_cleared
                        SpillageAdjustmentForm.date_computed.is_not(None),
                    or_(
                        SpillageAdjustmentForm.is_deleted.is_(None),  # NULL check for is_deleted
                        SpillageAdjustmentForm.is_deleted == False  # False check for is_deleted
                    )
            )
        )

        # Return All the result
        return stmt.all()

    def update_adjustment_form(self, adjustment_form_id: UUID, adjustment_form_update: AdjustmentFormUpdate):
        try:
            adjustment_form = self.db.query(SpillageAdjustmentForm).filter(SpillageAdjustmentForm.id == adjustment_form_id).first()
            if not adjustment_form or adjustment_form.is_deleted:
                raise AdjustmentFormNotFoundException(detail="Adjustment Form Record not found or already deleted.")

            for key, value in adjustment_form_update.dict(exclude_unset=True).items():
                setattr(adjustment_form, key, value)
            self.db.commit()
            self.db.refresh(adjustment_form)
            return self.get_adjustment_form()

        except Exception as e:
            raise AdjustmentFormUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_adjustment_form(self, adjustment_form_id: UUID):
        try:
            adjustment_form = self.db.query(SpillageAdjustmentForm).filter(SpillageAdjustmentForm.id == adjustment_form_id).first()
            if not adjustment_form or adjustment_form.is_deleted:
                raise AdjustmentFormNotFoundException(detail="Adjustment Form Record not found or already deleted.")

            adjustment_form.is_deleted = True
            self.db.commit()
            self.db.refresh(adjustment_form)
            return self.get_adjustment_form()

        except Exception as e:
            raise AdjustmentFormSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_adjustment_form(self, adjustment_form_id: UUID):
        try:
            adjustment_form = self.db.query(SpillageAdjustmentForm).filter(SpillageAdjustmentForm.id == adjustment_form_id).first()
            if not adjustment_form or not adjustment_form.is_deleted:
                raise AdjustmentFormNotFoundException(detail="Adjustment Form Record not found or already restored.")

            adjustment_form.is_deleted = False
            self.db.commit()
            self.db.refresh(adjustment_form)
            return adjustment_form

        except Exception as e:
            raise AdjustmentFormRestoreException(detail=f"Error: {str(e)}")