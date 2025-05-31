from backend.api_adjustment_form.v1_spillage.exceptions import (AdjustmentFormNotFoundException,
                                                                AdjustmentFormUpdateException,
                                                                AdjustmentFormSoftDeleteException,
                                                                AdjustmentFormRestoreException
                                                                )
from backend.api_status.v1.models import Status
from backend.api_adjustment_form.v1_spillage.main import AppCRUD
from backend.api_adjustment_form.v1_spillage.models import AdjustmentForm
from backend.api_adjustment_form.v1_spillage.schemas import AdjustmentFormCreate, AdjustmentFormUpdate
from uuid import UUID
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_warehouses.v1.models import Warehouse
from sqlalchemy import or_, desc
from sqlalchemy import text


# These are the code for the app to communicate to the database
class AdjustmentFormCRUD(AppCRUD):



    def get_deviation_report(self):

        def get_qty_comparison(db: Session):
            query = text("""
                SELECT
                    ove.rmcode AS rm,
                    ove.qty AS francis_qty,
                    ir.ending_Inv AS jarick_qty,
                    (ove.qty - ir.ending_inv) AS deviation
                FROM rm_overall_ending ove
                INNER JOIN rm_inventory_report AS ir
                    ON ove.rmcode = ir.matcode
            """)
            result = db.execute(query)
            return result.fetchall()

    def get_deleted_adjustment_form(self):
        """
             Join StockOnHand, OutgoingReport, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                AdjustmentForm.id,
                RawMaterial.rm_code.label("raw_material"),
                AdjustmentForm.qty_kg,
                AdjustmentForm.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                AdjustmentForm.adjustment_date,
                AdjustmentForm.reference_date,
                AdjustmentForm.reason,
                AdjustmentForm.ref_form,
                AdjustmentForm.ref_form_number,
                AdjustmentForm.created_at,
                AdjustmentForm.updated_at,
                AdjustmentForm.date_computed

            )

            .join(RawMaterial, AdjustmentForm.rm_code_id == RawMaterial.id)  # Join AdjustmentForm with RawMaterial
            .join(Warehouse, AdjustmentForm.warehouse_id == Warehouse.id)  # Join AdjustmentForm with Warehouse
            .join(Status, AdjustmentForm.status_id == Status.id)
            .filter(
                    AdjustmentForm.is_cleared == True,  # False check for is_cleared
                    AdjustmentForm.is_deleted == True  # False check for is_deleted
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
                AdjustmentForm.id,
                RawMaterial.rm_code.label("raw_material"),
                AdjustmentForm.qty_kg,
                AdjustmentForm.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                AdjustmentForm.adjustment_date,
                AdjustmentForm.reference_date,
                AdjustmentForm.reason,
                AdjustmentForm.ref_form,
                AdjustmentForm.ref_form_number,
                AdjustmentForm.created_at,
                AdjustmentForm.updated_at,
                AdjustmentForm.date_computed

            )

            .join(RawMaterial, AdjustmentForm.rm_code_id == RawMaterial.id)  # Join AdjustmentForm with RawMaterial
            .join(Warehouse, AdjustmentForm.warehouse_id == Warehouse.id)  # Join AdjustmentForm with Warehouse
            .join(Status, AdjustmentForm.status_id == Status.id)
            .filter(
                    # AdjustmentForm.is_cleared == True,  # False check for is_cleared
                        AdjustmentForm.date_computed.is_not(None),
                    or_(
                        AdjustmentForm.is_deleted.is_(None),  # NULL check for is_deleted
                        AdjustmentForm.is_deleted == False  # False check for is_deleted
                    )
            )
        )

        # Return All the result
        return stmt.all()

    def update_adjustment_form(self, adjustment_form_id: UUID, adjustment_form_update: AdjustmentFormUpdate):
        try:
            adjustment_form = self.db.query(AdjustmentForm).filter(AdjustmentForm.id == adjustment_form_id).first()
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
            adjustment_form = self.db.query(AdjustmentForm).filter(AdjustmentForm.id == adjustment_form_id).first()
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
            adjustment_form = self.db.query(AdjustmentForm).filter(AdjustmentForm.id == adjustment_form_id).first()
            if not adjustment_form or not adjustment_form.is_deleted:
                raise AdjustmentFormNotFoundException(detail="Adjustment Form Record not found or already restored.")

            adjustment_form.is_deleted = False
            self.db.commit()
            self.db.refresh(adjustment_form)
            return adjustment_form

        except Exception as e:
            raise AdjustmentFormRestoreException(detail=f"Error: {str(e)}")