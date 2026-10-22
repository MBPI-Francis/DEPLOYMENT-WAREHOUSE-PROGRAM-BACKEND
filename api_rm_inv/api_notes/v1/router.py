"""
API Router for Warehouse Notes Endpoints.

All endpoints use synchronous 'def' to allow threadpool concurrency
across LAN workstations and include limit/offset pagination.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from shared.users.models import User
from api_rm_inv.api_notes.v1.schemas import NotesCreate, NotesUpdate, NotesResponse
from api_rm_inv.api_notes.v1.service import NotesService

router = APIRouter(prefix="/notes", tags=["Notes / Notepad"])


@router.post(
    "/create/",
    response_model=NotesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new note"
)
def create_notes(
    payload: NotesCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new memo or lot note and records the audit log atomically."""
    service = NotesService(db)
    return service.create_notes(payload, request, current_user)


@router.get(
    "/list/",
    response_model=List[Dict[str, Any]],
    summary="List active notes (Paginated)"
)
def read_notes(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated active notes."""
    service = NotesService(db)
    return service.get_notes(limit=limit, offset=offset)


@router.get(
    "/list/deleted/",
    response_model=List[Dict[str, Any]],
    summary="List soft-deleted notes (Paginated)"
)
def get_deleted_list(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated soft-deleted notes for recovery."""
    service = NotesService(db)
    return service.get_deleted_notes(limit=limit, offset=offset)


@router.get(
    "/list/historical/",
    response_model=List[Dict[str, Any]],
    summary="List historical computed notes (Paginated)"
)
def get_historical_list(
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    db: Session = Depends(get_db)
):
    """Retrieves computed historical notes with pagination."""
    service = NotesService(db)
    return service.get_historical_notes(limit=limit, offset=offset)


@router.put(
    "/update/{notes_id}/",
    response_model=NotesResponse,
    summary="Update a note"
)
def update_notes(
    notes_id: UUID,
    payload: NotesUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates a note record and records an audit log atomically."""
    service = NotesService(db)
    return service.update_notes(notes_id, payload, request, current_user)


@router.delete(
    "/delete/{notes_id}/",
    summary="Soft-delete a note"
)
def delete_notes(
    notes_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft-deletes a note record atomically."""
    service = NotesService(db)
    return service.soft_delete_notes(notes_id, request, current_user)


@router.put(
    "/restore/{notes_id}/",
    summary="Restore a soft-deleted note"
)
def restore_notes(
    notes_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restores a soft-deleted note record atomically."""
    service = NotesService(db)
    return service.restore_notes(notes_id, request, current_user)