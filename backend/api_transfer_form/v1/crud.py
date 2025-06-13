from backend.api_transfer_form.v1.exceptions import (TempTransferFormNotFoundException,
                                                     TempTransferFormUpdateException,
                                                     TempTransferFormSoftDeleteException,
                                                     TempTransferFormRestoreException
                                                     )
from backend.api_transfer_form.v1.main import AppCRUD
from backend.api_transfer_form.v1.models import TempTransferForm
from backend.api_transfer_form.v1.schemas import TempTransferFormCreate, TempTransferFormUpdate
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_warehouses.v1.models import Warehouse
from backend.api_stock_on_hand.v1.models import StockOnHand
from backend.api_status.v1.models import Status
from uuid import UUID
from sqlalchemy import text, desc
from sqlalchemy import or_
from sqlalchemy.orm import aliased


# These are the code for the app to communicate to the database
class TempTransferFormCRUD(AppCRUD):

    def create_transfer_form(self, transfer_form: TempTransferFormCreate):

        # Check if the status id is null
        query = text("""SELECT * FROM view_beginning_soh
                        WHERE warehouseid = :warehouse_id
                              AND rawmaterialid = :rm_code_id
                              AND statusid = :status_id""")

        record = self.db.execute(query, {
            "warehouse_id": transfer_form.to_warehouse_id,
            "rm_code_id": transfer_form.rm_code_id,
            "status_id": transfer_form.status_id
        }).fetchone()  # or .fetchall() if expecting multiple rows
        result = record


        # This feature is required for the calculation
        if not result:

            # Get the date computed date from other existing records
            existing_query = text("""SELECT * FROM view_beginning_soh""")

            existing_record = self.db.execute(existing_query).fetchone()  # or .fetchall() if expecting multiple rows

            # Extract date_computed if record exists, else use None
            date_computed = existing_record[9] if existing_record else None
		
            # Extract the stock_recalculation_count value
            stock_recalculation_count = existing_record[10] if existing_record else None

            # Create a new StockOnHand record
            new_stock = StockOnHand(
                rm_code_id=transfer_form.rm_code_id,
                warehouse_id=transfer_form.to_warehouse_id,
                rm_soh=0.00,
                status_id=transfer_form.status_id,
                date_computed=date_computed,  # Insert retrieved date_computed
 		stock_recalculation_count=stock_recalculation_count  # Insert retrieved stock_recalculation_count
            )
            self.db.add(new_stock)
            self.db.commit()
            self.db.refresh(new_stock)


        transfer_form_item = TempTransferForm(
            rm_code_id=transfer_form.rm_code_id,
            from_warehouse_id=transfer_form.from_warehouse_id,
            to_warehouse_id=transfer_form.to_warehouse_id,
            ref_number=transfer_form.ref_number,
            transfer_date=transfer_form.transfer_date,
            qty_kg=transfer_form.qty_kg,
            status_id=transfer_form.status_id
        )


        self.db.add(transfer_form_item)
        self.db.commit()
        self.db.refresh(transfer_form_item)
        return transfer_form_item

    def get_transfer_form(self):

        # Create aliases for the Warehouse model
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")

        """
        Join StockOnHand, TransferForm, Warehouse, and RawMaterial tables.
        """
        stmt = (
            self.db.query(
                TempTransferForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempTransferForm.qty_kg,
                TempTransferForm.ref_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                TempTransferForm.transfer_date,
                Status.name.label("status"),
                TempTransferForm.created_at,
                TempTransferForm.updated_at,
                TempTransferForm.date_computed
            )

            .outerjoin(Status, Status.id == TempTransferForm.status_id)  # Left join Status with TransferForm
            .join(RawMaterial, TempTransferForm.rm_code_id == RawMaterial.id)  # Join StockOnHand with RawMaterial
            .join(FromWarehouse,
                  TempTransferForm.from_warehouse_id == FromWarehouse.id)  # Join TempTransferForm with Warehouse
            .join(ToWarehouse,
                  TempTransferForm.to_warehouse_id == ToWarehouse.id)  # Join TempTransferForm with Warehouse
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                or_(
                    TempTransferForm.is_cleared.is_(None),  # NULL check for is_cleared
                    TempTransferForm.is_cleared == False # False check for is_cleared
                ),
                or_(
                    TempTransferForm.is_deleted.is_(None),  # NULL check for is_deleted
                    TempTransferForm.is_deleted == False  # False check for is_deleted
                )
            )

            .order_by(desc(TempTransferForm.created_at))  # Order from newest to oldest
        )

        # Return filtered results
        return stmt.all()


    def get_deleted_transfer_form(self):

        # Create aliases for the Warehouse model
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")

        """
        Join StockOnHand, TransferForm, Warehouse, and RawMaterial tables.
        """
        stmt = (
            self.db.query(
                TempTransferForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempTransferForm.qty_kg,
                TempTransferForm.ref_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                TempTransferForm.transfer_date,
                Status.name.label("status"),
                TempTransferForm.created_at,
                TempTransferForm.updated_at,
                TempTransferForm.date_computed
            )

            .outerjoin(Status, Status.id == TempTransferForm.status_id)  # Left join Status with TransferForm
            .join(RawMaterial, TempTransferForm.rm_code_id == RawMaterial.id)  # Join StockOnHand with RawMaterial
            .join(FromWarehouse,
                  TempTransferForm.from_warehouse_id == FromWarehouse.id)  # Join TempTransferForm with Warehouse
            .join(ToWarehouse,
                  TempTransferForm.to_warehouse_id == ToWarehouse.id)  # Join TempTransferForm with Warehouse
            .filter(
                    TempTransferForm.is_deleted == True  # False check for is_deleted
            )
        )

        # Return filtered results
        return stmt.all()


    def get_historical_transfer_form(self, record_id):

        # Create aliases for the Warehouse model
        FromWarehouse = aliased(Warehouse, name="from_warehouse")
        ToWarehouse = aliased(Warehouse, name="to_warehouse")

        """
        Join StockOnHand, TransferForm, Warehouse, and RawMaterial tables.
        """
        stmt = (
            self.db.query(
                TempTransferForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempTransferForm.qty_kg,
                TempTransferForm.ref_number,
                FromWarehouse.wh_name.label("from_warehouse"),
                ToWarehouse.wh_name.label("to_warehouse"),
                TempTransferForm.transfer_date,
                Status.name.label("status"),
                TempTransferForm.created_at,
                TempTransferForm.updated_at,
                TempTransferForm.date_computed,
                TempTransferForm.is_adjusted
            )

            .outerjoin(Status, Status.id == TempTransferForm.status_id)  # Left join Status with TransferForm
            .join(RawMaterial, TempTransferForm.rm_code_id == RawMaterial.id)  # Join StockOnHand with RawMaterial
            .join(FromWarehouse,
                  TempTransferForm.from_warehouse_id == FromWarehouse.id)  # Join TempTransferForm with Warehouse
            .join(ToWarehouse,
                  TempTransferForm.to_warehouse_id == ToWarehouse.id)  # Join TempTransferForm with Warehouse
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                #     TempTransferForm.is_cleared == True,  # False check for is_cleared
                    TempTransferForm.date_computed.is_not(None)
                ,
                or_(
                    TempTransferForm.is_deleted.is_(None),  # NULL check for is_deleted
                    TempTransferForm.is_deleted == False  # False check for is_deleted
                )
            )
        )

        if stmt:
            if record_id:
                stmt = stmt.filter(TempTransferForm.id == record_id)

            return stmt.all()
        else:
            return []


    def update_transfer_form(self, transfer_form_id: UUID, transfer_form_update: TempTransferFormUpdate):
        try:
            transfer_form = self.db.query(TempTransferForm).filter(TempTransferForm.id == transfer_form_id).first()
            if not transfer_form or transfer_form.is_deleted:
                raise TempTransferFormNotFoundException(detail="Transfer Form not found or already deleted.")

            for key, value in transfer_form_update.dict(exclude_unset=True).items():
                setattr(transfer_form, key, value)
            self.db.commit()
            self.db.refresh(transfer_form)
            return self.get_transfer_form()

        except Exception as e:
            raise TempTransferFormUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_transfer_form(self, transfer_form_id: UUID):
        try:
            transfer_form = self.db.query(TempTransferForm).filter(TempTransferForm.id == transfer_form_id).first()
            if not transfer_form or transfer_form.is_deleted:
                raise TempTransferFormNotFoundException(detail="Transfer Form not found or already deleted.")

            transfer_form.is_deleted = True
            self.db.commit()
            self.db.refresh(transfer_form)
            return self.get_transfer_form()

        except Exception as e:
            raise TempTransferFormSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_transfer_form(self, transfer_form_id: UUID):
        try:
            transfer_form = self.db.query(TempTransferForm).filter(TempTransferForm.id == transfer_form_id).first()
            if not transfer_form or not transfer_form.is_deleted:
                raise TempTransferFormNotFoundException(detail="Transfer Form not found or already restored.")

            transfer_form.is_deleted = False
            self.db.commit()
            self.db.refresh(transfer_form)
            return transfer_form

        except Exception as e:
            raise TempTransferFormRestoreException(detail=f"Error: {str(e)}")