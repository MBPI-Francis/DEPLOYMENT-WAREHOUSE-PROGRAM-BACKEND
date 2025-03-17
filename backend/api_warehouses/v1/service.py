from backend.api_warehouses.v1.exceptions import WarehouseCreateException, WarehouseNotFoundException, \
    WarehouseUpdateException, WarehouseSoftDeleteException, WarehouseRestoreException
from backend.api_warehouses.v1.main import AppCRUD, AppService
from backend.api_warehouses.v1.models import Warehouse
from backend.api_warehouses.v1.schemas import WarehouseCreate, WarehouseUpdate
from backend.api_users.v1.models import User
from sqlalchemy.sql import func
from uuid import UUID


# These are the code for the app to communicate to the database
class WarehouseCRUD(AppCRUD):
    def create_warehouse(self, warehouse: WarehouseCreate):
        warehouse_item = Warehouse(wh_number=warehouse.wh_number,
                                   description=warehouse.description,
                                   wh_name=warehouse.wh_name,
                                   updated_by_id=warehouse.updated_by_id,
                                   created_by_id=warehouse.created_by_id)
        self.db.add(warehouse_item)
        self.db.commit()
        self.db.refresh(warehouse_item)
        return warehouse_item

    def get_warehouse(self):
        warehouse_item = self.db.query(Warehouse).all()
        if warehouse_item:
            return warehouse_item
        return []
    
    
    def all_transformed_warehouse_list(self):
        # Join tables
        stmt = (
            self.db.query(
                Warehouse.id,
                Warehouse.wh_number,
                Warehouse.wh_name,
                Warehouse.created_at,
                Warehouse.updated_at,
                func.concat(User.first_name, " ", User.last_name).label("created_by")
            )
            .outerjoin(User,
                       User.id == Warehouse.created_by_id)  # Left join StockOnHand with ReceivingReport
        )

        # Return All the result
        return stmt.all()
        


    def update_warehouse(self, warehouse_id: UUID, warehouse_update: WarehouseUpdate):
        try:
            warehouse = self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
            if not warehouse or warehouse.is_deleted:
                raise WarehouseNotFoundException(detail="Warehouse not found or already deleted.")

            for key, value in warehouse_update.dict(exclude_unset=True).items():
                setattr(warehouse, key, value)
            self.db.commit()
            self.db.refresh(warehouse)
            return warehouse

        except Exception as e:
            raise WarehouseUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_warehouse(self, warehouse_id: UUID):
        try:
            warehouse = self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
            if not warehouse or warehouse.is_deleted:
                raise WarehouseNotFoundException(detail="Warehouse not found or already deleted.")

            warehouse.is_deleted = True
            self.db.commit()
            self.db.refresh(warehouse)
            return warehouse

        except Exception as e:
            raise WarehouseSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_warehouse(self, warehouse_id: UUID):
        try:
            warehouse = self.db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
            if not warehouse or not warehouse.is_deleted:
                raise WarehouseNotFoundException(detail="Warehouse not found or already restored.")

            warehouse.is_deleted = False
            self.db.commit()
            self.db.refresh(warehouse)
            return warehouse

        except Exception as e:
            raise WarehouseRestoreException(detail=f"Error: {str(e)}")


# These are the code for the business logic like calculation etc.
class WarehouseService(AppService):
    def create_warehouse(self, item: WarehouseCreate):
        try:
            warehouse_item = WarehouseCRUD(self.db).create_warehouse(item)

        except Exception as e:
            raise WarehouseCreateException(detail=f"Error: {str(e)}")


        return warehouse_item

    def get_warehouse(self):
        try:
            warehouse_item = WarehouseCRUD(self.db).get_warehouse()

        except Exception as e:
            raise WarehouseNotFoundException(detail=f"Error: {str(e)}")
        return warehouse_item


    def all_transformed_warehouse_list(self):
        try:
            warehouse_item = WarehouseCRUD(self.db).all_transformed_warehouse_list()

        except Exception as e:
            raise WarehouseNotFoundException(detail=f"Error: {str(e)}")
        return warehouse_item


    # This is the service/business logic in updating the warehouse.
    def update_warehouse(self, warehouse_id: UUID, warehouse_update: WarehouseUpdate):
        warehouse = WarehouseCRUD(self.db).update_warehouse(warehouse_id, warehouse_update)
        return warehouse

    # This is the service/business logic in soft deleting the warehouse.
    def soft_delete_warehouse(self, warehouse_id: UUID):
        warehouse = WarehouseCRUD(self.db).soft_delete_warehouse(warehouse_id)
        return warehouse


    # This is the service/business logic in soft restoring the warehouse.
    def restore_warehouse(self, warehouse_id: UUID):
        warehouse = WarehouseCRUD(self.db).restore_warehouse(warehouse_id)
        return warehouse





