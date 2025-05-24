from backend.api_adjustment_form.v1_form_entries.exceptions import (AdjustmentFormNotFoundException,
                                                                AdjustmentFormUpdateException,
                                                                AdjustmentFormSoftDeleteException,
                                                                AdjustmentFormRestoreException
                                                                )
from backend.api_change_status_form.v1.models import TempHeldForm
from backend.api_outgoing_report.v1.models import TempOutgoingReport
from backend.api_preparation_form.v1.models import TempPreparationForm
from backend.api_receiving_report.v1.models import TempReceivingReport
from backend.api_status.v1.models import Status
from backend.api_adjustment_form.v1_form_entries.main import AppCRUD
from backend.api_adjustment_form.v1_form_entries.models import AdjustmentFormParent, AdjustmentFormCorrect
from backend.api_adjustment_form.v1_form_entries.schemas import AdjustmentFormCreate, AdjustmentFormUpdate
from uuid import UUID
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_transfer_form.v1.models import TempTransferForm
from backend.api_warehouses.v1.models import Warehouse
from sqlalchemy import or_, desc
from sqlalchemy.orm import aliased


# These are the code for the app to communicate to the database
class AdjustmentFormCRUD(AppCRUD):


    def create_adjustment_form(self, adjustment_form: AdjustmentFormCreate, form: str):

        child_record = None
        # Step 1: Create parent record
        parent_record = AdjustmentFormParent(
            ref_number=adjustment_form.ref_number,
            adjustment_date=adjustment_form.adjustment_date,
            reference_date=adjustment_form.reference_date,
            adjustment_type=adjustment_form.adjustment_type,
            responsible_person=adjustment_form.responsible_person,
        )
        self.db.add(parent_record)
        self.db.flush()  # Get parent.id without committing yet

        # Step 2: Create corresponding child
        if form == "receiving form":
            child_record = AdjustmentFormCorrect(
                adjustment_parent_id=parent_record.id,
                rm_code_id=adjustment_form.rm_code_id,
                warehouse_id=adjustment_form.warehouse_id,
                status_id=adjustment_form.status_id,
                qty_kg=adjustment_form.qty_kg,
            )


        elif form == "outgoing form":
            child_record = AdjustmentFormCorrect(
                adjustment_parent_id=parent_record.id,
                rm_code_id=adjustment_form.rm_code_id,
                warehouse_id=adjustment_form.warehouse_id,
                status_id=adjustment_form.status_id,
                qty_kg=adjustment_form.qty_kg,
            )

        elif form == "preparation form":
            child_record = AdjustmentFormCorrect(
                adjustment_parent_id=parent_record.id,
                rm_code_id=adjustment_form.rm_code_id,
                warehouse_id=adjustment_form.warehouse_id,
                status_id=adjustment_form.status_id,
                qty_prepared=adjustment_form.qty_prepared,
                qty_return=adjustment_form.qty_return,
            )


        elif form == "transfer form":
            child_record = AdjustmentFormCorrect(
                adjustment_parent_id=parent_record.id,
                rm_code_id=adjustment_form.rm_code_id,
                from_warehouse_id=adjustment_form.from_warehouse_id,
                to_warehouse_id=adjustment_form.to_warehouse_id,
                status_id=adjustment_form.status_id,
                qty_kg=adjustment_form.qty_kg,
            )


        elif form == "change status form":
            child_record = AdjustmentFormCorrect(
                adjustment_parent_id=parent_record.id,
                rm_code_id=adjustment_form.rm_code_id,
                warehouse_id=adjustment_form.warehouse_id,
                current_status_id=adjustment_form.current_status_id,
                new_status_id=adjustment_form.new_status_id,
                qty_kg=adjustment_form.qty_kg,
            )


        self.db.add(child_record)
        self.db.commit()
        self.db.refresh(parent_record)

        return {
            "parent": parent_record,
            "child": child_record
        }

    def get_adjustment_form(self):
        # Create aliases for the Warehouse model
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")


        # Create aliases for the Warehouse model
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")


        stmt = (
            self.db.query(
                AdjustmentFormCorrect.id,
                AdjustmentFormCorrect.incorrect_preparation_id,
                AdjustmentFormCorrect.incorrect_receiving_id,
                AdjustmentFormCorrect.incorrect_outgoing_id,
                AdjustmentFormCorrect.incorrect_transfer_id,
                AdjustmentFormCorrect.incorrect_change_status_id,


                RawMaterial.rm_code.label("raw_material"),
                AdjustmentFormCorrect.qty_kg,
                AdjustmentFormParent.ref_number,
                AdjustmentFormParent.responsible_person,
                Warehouse.wh_name,
                Status.name.label("status"),
                AdjustmentFormParent.adjustment_date,
                AdjustmentFormParent.referenced_date,
                AdjustmentFormCorrect.qty_prepared,
                AdjustmentFormCorrect.qty_return,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                AdjustmentFormCorrect.created_at,
                AdjustmentFormCorrect.updated_at,
                AdjustmentFormCorrect.date_computed

            )
            .join(AdjustmentFormCorrect, AdjustmentFormParent.adjustment_child)  # one-to-one
            .join(RawMaterial, AdjustmentFormCorrect.rm_code_id == RawMaterial.id)
            .outerjoin(Warehouse, AdjustmentFormCorrect.warehouse_id == Warehouse.id)
            .outerjoin(Status, AdjustmentFormCorrect.status_id == Status.id)

            .outerjoin(FromWarehouse,
                  AdjustmentFormCorrect.from_warehouse_id == FromWarehouse.id)  # Join AdjustmentFormCorrect with Warehouse
            .outerjoin(ToWarehouse,
                  AdjustmentFormCorrect.to_warehouse_id == ToWarehouse.id)  # Join AdjustmentFormCorrect with Warehouse

            .outerjoin(CurrentStatus,
                  AdjustmentFormCorrect.current_status_id == CurrentStatus.id)  # Join AdjustmentFormCorrect with CurrentStatus
            .outerjoin(NewStatus, AdjustmentFormCorrect.new_status_id == NewStatus.id)  # Join AdjustmentFormCorrect with NewStatus

            # OUTER JOINS for optional foreign keys
            .outerjoin(TempPreparationForm, AdjustmentFormCorrect.incorrect_preparation_id == TempPreparationForm.id)
            .outerjoin(TempReceivingReport, AdjustmentFormCorrect.incorrect_receiving_id == TempReceivingReport.id)
            .outerjoin(TempOutgoingReport, AdjustmentFormCorrect.incorrect_outgoing_id == TempOutgoingReport.id)
            .outerjoin(TempTransferForm, AdjustmentFormCorrect.incorrect_transfer_id == TempTransferForm.id)
            .outerjoin(TempHeldForm, AdjustmentFormCorrect.incorrect_change_status_id == TempHeldForm.id)

            .filter(
                or_(
                    AdjustmentFormCorrect.is_cleared.is_(None),
                    AdjustmentFormCorrect.is_cleared == False
                ),
                or_(
                    AdjustmentFormCorrect.is_deleted.is_(None),
                    AdjustmentFormCorrect.is_deleted == False
                )
            )
            .order_by(desc(AdjustmentFormCorrect.created_at))
        )

        return stmt.all()

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