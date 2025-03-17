from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.api_users.v1.schemas import UserCreate, UserUpdate, UserResponse
from backend.api_users.v1.service import UserService
from backend.settings.database import get_db
from uuid import UUID

router = APIRouter(prefix="/api/users/v1")

@router.post("/create/", response_model=UserResponse)
async def create_user(department: UserCreate, db: get_db = Depends()):
    result = UserService(db).create_user(department)
    return result

@router.get("/list/", response_model=list[UserResponse])
async def read_user(db: get_db = Depends()):
    result = UserService(db).get_user()
    return result

@router.put("/update/{user_id}/", response_model=UserResponse)
async def update_user(user_id: UUID, user_update: UserUpdate, db: get_db = Depends()):
    result = UserService(db).update_user(user_id, user_update)
    return result


@router.put("/restore/{user_id}/", response_model=UserResponse)
async def restore_user(user_id: UUID,  db: get_db = Depends()):
    result = UserService(db).restore_user(user_id)
    return result


@router.delete("/delete/{user_id}/", response_model=UserResponse)
async def deactivate_user(user_id: UUID, db: get_db = Depends()):
    result = UserService(db).deactivate_user(user_id)
    return result