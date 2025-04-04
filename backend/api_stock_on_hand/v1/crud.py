from backend.api_status.v1.models import Status
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_stock_on_hand.v1.exceptions import (
                                                     StockOnHandNotFoundException,
                                                     StockOnHandUpdateException,
                                                     StockOnHandSoftDeleteException,
                                                     StockOnHandRestoreException
                                                     )
from backend.api_stock_on_hand.v1.main import AppCRUD
from backend.api_stock_on_hand.v1.models import StockOnHand
from backend.api_stock_on_hand.v1.schemas import StockOnHandCreate, StockOnHandUpdate
from uuid import UUID
from backend.api_warehouses.v1.models import Warehouse
from sqlalchemy import or_
from datetime import date
from sqlalchemy import text

# These are the code for the app to communicate to the database
class StockOnHandCRUD(AppCRUD):

    def create_rm_soh(self, rm_soh: StockOnHandCreate):
        rm_soh_item = StockOnHand(rm_code_id=rm_soh.rm_code_id,
                                  warehouse_id=rm_soh.warehouse_id,
                                  rm_soh=rm_soh.rm_soh,
                                  status_id = rm_soh.status_id,
                                   description=rm_soh.description,
                                   updated_by_id=rm_soh.updated_by_id,
                                   created_by_id=rm_soh.created_by_id)
        self.db.add(rm_soh_item)
        self.db.commit()
        self.db.refresh(rm_soh_item)
        return rm_soh_item

    def all_rm_soh(self):
        rm_soh_item = self.db.query(StockOnHand).all()
        if rm_soh_item:
            return rm_soh_item
        return []

    def get_historical_stock_on_hand(self, date_computed):
        """
        Retrieve historical stock-on-hand records.
        If `date_computed` is provided, filter results by that date.
        """
        # Base query joining necessary tables
        stmt = (
            self.db.query(
                StockOnHand.warehouse_id.label("wh_id"),
                Warehouse.wh_name.label("wh_name"),
                Warehouse.wh_number.label("wh_number"),
                StockOnHand.rm_code_id.label("rm_id"),
                RawMaterial.rm_code.label("rm_code"),
                StockOnHand.rm_soh.label("qty"),
                StockOnHand.stock_change_date.label("stock_change_date"),
                Status.name.label("status_name"),
                StockOnHand.status_id.label("status_id"),
                StockOnHand.date_computed
            )
            .join(RawMaterial, StockOnHand.rm_code_id == RawMaterial.id)  # Join StockOnHand with RawMaterial
            .join(Warehouse, StockOnHand.warehouse_id == Warehouse.id)  # Join StockOnHand with Warehouse
            .outerjoin(Status, StockOnHand.status_id == Status.id)  # Left Join with Status
            .filter(
                StockOnHand.date_computed.is_not(None),  # Ensure date_computed is present
                or_(
                    StockOnHand.is_deleted.is_(None),  # NULL check for is_deleted
                    StockOnHand.is_deleted == False  # False check for is_deleted
                )
            )
        )


        if stmt:
            # Apply date_computed filter if provided
            if date_computed:
                stmt = stmt.filter(StockOnHand.date_computed == date_computed)


            return stmt.all()

        else:
            return []

    def import_rm_soh(self, rm_code_id, total, status_id, warehouse_id, date_computed):
        # Insert data into the StockOnHand table

        # Get the largest stock recalculation count
        existing_query = text("""SELECT MAX(stock_recalculation_count) AS largest_modification 
                                FROM tbl_stock_on_hand;
                                """)

        largest_count = self.db.execute(existing_query).fetchone()  # or .fetchall() if expecting multiple rows
        if largest_count[0]:
            new_stock_recalculation_count = largest_count[0] + 1
        else:
            new_stock_recalculation_count = 1


        new_stock_on_hand = StockOnHand(
            rm_code_id=rm_code_id,
            rm_soh=total,
            status_id=status_id,
            warehouse_id=warehouse_id,
            date_computed=date_computed,
            is_imported=True,
            stock_recalculation_count=new_stock_recalculation_count
        )
        self.db.add(new_stock_on_hand)
        self.db.commit()
        self.db.refresh(new_stock_on_hand)


    def update_rm_soh(self, rm_soh_id: UUID, rm_soh_update: StockOnHandUpdate):
        try:
            rm_soh = self.db.query(StockOnHand).filter(StockOnHand.id == rm_soh_id).first()
            if not rm_soh or rm_soh.is_deleted:
                raise StockOnHandNotFoundException(detail="Raw Material's SOH not found or already deleted.")

            for key, value in rm_soh_update.model_dump(exclude_unset=True).items():
                setattr(rm_soh, key, value)
            self.db.commit()
            self.db.refresh(rm_soh)
            return rm_soh

        except Exception as e:
            raise StockOnHandUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_rm_soh(self, rm_soh_id: UUID):
        try:
            rm_soh = self.db.query(StockOnHand).filter(StockOnHand.id == rm_soh_id).first()
            if not rm_soh or rm_soh.is_deleted:
                raise StockOnHandNotFoundException(detail="Raw Material's SOH not found or already deleted.")

            rm_soh.is_deleted = True
            self.db.commit()
            self.db.refresh(rm_soh)
            return rm_soh

        except Exception as e:
            raise StockOnHandSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_rm_soh(self, rm_soh_id: UUID):
        try:
            rm_soh = self.db.query(StockOnHand).filter(StockOnHand.id == rm_soh_id).first()
            if not rm_soh or not rm_soh.is_deleted:
                raise StockOnHandNotFoundException(detail="Raw Material's SOH not found or already restored.")

            rm_soh.is_deleted = False
            self.db.commit()
            self.db.refresh(rm_soh)
            return rm_soh

        except Exception as e:
            raise StockOnHandRestoreException(detail=f"Error: {str(e)}")