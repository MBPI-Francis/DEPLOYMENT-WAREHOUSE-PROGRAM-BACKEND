from backend.api_receiving_report.v1.exceptions import TempReceivingReportCreateException, TempReceivingReportNotFoundException, \
    TempReceivingReportUpdateException, TempReceivingReportSoftDeleteException, TempReceivingReportRestoreException
from backend.api_receiving_report.v1.main import AppCRUD, AppService
from backend.api_receiving_report.v1.models import TempReceivingReport
from backend.api_receiving_report.v1.schemas import TempReceivingReportCreate, TempReceivingReportUpdate
from backend.api_raw_materials.v1.models import RawMaterial
from backend.api_warehouses.v1.models import Warehouse
from uuid import UUID
from backend.api_stock_on_hand.v1.models import StockOnHand
from sqlalchemy import desc, or_
from sqlalchemy.sql import func, cast, case
from sqlalchemy.types import String
from sqlalchemy import text
from backend.api_receiving_report.v1.crud import TempReceivingReportCRUD


# These are the code for the business logic like calculation etc.
class TempReceivingReportService(AppService):
    def create_receiving_report(self, item: TempReceivingReportCreate):
        try:
            receiving_report_item = TempReceivingReportCRUD(self.db).create_receiving_report(item)

        except Exception as e:
            raise TempReceivingReportCreateException(detail=f"Error: {str(e)}")


        return receiving_report_item

    def get_receiving_report(self,
                             record_id=None):
        try:
            receiving_report_item = TempReceivingReportCRUD(self.db).get_receiving_report(record_id)

        except Exception as e:
            raise TempReceivingReportNotFoundException(detail=f"Error: {str(e)}")
        return receiving_report_item

    def get_deleted_receiving_report(self):
        try:
            receiving_report_item = TempReceivingReportCRUD(self.db).get_deleted_receiving_report()

        except Exception as e:
            raise TempReceivingReportNotFoundException(detail=f"Error: {str(e)}")
        return receiving_report_item


    def get_historical_receiving_report(self, record_id):
        try:
            receiving_report_item = TempReceivingReportCRUD(self.db).get_historical_receiving_report(record_id)

        except Exception as e:
            raise TempReceivingReportNotFoundException(detail=f"Error: {str(e)}")
        return receiving_report_item


    # This is the service/business logic in updating the receiving_report.
    def update_receiving_report(self, receiving_report_id: UUID, receiving_report_update: TempReceivingReportUpdate):
        receiving_report = TempReceivingReportCRUD(self.db).update_receiving_report(receiving_report_id, receiving_report_update)
        return receiving_report

    # This is the service/business logic in soft deleting the receiving_report.
    def soft_delete_receiving_report(self, receiving_report_id: UUID):
        receiving_report = TempReceivingReportCRUD(self.db).soft_delete_receiving_report(receiving_report_id)
        return receiving_report


    # This is the service/business logic in soft restoring the receiving_report.
    def restore_receiving_report(self, receiving_report_id: UUID):
        receiving_report = TempReceivingReportCRUD(self.db).restore_receiving_report(receiving_report_id)
        return receiving_report





