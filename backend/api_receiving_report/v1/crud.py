# These are the code for the app to communicate to the database
from backend.api_receiving_report.v1.exceptions import TempReceivingReportCreateException, TempReceivingReportNotFoundException, \
    TempReceivingReportUpdateException, TempReceivingReportSoftDeleteException, TempReceivingReportRestoreException
from backend.api_receiving_report.v1.main import AppCRUD, AppService
from backend.api_receiving_report.v1.models import TempReceivingReport
from backend.api_receiving_report.v1.schemas import TempReceivingReportCreate, TempReceivingReportUpdate
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_status.v1.models import Status
from backend.api_warehouses.v1.models import Warehouse
from uuid import UUID
from backend.api_stock_on_hand.v1.models import StockOnHand
from sqlalchemy import desc, or_
from sqlalchemy.sql import func, cast, case
from sqlalchemy.types import String
from sqlalchemy import text


class TempReceivingReportCRUD(AppCRUD):
    def create_receiving_report(self, receiving_report: TempReceivingReportCreate):

        # Check if the status id is null
        query = text("""SELECT * FROM view_beginning_soh
                        WHERE warehouseid = :warehouse_id
                              AND rawmaterialid = :rm_code_id
                              AND statusid = :status_id""")



        record = self.db.execute(query, {
            "warehouse_id": receiving_report.warehouse_id,
            "rm_code_id": receiving_report.rm_code_id,
            "status_id": receiving_report.status_id
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
                rm_code_id=receiving_report.rm_code_id,
                warehouse_id=receiving_report.warehouse_id,
                rm_soh=0.00,
                status_id=receiving_report.status_id,
                date_computed=date_computed,
 		stock_recalculation_count=stock_recalculation_count  # Insert retrieved stock_recalculation_count
            )
            self.db.add(new_stock)
            self.db.commit()
            self.db.refresh(new_stock)


        receiving_report_item = TempReceivingReport(rm_code_id=receiving_report.rm_code_id,
                                                   warehouse_id=receiving_report.warehouse_id,
                                                   ref_number=receiving_report.ref_number,
                                                   receiving_date=receiving_report.receiving_date,
                                                   qty_kg=receiving_report.qty_kg,
                                                    status_id=receiving_report.status_id
                                                   )


        self.db.add(receiving_report_item)
        self.db.commit()
        self.db.refresh(receiving_report_item)
        return receiving_report_item

    def get_receiving_report(self):
        """
        Join StockOnHand, ReceivingReport, Warehouse, and RawMaterial tables.
        """
        # Join tables
        stmt = (
            self.db.query(
                TempReceivingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                TempReceivingReport.qty_kg,
                TempReceivingReport.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempReceivingReport.receiving_date,
                TempReceivingReport.created_at,
                TempReceivingReport.updated_at

            )
            .join(RawMaterial, TempReceivingReport.rm_code_id == RawMaterial.id)       # Join Receiving Report with RawMaterial
            .join(Warehouse, TempReceivingReport.warehouse_id == Warehouse.id) # Join Receiving Report with Warehouse
            .join(Status, TempReceivingReport.status_id == Status.id)
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                or_(
                    TempReceivingReport.is_cleared.is_(None),  # NULL check for is_cleared
                    TempReceivingReport.is_cleared == False  # False check for is_cleared
                ),
                or_(
                    TempReceivingReport.is_deleted.is_(None),  # NULL check for is_deleted
                    TempReceivingReport.is_deleted == False  # False check for is_deleted
                )
            )

            .order_by(desc(TempReceivingReport.created_at))  # Order from newest to oldest
        )

        # Return All the result
        return stmt.all()




    def get_deleted_receiving_report(self):
        """
        Join StockOnHand, ReceivingReport, Warehouse, and RawMaterial tables.
        """
        # Join tables
        stmt = (
            self.db.query(
                TempReceivingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                TempReceivingReport.qty_kg,
                TempReceivingReport.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempReceivingReport.receiving_date,
                TempReceivingReport.created_at,
                TempReceivingReport.updated_at

            )
            .join(RawMaterial, TempReceivingReport.rm_code_id == RawMaterial.id)       # Join Receiving Report with RawMaterial
            .join(Warehouse, TempReceivingReport.warehouse_id == Warehouse.id) # Join Receiving Report with Warehouse
            .join(Status, TempReceivingReport.status_id == Status.id)
            .filter(
                    TempReceivingReport.is_deleted == True  # False check for is_deleted
            )
        )

        # Return All the result
        return stmt.all()



    def get_historical_receiving_report(self):
        """
        Join StockOnHand, ReceivingReport, Warehouse, and RawMaterial tables.
        """
        # Join tables
        stmt = (
            self.db.query(
                TempReceivingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                TempReceivingReport.qty_kg,
                TempReceivingReport.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempReceivingReport.receiving_date,
                TempReceivingReport.created_at,
                TempReceivingReport.updated_at,
                TempReceivingReport.date_computed

            )
            .join(RawMaterial, TempReceivingReport.rm_code_id == RawMaterial.id)       # Join Receiving Report with RawMaterial
            .join(Warehouse, TempReceivingReport.warehouse_id == Warehouse.id) # Join Receiving Report with Warehouse
            .join(Status, TempReceivingReport.status_id == Status.id)
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                #     TempReceivingReport.is_cleared == True,  # False check for is_cleared
                    TempReceivingReport.date_computed.is_not(None)
                ,
                or_(
                    TempReceivingReport.is_deleted.is_(None),  # NULL check for is_deleted
                    TempReceivingReport.is_deleted == False  # False check for is_deleted
                )
            )
        )

        # Return All the result
        return stmt.all()

    def update_receiving_report(self, receiving_report_id: UUID, receiving_report_update: TempReceivingReportUpdate):

        # Check if the status id is null
        query = text("""SELECT * FROM view_beginning_soh
                                WHERE warehouseid = :warehouse_id
                                      AND rawmaterialid = :rm_code_id
                                      AND statusid = :status_id""")

        record = self.db.execute(query, {
            "warehouse_id": receiving_report_update.warehouse_id,
            "rm_code_id": receiving_report_update.rm_code_id,
            "status_id": receiving_report_update.status_id
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
                rm_code_id=receiving_report_update.rm_code_id,
                warehouse_id=receiving_report_update.warehouse_id,
                rm_soh=0.00,
                status_id=receiving_report_update.status_id,
                date_computed=date_computed,
                stock_recalculation_count=stock_recalculation_count  # Insert retrieved stock_recalculation_count
            )
            self.db.add(new_stock)
            self.db.commit()
            self.db.refresh(new_stock)

        try:
            receiving_report = self.db.query(TempReceivingReport).filter(TempReceivingReport.id == receiving_report_id).first()
            if not receiving_report or receiving_report.is_deleted:
                raise TempReceivingReportNotFoundException(detail="Receiving Report not found or already deleted.")

            for key, value in receiving_report_update.dict(exclude_unset=True).items():
                setattr(receiving_report, key, value)
            self.db.commit()
            self.db.refresh(receiving_report)
            return self.get_receiving_report()

        except Exception as e:
            raise TempReceivingReportUpdateException(detail=f"Error: {str(e)}")


    def soft_delete_receiving_report(self, receiving_report_id: UUID):
        try:
            receiving_report = self.db.query(TempReceivingReport).filter(TempReceivingReport.id == receiving_report_id).first()
            if not receiving_report or receiving_report.is_deleted:
                raise TempReceivingReportNotFoundException(detail="Receiving Report not found or already deleted.")

            receiving_report.is_deleted = True
            self.db.commit()
            self.db.refresh(receiving_report)
            rr_list = self.get_receiving_report()
            return rr_list

        except Exception as e:
            raise TempReceivingReportSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_receiving_report(self, receiving_report_id: UUID):
        try:
            receiving_report = self.db.query(TempReceivingReport).filter(TempReceivingReport.id == receiving_report_id).first()
            if not receiving_report or not receiving_report.is_deleted:
                raise TempReceivingReportNotFoundException(detail="Receiving Report not found or already restored.")

            receiving_report.is_deleted = False
            self.db.commit()
            self.db.refresh(receiving_report)
            return receiving_report

        except Exception as e:
            raise TempReceivingReportRestoreException(detail=f"Error: {str(e)}")
