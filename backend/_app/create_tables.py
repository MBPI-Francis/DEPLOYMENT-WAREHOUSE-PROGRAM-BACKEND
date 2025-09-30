



class CreateDatabaseTables:

    @staticmethod
    def create_database_tables():
        # Import all the models that we wanted to turn into a database tables
        from backend.api_adjustment_form.v1_form_entries.models import AdjustmentFormParent, AdjustmentFormCorrect
        from backend.api_adjustment_form.v1_spillage.models import SpillageAdjustmentForm
        from backend.api_change_status_form.v1.models import TempHeldForm
        from backend.api_notes.v1.models import TempNotes
        from backend.api_outgoing_report.v1.models import TempOutgoingReport
        from backend.api_preparation_form.v1.models import TempPreparationForm
        from backend.api_product_kinds.v1.models import ProductKind
        from backend.api_raw_materials.v1.models import RawMaterial
        from backend.api_receiving_report.v1.models import TempReceivingReport
        from backend.api_status.v1.models import Status
        from backend.api_stock_on_hand.v1.models import StockOnHand

        # Commented out, it will be created in the future
        # from backend.api_supplies_outgoing_report.v1.models import SuppliesOutgoingReport
        from backend.api_transfer_form.v1.models import TempTransferForm
        from backend.api_users.v1.models import User
        from backend.api_warehouses.v1.models import Warehouse


        #
        # Import the engine and the Base
        from backend.settings.database import engine, Base

        # This is the code to create database tables based on the imported models
        print("INFO: Creating Database Tables...")
        Base.metadata.create_all(bind=engine)
        print("INFO: Database Tables is successfully created!")