from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api_status.v1.schemas import StatusCreate, StatusUpdate, StatusResponse, StatusResponse, \
    StatusSearchResponse
from backend.api_status.v1.service import StatusService
from backend.settings.database import get_db
from uuid import UUID
from typing import List

router = APIRouter(prefix="/api/status/v1_spillage")

@router.post("/create/", response_model=StatusResponse)
async def create_status(status: StatusCreate, db: get_db = Depends()):
    result = StatusService(db).create_status(status)
    return result

@router.get("/list/", response_model=list[StatusResponse])
async def read_status(db: get_db = Depends()):
    result = StatusService(db).get_status()
    return result


@router.get("/transformed_list/", response_model=list[StatusResponse])
async def read_transformed_status(db: get_db = Depends()):
    result = StatusService(db).all_transformed_status()
    return result

@router.put("/update/{status_id}/", response_model=StatusResponse)
async def update_status(status_id: UUID, status_update: StatusUpdate, db: get_db = Depends()):
    result = StatusService(db).update_status(status_id, status_update)
    return result

@router.put("/restore/{status_id}/", response_model=StatusResponse)
async def restore_status(status_id: UUID,  db: get_db = Depends()):
    result = StatusService(db).restore_status(status_id)
    return result


@router.delete("/delete/{status_id}/", response_model=StatusResponse)
async def delete_status(status_id: UUID, db: get_db = Depends()):
    result = StatusService(db).soft_delete_status(status_id)
    return result


@router.get("/search_status/", response_model=StatusSearchResponse)
async def search_status(name: str = None, db: get_db = Depends()):
    result = StatusService(db).get_status_by_name(name)
    return result
