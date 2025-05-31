from backend.api_outgoing_report.v1.exceptions import (TempOutgoingReportNotFoundException,
                                                       TempOutgoingReportUpdateException,
                                                       TempOutgoingReportSoftDeleteException,
                                                       TempOutgoingReportRestoreException
                                                       )
from backend.api_status.v1.models import Status
from backend.api_outgoing_report.v1.main import AppCRUD
from backend.api_outgoing_report.v1.models import TempOutgoingReport
from backend.api_outgoing_report.v1.schemas import OutgoingFormCreate, OutgoingFormUpdate
from uuid import UUID
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_warehouses.v1.models import Warehouse
from sqlalchemy import or_, desc


# These are the code for the app to communicate to the database
class TempOutgoingReportCRUD(AppCRUD):


    def create_outgoing_report(self, outgoing_report: OutgoingFormCreate):

        outgoing_report_item = TempOutgoingReport(rm_code_id=outgoing_report.rm_code_id,
                                            warehouse_id=outgoing_report.warehouse_id,
                                            ref_number=outgoing_report.ref_number,
                                            outgoing_date=outgoing_report.outgoing_date,
                                            qty_kg=outgoing_report.qty_kg,
                                            status_id = outgoing_report.status_id
                                            )


        self.db.add(outgoing_report_item)
        self.db.commit()
        self.db.refresh(outgoing_report_item)
        # return self.get_outgoing_report()
        return outgoing_report_item

    def get_outgoing_report(self):
        """
             Join StockOnHand, OutgoingReport, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                TempOutgoingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                TempOutgoingReport.qty_kg,
                TempOutgoingReport.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempOutgoingReport.outgoing_date,
                TempOutgoingReport.created_at,
                TempOutgoingReport.updated_at,
                TempOutgoingReport.date_computed

            )

            .join(RawMaterial, TempOutgoingReport.rm_code_id == RawMaterial.id)  # Join TempOutgoingReport with RawMaterial
            .join(Warehouse, TempOutgoingReport.warehouse_id == Warehouse.id)  # Join TempOutgoingReport with Warehouse
            .join(Status, TempOutgoingReport.status_id == Status.id)
            .filter(
                # Filter for records where is_cleared or is_deleted is NULL or False
                or_(
                    TempOutgoingReport.is_cleared.is_(None),  # NULL check for is_cleared
                    TempOutgoingReport.is_cleared == False  # False check for is_cleared
                ),
                or_(
                    TempOutgoingReport.is_deleted.is_(None),  # NULL check for is_deleted
                    TempOutgoingReport.is_deleted == False  # False check for is_deleted
                )
            )

            .order_by(desc(TempOutgoingReport.created_at))  # Order from newest to oldest
        )

        # Return All the result
        return stmt.all()

    def get_deleted_outgoing_report(self):
        """
             Join StockOnHand, OutgoingReport, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                TempOutgoingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                TempOutgoingReport.qty_kg,
                TempOutgoingReport.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempOutgoingReport.outgoing_date,
                TempOutgoingReport.created_at,
                TempOutgoingReport.updated_at,
                TempOutgoingReport.date_computed

            )

            .join(RawMaterial, TempOutgoingReport.rm_code_id == RawMaterial.id)  # Join TempOutgoingReport with RawMaterial
            .join(Warehouse, TempOutgoingReport.warehouse_id == Warehouse.id)  # Join TempOutgoingReport with Warehouse
            .join(Status, TempOutgoingReport.status_id == Status.id)
            .filter(
                    TempOutgoingReport.is_cleared == True,  # False check for is_cleared
                    TempOutgoingReport.is_deleted == True  # False check for is_deleted
            )
        )

        # Return All the result
        return stmt.all()

    def get_historical_outgoing_report(self):
        """
             Join StockOnHand, OutgoingReport, Warehouse, and RawMaterial tables.
             """
        # Join tables
        stmt = (
            self.db.query(
                TempOutgoingReport.id,
                RawMaterial.rm_code.label("raw_material"),
                TempOutgoingReport.qty_kg,
                TempOutgoingReport.ref_number,
                Warehouse.wh_name,
                Status.name.label("status"),
                TempOutgoingReport.outgoing_date,
                TempOutgoingReport.created_at,
                TempOutgoingReport.updated_at,
                TempOutgoingReport.date_computed

            )

            .join(RawMaterial, TempOutgoingReport.rm_code_id == RawMaterial.id)  # Join TempOutgoingReport with RawMaterial
            .join(Warehouse, TempOutgoingReport.warehouse_id == Warehouse.id)  # Join TempOutgoingReport with Warehouse
            .join(Status, TempOutgoingReport.status_id == Status.id)
            .filter(
                    # TempOutgoingReport.is_cleared == True,  # False check for is_cleared
                        TempOutgoingReport.date_computed.is_not(None),
                    or_(
                        TempOutgoingReport.is_deleted.is_(None),  # NULL check for is_deleted
                        TempOutgoingReport.is_deleted == False  # False check for is_deleted
                    )
            )
        )

        # Return All the result
        return stmt.all()

    def update_outgoing_report(self, outgoing_report_id: UUID, outgoing_report_update: OutgoingFormUpdate):
        try:
            outgoing_report = self.db.query(TempOutgoingReport).filter(TempOutgoingReport.id == outgoing_report_id).first()
            if not outgoing_report or outgoing_report.is_deleted:
                raise TempOutgoingReportNotFoundException(detail="Outgoing Report not found or already deleted.")

            for key, value in outgoing_report_update.dict(exclude_unset=True).items():
                setattr(outgoing_report, key, value)
            self.db.commit()
            self.db.refresh(outgoing_report)
            return self.get_outgoing_report()

        except Exception as e:
            raise TempOutgoingReportUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_outgoing_report(self, outgoing_report_id: UUID):
        try:
            outgoing_report = self.db.query(TempOutgoingReport).filter(TempOutgoingReport.id == outgoing_report_id).first()
            if not outgoing_report or outgoing_report.is_deleted:
                raise TempOutgoingReportNotFoundException(detail="Outgoing Report not found or already deleted.")

            outgoing_report.is_deleted = True
            self.db.commit()
            self.db.refresh(outgoing_report)
            return self.get_outgoing_report()

        except Exception as e:
            raise TempOutgoingReportSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_outgoing_report(self, outgoing_report_id: UUID):
        try:
            outgoing_report = self.db.query(TempOutgoingReport).filter(TempOutgoingReport.id == outgoing_report_id).first()
            if not outgoing_report or not outgoing_report.is_deleted:
                raise TempOutgoingReportNotFoundException(detail="Outgoing Report not found or already restored.")

            outgoing_report.is_deleted = False
            self.db.commit()
            self.db.refresh(outgoing_report)
            return outgoing_report

        except Exception as e:
            raise TempOutgoingReportRestoreException(detail=f"Error: {str(e)}")