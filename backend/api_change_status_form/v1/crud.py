from backend.api_change_status_form.v1.exceptions import (TempHeldFormNotFoundException,
                                                          TempHeldFormUpdateException,
                                                          TempHeldFormSoftDeleteException,
                                                          TempHeldFormRestoreException
                                                          )
from backend.api_change_status_form.v1.main import AppCRUD
from backend.api_change_status_form.v1.models import TempHeldForm
from backend.api_change_status_form.v1.schemas import TempHeldFormCreate, TempHeldFormUpdate
from uuid import UUID
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_warehouses.v1.models import Warehouse
from backend.api_stock_on_hand.v1.models import StockOnHand
from backend.api_status.v1.models import Status
from sqlalchemy import or_, desc
from sqlalchemy.orm import aliased
from sqlalchemy import text


# These are the code for the app to communicate to the database
class TempHeldFormCRUD(AppCRUD):

    def create_held_form(self, held_form: TempHeldFormCreate):


        # Check if the status id is null
        query = text("""SELECT * FROM view_beginning_soh
                        WHERE warehouseid = :warehouse_id
                              AND rawmaterialid = :rm_code_id
                              AND statusid = :status_id""")



        record = self.db.execute(query, {
            "warehouse_id": held_form.warehouse_id,
            "rm_code_id": held_form.rm_code_id,
            "status_id": held_form.new_status_id
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
                rm_code_id=held_form.rm_code_id,
                warehouse_id=held_form.warehouse_id,
                rm_soh=0.00,
                status_id=held_form.new_status_id,
                date_computed=date_computed,
                stock_recalculation_count=stock_recalculation_count
            )

            self.db.add(new_stock)
            self.db.commit()
            self.db.refresh(new_stock)


        held_form_item = TempHeldForm(
            rm_code_id=held_form.rm_code_id,
            warehouse_id=held_form.warehouse_id,
            ref_number=held_form.ref_number,
            change_status_date=held_form.change_status_date,
            qty_kg=held_form.qty_kg,
            current_status_id=held_form.current_status_id,
            new_status_id=held_form.new_status_id
        )

        self.db.add(held_form_item)
        self.db.commit()
        self.db.refresh(held_form_item)
        return held_form_item

    def get_held_form(self):

        """
             Join StockOnHand, TempHeldForm, Warehouse, and RawMaterial tables.
             """

        # Create aliases for the Warehouse model
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")


        # Join tables
        stmt = (
            self.db.query(
                TempHeldForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempHeldForm.qty_kg,
                TempHeldForm.ref_number,
                Warehouse.wh_name,
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                TempHeldForm.change_status_date,
                TempHeldForm.created_at,
                TempHeldForm.updated_at,
                TempHeldForm.date_computed

            )
            .join(RawMaterial, TempHeldForm.rm_code_id == RawMaterial.id)  # Join TempHeldForm with RawMaterial
            .join(Warehouse, TempHeldForm.warehouse_id == Warehouse.id)  # Join TempHeldForm with Warehouse
            .join(CurrentStatus, TempHeldForm.current_status_id == CurrentStatus.id)  # Join TempHeldForm with CurrentStatus
            .join(NewStatus, TempHeldForm.new_status_id == NewStatus.id)  # Join TempHeldForm with NewStatus
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                or_(
                    TempHeldForm.is_cleared.is_(None),  # NULL check for is_cleared
                    TempHeldForm.is_cleared == False  # False check for is_cleared
                ),
                or_(
                    TempHeldForm.is_deleted.is_(None),  # NULL check for is_deleted
                    TempHeldForm.is_deleted == False  # False check for is_deleted
                )
            )

            .order_by(desc(TempHeldForm.created_at))  # Order from newest to oldest

        )

        if stmt.all():
            # Return All the result
            return stmt.all()

        else:
            return []







        # held_form_item = self.db.query(TempHeldForm).all()
        # if held_form_item:
        #     return held_form_item
        # return []

    def get_deleted_held_form(self):

        """
             Join StockOnHand, TempHeldForm, Warehouse, and RawMaterial tables.
             """

        # Create aliases for the Warehouse model
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")

        # Join tables
        stmt = (
            self.db.query(
                TempHeldForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempHeldForm.qty_kg,
                TempHeldForm.ref_number,
                Warehouse.wh_name,
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                TempHeldForm.change_status_date,
                TempHeldForm.created_at,
                TempHeldForm.updated_at,
                TempHeldForm.date_computed

            )
            .join(RawMaterial, TempHeldForm.rm_code_id == RawMaterial.id)  # Join TempHeldForm with RawMaterial
            .join(Warehouse, TempHeldForm.warehouse_id == Warehouse.id)  # Join TempHeldForm with Warehouse
            .join(CurrentStatus,
                  TempHeldForm.current_status_id == CurrentStatus.id)  # Join TempHeldForm with CurrentStatus
            .join(NewStatus, TempHeldForm.new_status_id == NewStatus.id)  # Join TempHeldForm with NewStatus
            .filter(
                    TempHeldForm.is_deleted == True  # False check for is_deleted
            )

        )

        if stmt.all():
            # Return All the result
            return stmt.all()

        else:
            return []



    def get_historical_held_form(self):

        """
             Join StockOnHand, TempHeldForm, Warehouse, and RawMaterial tables.
             """

        # Create aliases for the Warehouse model
        CurrentStatus = aliased(Status, name="current_status")
        NewStatus = aliased(Status, name="new_status")

        # Join tables
        stmt = (
            self.db.query(
                TempHeldForm.id,
                RawMaterial.rm_code.label("raw_material"),
                TempHeldForm.qty_kg,
                TempHeldForm.ref_number,
                Warehouse.wh_name,
                CurrentStatus.name.label("current_status"),
                NewStatus.name.label("new_status"),
                TempHeldForm.change_status_date,
                TempHeldForm.created_at,
                TempHeldForm.updated_at,
                TempHeldForm.date_computed

            )
            .join(RawMaterial, TempHeldForm.rm_code_id == RawMaterial.id)  # Join TempHeldForm with RawMaterial
            .join(Warehouse, TempHeldForm.warehouse_id == Warehouse.id)  # Join TempHeldForm with Warehouse
            .join(CurrentStatus,
                  TempHeldForm.current_status_id == CurrentStatus.id)  # Join TempHeldForm with CurrentStatus
            .join(NewStatus, TempHeldForm.new_status_id == NewStatus.id)  # Join TempHeldForm with NewStatus
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                #     TempHeldForm.is_cleared == True,  # False check for is_cleared
                TempHeldForm.date_computed.is_not(None)
                ,
                or_(
                    TempHeldForm.is_deleted.is_(None),  # NULL check for is_deleted
                    TempHeldForm.is_deleted == False  # False check for is_deleted
                )
            )

        )

        if stmt.all():
            # Return All the result
            return stmt.all()

        else:
            return []


    def update_held_form(self, held_form_id: UUID, held_form_update: TempHeldFormUpdate):
        try:
            held_form = self.db.query(TempHeldForm).filter(TempHeldForm.id == held_form_id).first()
            if not held_form or held_form.is_deleted:
                raise TempHeldFormNotFoundException(detail="Held Form not found or already deleted.")

            for key, value in held_form_update.dict(exclude_unset=True).items():
                setattr(held_form, key, value)
            self.db.commit()
            self.db.refresh(held_form)
            return self.get_held_form()

        except Exception as e:
            raise TempHeldFormUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_held_form(self, held_form_id: UUID):
        try:
            held_form = self.db.query(TempHeldForm).filter(TempHeldForm.id == held_form_id).first()
            if not held_form or held_form.is_deleted:
                raise TempHeldFormNotFoundException(detail="Held Form not found or already deleted.")

            held_form.is_deleted = True
            self.db.commit()
            self.db.refresh(held_form)
            return self.get_held_form()

        except Exception as e:
            raise TempHeldFormSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_held_form(self, held_form_id: UUID):
        try:
            held_form = self.db.query(TempHeldForm).filter(TempHeldForm.id == held_form_id).first()
            if not held_form or not held_form.is_deleted:
                raise TempHeldFormNotFoundException(detail="Held Form not found or already restored.")

            held_form.is_deleted = False
            self.db.commit()
            self.db.refresh(held_form)
            return held_form

        except Exception as e:
            raise TempHeldFormRestoreException(detail=f"Error: {str(e)}")