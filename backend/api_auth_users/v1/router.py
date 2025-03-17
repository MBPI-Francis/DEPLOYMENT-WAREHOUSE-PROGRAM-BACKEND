from fastapi import APIRouter, Depends
from backend.api_auth_users.v1.schemas import AuthUserResponse
from backend.api_auth_users.v1.service import AuthUserService
from backend.settings.database import get_db

router = APIRouter(prefix="/api/auth_users")


@router.get("/{user_name}/{password}/", response_model=AuthUserResponse)
async def auth_user(user_name, password, db: get_db = Depends()):
    result = AuthUserService(db).auth_user(user_name, password)
    return result



