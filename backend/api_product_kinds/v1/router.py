from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api_product_kinds.v1.schemas import ProductKindCreate, ProductKindUpdate, ProductKindResponse
from backend.api_product_kinds.v1.service import ProductKindService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/product_kinds/v1_spillage")

@router.post("/create/", response_model=ProductKindResponse)
async def create_product_kind(product_kind: ProductKindCreate, db: get_db = Depends()):
    result = ProductKindService(db).create_product_kind(product_kind)
    return result

@router.get("/list/", response_model=list[ProductKindResponse])
async def read_product_kind(db: get_db = Depends()):
    result = ProductKindService(db).get_product_kind()
    return result

@router.put("/update/{product_kind_id}/", response_model=ProductKindResponse)
async def update_product_kind(product_kind_id, product_kind_update: ProductKindUpdate, db: get_db = Depends()):
    result = ProductKindService(db).update_product_kind(product_kind_id, product_kind_update)
    return result


@router.put("/restore/{product_kind_id}/", response_model=ProductKindResponse)
async def restore_product_kind(product_kind_id,  db: get_db = Depends()):
    result = ProductKindService(db).restore_product_kind(product_kind_id)
    return result


@router.delete("/delete/{product_kind_id}/", response_model=ProductKindResponse)
async def delete_product_kind(product_kind_id, db: get_db = Depends()):
    result = ProductKindService(db).soft_delete_product_kind(product_kind_id)
    return result