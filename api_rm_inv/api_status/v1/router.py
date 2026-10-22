"""
API Router for Status Management Endpoints.

All endpoints use synchronous 'def' to allow threadpool concurrency
across LAN workstations and include limit/offset pagination.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_status.v1.schemas import (
    StatusCreate,
    StatusUpdate,
    StatusResponse,
    TransformedStatusResponse,
    StatusSearchResponse
)
from api_rm_inv.api_status.v1.service import StatusService

router = APIRouter(prefix="/status", tags=["Status Management"])


@router.post(
    "/create/",
    response_model=StatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new quality status"
)
def create_status(
    payload: StatusCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new quality classification tag."""
    service = StatusService(db)
    return service.create_status(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[StatusResponse],
    summary="List active quality statuses (Paginated)"
)
def read_status(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated active quality statuses."""
    service = StatusService(db)
    return service.get_status(limit=limit, offset=offset)


@router.get(
    "/transformed_list/",
    response_model=List[Dict[str, Any]],
    summary="List statuses with creator details (Paginated)"
)
def read_transformed_status(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves active quality statuses joined with creator full names."""
    service = StatusService(db)
    return service.all_transformed_status(limit=limit, offset=offset)


@router.get(
    "/search_status/",
    response_model=StatusSearchResponse,
    summary="Search status by name"
)
def search_status(
    name: str = Query(..., description="Status name to search"),
    db: Session = Depends(get_db)
):
    """Looks up a status record by exact or normalized name."""
    service = StatusService(db)
    return service.get_status_by_name(name)


@router.put(
    "/update/{status_name}/",
    response_model=StatusResponse,
    summary="Update quality status by name"
)
def update_status(
    status_name: str,
    payload: StatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = StatusService(db)
    return service.update_status_by_name(status_name, payload, request, current_user)


@router.delete(
    "/delete/{status_name}/",
    response_model=StatusResponse,
    summary="Soft-delete a quality status by name"
)
def delete_status(
    status_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = StatusService(db)
    return service.soft_delete_status_by_name(status_name, request, current_user)


@router.put(
    "/restore/{status_name}/",
    response_model=StatusResponse,
    summary="Restore a soft-deleted quality status by name"
)
def restore_status(
    status_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = StatusService(db)
    return service.restore_status_by_name(status_name, request, current_user)