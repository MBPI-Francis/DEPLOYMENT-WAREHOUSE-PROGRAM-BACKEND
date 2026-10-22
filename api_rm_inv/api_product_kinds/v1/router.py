"""
API Router for Product Kinds Endpoints.

All endpoints use synchronous 'def' to allow threadpool concurrency
across LAN workstations and include limit/offset pagination.
"""

from typing import List
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_product_kinds.v1.schemas import ProductKindCreate, ProductKindUpdate, ProductKindResponse
from api_rm_inv.api_product_kinds.v1.service import ProductKindService

router = APIRouter(prefix="/product-kinds", tags=["Product Kinds"])


@router.post(
    "/create/",
    response_model=ProductKindResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product classification kind"
)
def create_product_kind(
    payload: ProductKindCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registers a new master product classification kind."""
    service = ProductKindService(db)
    return service.create_product_kind(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[ProductKindResponse],
    summary="List active product classification kinds (Paginated)"
)
def read_product_kind(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated active product classification kinds."""
    service = ProductKindService(db)
    return service.get_product_kind(limit=limit, offset=offset)


@router.put(
    "/update/{product_kind_id}/",
    response_model=ProductKindResponse,
    summary="Update product kind by code"
)
def update_product_kind(
    product_kind_id: str,
    payload: ProductKindUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates master product classification metadata."""
    service = ProductKindService(db)
    return service.update_product_kind(product_kind_id, payload, request, current_user)


@router.put(
    "/restore/{product_kind_id}/",
    response_model=ProductKindResponse,
    summary="Restore a soft-deleted product kind"
)
def restore_product_kind(
    product_kind_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reactivates a previously soft-deleted product classification kind."""
    service = ProductKindService(db)
    return service.restore_product_kind(product_kind_id, request, current_user)


@router.delete(
    "/delete/{product_kind_id}/",
    response_model=ProductKindResponse,
    summary="Soft-delete a product kind"
)
def delete_product_kind(
    product_kind_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft-deletes a product classification kind preserving historical recipes."""
    service = ProductKindService(db)
    return service.soft_delete_product_kind(product_kind_id, request, current_user)