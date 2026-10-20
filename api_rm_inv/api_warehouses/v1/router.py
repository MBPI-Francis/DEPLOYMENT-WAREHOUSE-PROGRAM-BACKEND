"""
API Router for Warehouse Management Endpoints.

All endpoints use synchronous 'def' to allow threadpool concurrency
across LAN workstations.
"""

from typing import List
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_warehouses.v1.schemas import (
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseResponse,
    TransformedWarehouseResponse,
    MessageResponse
)
from api_rm_inv.api_warehouses.v1.service import WarehouseService

router = APIRouter(prefix="/api/warehouses/v1", tags=["Warehouses"])


@router.post(
    "/create/",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new physical warehouse"
)
def create_warehouse(
    payload: WarehouseCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new warehouse or storage silo in the plant."""
    service = WarehouseService(db)
    return service.create_warehouse(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[WarehouseResponse],
    summary="List all active warehouses"
)
def read_warehouse(db: Session = Depends(get_db)):
    """Retrieves all active warehouses sorted by facility number."""
    service = WarehouseService(db)
    return service.get_warehouse()


@router.get(
    "/transformed_list/",
    response_model=List[TransformedWarehouseResponse],
    summary="List warehouses with creator details"
)
def read_transformed_warehouse_list(db: Session = Depends(get_db)):
    """Retrieves active warehouses joined with creator user full names."""
    service = WarehouseService(db)
    return service.all_transformed_warehouse_list()


@router.put(
    "/update/{wh_number}/",
    response_model=WarehouseResponse,
    summary="Update warehouse by number"
)
def update_warehouse(
    wh_number: int,  # <-- Typed as int to match smallint in PostgreSQL
    payload: WarehouseUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WarehouseService(db)
    return service.update_warehouse_by_number(wh_number, payload, request, current_user)


@router.delete(
    "/delete/{wh_number}/",
    response_model=MessageResponse,
    summary="Soft-delete a warehouse by number"
)
def delete_warehouse(
    wh_number: int,  # <-- Typed as int
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WarehouseService(db)
    return service.soft_delete_warehouse_by_number(wh_number, request, current_user)


@router.put(
    "/restore/{wh_number}/",
    response_model=MessageResponse,
    summary="Restore a soft-deleted warehouse by number"
)
def restore_warehouse(
    wh_number: int,  # <-- Typed as int
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = WarehouseService(db)
    return service.restore_warehouse_by_number(wh_number, request, current_user)