from backend.api_outgoing_report.v1.exceptions import TempOutgoingReportCreateException, TempOutgoingReportNotFoundException
from backend.api_outgoing_report.v1.main import AppService
from backend.api_outgoing_report.v1.schemas import OutgoingFormCreate, OutgoingFormUpdate
from uuid import UUID
from backend.api_outgoing_report.v1.crud import TempOutgoingReportCRUD



# These are the code for the business logic like calculation etc.
class TempOutgoingReportService(AppService):
    def create_outgoing_report(self, item: OutgoingFormCreate):
        try:
            outgoing_report_item = TempOutgoingReportCRUD(self.db).create_outgoing_report(item)

        except Exception as e:
            raise TempOutgoingReportCreateException(detail=f"Error: {str(e)}")


        return outgoing_report_item

    def get_outgoing_report(self):
        try:
            outgoing_report_item = TempOutgoingReportCRUD(self.db).get_outgoing_report()

        except Exception as e:
            raise TempOutgoingReportNotFoundException(detail=f"Error: {str(e)}")
        return outgoing_report_item

    def get_deleted_outgoing_report(self):
        try:
            outgoing_report_item = TempOutgoingReportCRUD(self.db).get_deleted_outgoing_report()

        except Exception as e:
            raise TempOutgoingReportNotFoundException(detail=f"Error: {str(e)}")
        return outgoing_report_item

    def get_historical_outgoing_report(self, outgoing_report_id):
        try:
            outgoing_report_item = TempOutgoingReportCRUD(self.db).get_historical_outgoing_report(outgoing_report_id)

        except Exception as e:
            raise TempOutgoingReportNotFoundException(detail=f"Error: {str(e)}")
        return outgoing_report_item

    # This is the service/business logic in updating the outgoing_report.
    def update_outgoing_report(self, outgoing_report_id: UUID, outgoing_report_update: OutgoingFormUpdate):
        outgoing_report = TempOutgoingReportCRUD(self.db).update_outgoing_report(outgoing_report_id, outgoing_report_update)
        return outgoing_report

    # This is the service/business logic in soft deleting the outgoing_report.
    def soft_delete_outgoing_report(self, outgoing_report_id: UUID):
        outgoing_report = TempOutgoingReportCRUD(self.db).soft_delete_outgoing_report(outgoing_report_id)
        return outgoing_report


    # This is the service/business logic in soft restoring the outgoing_report.
    def restore_outgoing_report(self, outgoing_report_id: UUID):
        outgoing_report = TempOutgoingReportCRUD(self.db).restore_outgoing_report(outgoing_report_id)
        return outgoing_report





