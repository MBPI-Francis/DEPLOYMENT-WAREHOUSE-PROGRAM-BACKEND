from backend.api_product_kinds.v1.exceptions import ProductKindCreateException, ProductKindNotFoundException, \
    ProductKindUpdateException, ProductKindSoftDeleteException, ProductKindRestoreException
from backend.api_product_kinds.v1.main import AppCRUD, AppService
from backend.api_product_kinds.v1.models import ProductKind
from backend.api_product_kinds.v1.schemas import ProductKindCreate, ProductKindUpdate
from uuid import UUID


# These are the code for the app to communicate to the database
class ProductKindCRUD(AppCRUD):
    def create_product_kind(self, product_kind: ProductKindCreate):
        product_kind_item = ProductKind(id=product_kind.id,
                                        name=product_kind.name,
                                        description=product_kind.description,
                                        updated_by_id=product_kind.updated_by_id,
                                        created_by_id=product_kind.created_by_id)
        self.db.add(product_kind_item)
        self.db.commit()
        self.db.refresh(product_kind_item)
        return product_kind_item

    def get_product_kind(self):
        product_kind_item = self.db.query(ProductKind).all()
        if product_kind_item:
            return product_kind_item
        return []


    def update_product_kind(self, product_kind_id, product_kind_update: ProductKindUpdate):
        try:
            product_kind = self.db.query(ProductKind).filter(ProductKind.id == product_kind_id).first()
            if not product_kind or product_kind.is_deleted:
                raise ProductKindNotFoundException(detail="Product Kind not found or already deleted.")

            for key, value in product_kind_update.model_dump(exclude_unset=True).items():
                setattr(product_kind, key, value)
            self.db.commit()
            self.db.refresh(product_kind)
            return product_kind

        except Exception as e:
            raise ProductKindUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_product_kind(self, product_kind_id):
        try:
            product_kind = self.db.query(ProductKind).filter(ProductKind.id == product_kind_id).first()
            if not product_kind or product_kind.is_deleted:
                raise ProductKindNotFoundException(detail="Product Kind not found or already deleted.")

            product_kind.is_deleted = True
            self.db.commit()
            self.db.refresh(product_kind)
            return product_kind

        except Exception as e:
            raise ProductKindSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_product_kind(self, product_kind_id):
        try:
            product_kind = self.db.query(ProductKind).filter(ProductKind.id == product_kind_id).first()
            if not product_kind or not product_kind.is_deleted:
                raise ProductKindNotFoundException(detail="Product Kind not found or already restored.")

            product_kind.is_deleted = False
            self.db.commit()
            self.db.refresh(product_kind)
            return product_kind

        except Exception as e:
            raise ProductKindRestoreException(detail=f"Error: {str(e)}")


# These are the code for the business logic like calculation etc.
class ProductKindService(AppService):
    def create_product_kind(self, item: ProductKindCreate):
        try:
            product_kind_item = ProductKindCRUD(self.db).create_product_kind(item)

        except Exception as e:
            raise ProductKindCreateException(detail=f"Error: {str(e)}")

        return product_kind_item

    def get_product_kind(self):
        try:
            product_kind_item = ProductKindCRUD(self.db).get_product_kind()

        except Exception as e:
            raise ProductKindNotFoundException(detail=f"Error: {str(e)}")
        return product_kind_item

    # This is the service/business logic in updating the product_kind.
    def update_product_kind(self, product_kind_id, product_kind_update: ProductKindUpdate):
        product_kind = ProductKindCRUD(self.db).update_product_kind(product_kind_id, product_kind_update)
        return product_kind

    # This is the service/business logic in soft deleting the product_kind.
    def soft_delete_product_kind(self, product_kind_id):
        product_kind = ProductKindCRUD(self.db).soft_delete_product_kind(product_kind_id)
        return product_kind


    # This is the service/business logic in soft restoring the product_kind.
    def restore_product_kind(self, product_kind_id):
        product_kind = ProductKindCRUD(self.db).restore_product_kind(product_kind_id)
        return product_kind





