"""
API Router for Raw Material Endpoints.

All endpoints use standard 'def' (synchronous) so that database I/O runs
in FastAPI's worker thread pool, preventing concurrent LAN clients from
blocking the main asyncio event loop.
"""

from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_raw_materials.v1.schemas import (
    RawMaterialCreate,
    RawMaterialUpdate,
    RawMaterialResponse,
    TransformedRawMaterialResponse,
    MessageResponse
)
from api_rm_inv.api_raw_materials.v1.service import RawMaterialService

router = APIRouter(prefix="/api/raw_materials/v1", tags=["Raw Materials"])


@router.post(
    "/create/",
    response_model=RawMaterialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new raw material"
)
def create_raw_material(
    payload: RawMaterialCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a unique raw material item into the warehouse catalog."""
    service = RawMaterialService(db)
    return service.register_material(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[RawMaterialResponse],
    summary="List all active raw materials"
)
def list_raw_materials(db: Session = Depends(get_db)):
    """Retrieves all active raw materials sorted alphabetically by item code."""
    service = RawMaterialService(db)
    return service.get_all_materials()


@router.get(
    "/transformed_list/",
    response_model=List[TransformedRawMaterialResponse],
    summary="List raw materials with creator details"
)
def list_transformed_raw_materials(db: Session = Depends(get_db)):
    """Retrieves raw materials joined with the user full name who created each record."""
    service = RawMaterialService(db)
    return service.get_transformed_list()


@router.get(
    "/get/{rm_code}/",
    response_model=RawMaterialResponse,
    summary="Find material by code"
)
def get_raw_material(rm_code: str, db: Session = Depends(get_db)):
    """Looks up a single raw material by its exact material code."""
    service = RawMaterialService(db)
    return service.get_material_by_code(rm_code)


@router.put(
    "/update/{rm_code}/",
    response_model=RawMaterialResponse,
    summary="Update raw material by code"
)
def update_raw_material(
    rm_code: str,
    payload: RawMaterialUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates editable information on an existing raw material directly using its code."""
    service = RawMaterialService(db)
    return service.update_material_by_code(rm_code, payload, request, current_user)


@router.delete(
    "/delete/{rm_code}/",
    response_model=MessageResponse,
    summary="Soft-delete a raw material by code"
)
def delete_raw_material(
    rm_code: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft-deletes a raw material so historical transaction records remain intact."""
    service = RawMaterialService(db)
    return service.soft_delete_material_by_code(rm_code, request, current_user)


@router.put(
    "/restore/{rm_code}/",
    response_model=MessageResponse,
    summary="Restore a soft-deleted raw material by code"
)
def restore_raw_material(
    rm_code: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reactivates a previously soft-deleted raw material back to active status."""
    service = RawMaterialService(db)
    return service.restore_material_by_code(rm_code, request, current_user)


@router.post(
    "/import_raw_materials/",
    summary="Bulk import raw materials from Excel (.xlsx)"
)
def import_raw_materials(
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parses an uploaded Excel sheet and imports unique raw materials in bulk.
    Skips any codes that already exist in the database without failing the entire file.
    """
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Please upload an Excel (.xlsx) file."
        )

    content = file.file.read()
    service = RawMaterialService(db)
    return service.process_excel_import(content, request, current_user)