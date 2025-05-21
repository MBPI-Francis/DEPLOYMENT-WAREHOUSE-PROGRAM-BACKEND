from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api_notes.v1.schemas import NotesCreate, NotesUpdate, NotesResponse
from backend.api_notes.v1.service import NotesService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/notes/v1_spillage")

@router.post("/create/", response_model=NotesResponse)
async def create_notes(notes: NotesCreate, db: get_db = Depends()):
    result = NotesService(db).create_notes(notes)
    return result

@router.get("/list/", response_model=list[NotesResponse])
async def read_notes(db: get_db = Depends()):
    result = NotesService(db).get_notes()
    return result


@router.get("/list/deleted/", response_model=list[NotesResponse])
async def get_deleted_list(db: get_db = Depends()):
    result = NotesService(db).get_deleted_notes()
    return result


@router.get("/list/historical/", response_model=list[NotesResponse])
async def get_historical_list(db: get_db = Depends()):
    result = NotesService(db).get_historical_notes()
    return result

@router.put("/update/{notes_id}/", response_model=NotesResponse)
async def update_notes(notes_id: UUID, notes_update: NotesUpdate, db: get_db = Depends()):
    result = NotesService(db).update_notes(notes_id, notes_update)
    return result

@router.put("/restore/{notes_id}/", response_model=NotesResponse)
async def restore_notes(notes_id: UUID,  db: get_db = Depends()):
    result = NotesService(db).restore_notes(notes_id)
    return result

@router.delete("/delete/{notes_id}/", response_model=NotesResponse)
async def delete_notes(notes_id: UUID, db: get_db = Depends()):
    result = NotesService(db).soft_delete_notes(notes_id)
    return result

