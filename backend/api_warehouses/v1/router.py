from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api_warehouses.v1.schemas import WarehouseCreate, WarehouseUpdate, WarehouseResponse, TransformedWarehouseResponse
from backend.api_warehouses.v1.service import WarehouseService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/warehouses/v1_spillage")

@router.post("/create/", response_model=WarehouseResponse)
async def create_warehouse(warehouse: WarehouseCreate, db: get_db = Depends()):
    result = WarehouseService(db).create_warehouse(warehouse)
    return result

@router.get("/list/", response_model=list[WarehouseResponse])
async def read_warehouse(db: get_db = Depends()):
    result = WarehouseService(db).get_warehouse()
    return result


@router.get("/transformed_list/", response_model=list[TransformedWarehouseResponse])
async def read_transformed_raw_material(db: get_db = Depends()):
    result = WarehouseService(db).all_transformed_warehouse_list()
    return result

@router.put("/update/{warehouse_id}/", response_model=WarehouseResponse)
async def update_warehouse(warehouse_id: UUID, warehouse_update: WarehouseUpdate, db: get_db = Depends()):
    result = WarehouseService(db).update_warehouse(warehouse_id, warehouse_update)
    return result

@router.put("/restore/{warehouse_id}/", response_model=WarehouseResponse)
async def restore_warehouse(warehouse_id: UUID,  db: get_db = Depends()):
    result = WarehouseService(db).restore_warehouse(warehouse_id)
    return result


@router.delete("/delete/{warehouse_id}/", response_model=WarehouseResponse)
async def delete_warehouse(warehouse_id: UUID, db: get_db = Depends()):
    result = WarehouseService(db).soft_delete_warehouse(warehouse_id)
    return result