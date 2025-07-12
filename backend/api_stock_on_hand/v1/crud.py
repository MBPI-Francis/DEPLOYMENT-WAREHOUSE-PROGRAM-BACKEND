from typing import Optional, List

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
from backend.api_stock_on_hand.v1.schemas import StockOnHandCreate, StockOnHandUpdate, HistoricalStockOnHandResponse
from uuid import UUID
from backend.api_warehouses.v1.models import Warehouse
from sqlalchemy import or_, and_
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

    def get_historical_stock_on_hand(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        mat_code: Optional[str] = None,
        location: Optional[str] = None, # Corresponds to wh_name
        status: Optional[str] = None, # Corresponds to status_name
    ) -> List[HistoricalStockOnHandResponse]: # Changed return type to match schema

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
                StockOnHand.date_computed # Keep this for filtering and display
            )
            .join(RawMaterial, StockOnHand.rm_code_id == RawMaterial.id)
            .join(Warehouse, StockOnHand.warehouse_id == Warehouse.id)
            .outerjoin(Status, StockOnHand.status_id == Status.id)
            .filter(
                StockOnHand.date_computed.is_not(None),
                or_(
                    StockOnHand.is_deleted.is_(None),
                    StockOnHand.is_deleted == False
                )
            )
        )

        # Apply filters based on provided parameters
        if date_from and date_to:
            # Assuming date_computed is a DATE or DATETIME type in your database
            # and date_from/date_to are in 'YYYY-MM-DD' format
            stmt = stmt.filter(
                and_(
                    StockOnHand.date_computed >= date_from,
                    StockOnHand.date_computed <= date_to
                )
            )
        elif date_from: # If only date_from is provided
            stmt = stmt.filter(StockOnHand.date_computed >= date_from)
        elif date_to: # If only date_to is provided
            stmt = stmt.filter(StockOnHand.date_computed <= date_to)


        if mat_code and mat_code.lower() != "all":
            stmt = stmt.filter(RawMaterial.rm_code == mat_code)

        if location and location.lower() != "all":
            stmt = stmt.filter(Warehouse.wh_name == location) # Filter by warehouse name

        if status and status.lower() != "all":
            stmt = stmt.filter(Status.name == status) # Filter by status name

        # Execute query and return results mapped to schema
        # If using SQLAlchemy 2.0 style, it would be db.scalars(stmt).all()
        # For older versions, result = self.db.execute(stmt).fetchall()
        # and then map manually. Assuming your current setup returns a list of rows
        # that can be directly used for HistoricalStockOnHandResponse.
        rows = stmt.all() # Assuming stmt.all() returns rows directly mappable

        # Map results to Pydantic schema
        # Ensure your HistoricalStockOnHandResponse schema matches the selected columns
        return [
            HistoricalStockOnHandResponse(
                wh_id=row.wh_id,
                wh_name=row.wh_name,
                wh_number=row.wh_number,
                rm_id=row.rm_id,
                rm_code=row.rm_code,
                qty=row.qty,
                stock_change_date=row.stock_change_date,
                status_name=row.status_name,
                status_id=row.status_id,
                date_computed=row.date_computed,
            )
            for row in rows
        ]


    def import_rm_soh(self, rm_code_id, total, status_id, warehouse_id, date_computed, count):
        # Insert data into the StockOnHand table

        new_stock_on_hand = StockOnHand(
            rm_code_id=rm_code_id,
            rm_soh=total,
            status_id=status_id,
            warehouse_id=warehouse_id,
            date_computed=date_computed,
            is_imported=True,
            stock_recalculation_count=count
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