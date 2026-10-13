# backend/_app/create_tables.py



class CreateDatabaseTables:

    @staticmethod
    def create_database_tables():
        # Import all the models that we wanted to turn into a database tables
        from api_rm_inv.api_adjustment_form.v1_form_entries.models import AdjustmentFormParent, AdjustmentFormCorrect
        from api_rm_inv.api_adjustment_form.v1_spillage.models import SpillageAdjustmentForm
        from api_rm_inv.api_change_status_form.v1.models import TempHeldForm
        from api_rm_inv.api_notes.v1.models import TempNotes
        from api_rm_inv.api_outgoing_report.v1.models import TempOutgoingReport
        from api_rm_inv.api_preparation_form.v1.models import TempPreparationForm
        from api_rm_inv.api_product_kinds.v1.models import ProductKind
        from api_rm_inv.api_raw_materials.v1.models import RawMaterial
        from api_rm_inv.api_receiving_report.v1.models import TempReceivingReport
        from api_rm_inv.api_status.v1.models import Status
        from api_rm_inv.api_stock_on_hand.v1.models import StockOnHand

        # Commented out, it will be created in the future
        # from backend.api_supplies_outgoing_report.v1.models import SuppliesOutgoingReport
        from api_rm_inv.api_transfer_form.v1.models import TempTransferForm
        from api_rm_inv.api_users.v1.models import User
        from api_rm_inv.api_warehouses.v1.models import Warehouse


        #
        # Import the engine and the Base
        from api_rm_inv.settings.database import engine, Base

        # This is the code to create database tables based on the imported models
        print("INFO: Creating Database Tables...")
        Base.metadata.create_all(bind=engine)
        print("INFO: Database Tables is successfully created!")