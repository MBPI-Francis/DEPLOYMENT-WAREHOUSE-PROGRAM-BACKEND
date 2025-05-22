from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from backend.api_raw_materials.v1.schemas import RawMaterialCreate, RawMaterialUpdate, RawMaterialResponse, TransformedRawMaterialResponse
from backend.api_raw_materials.v1.service import RawMaterialService
from backend.settings.database import get_db
from uuid import UUID
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/raw_materials/v1")

@router.post("/create/", response_model=RawMaterialResponse)
async def create_raw_material(raw_material: RawMaterialCreate, db: get_db = Depends()):
    result = RawMaterialService(db).create_raw_material(raw_material)
    return result

@router.get("/list/", response_model=list[RawMaterialResponse])
async def read_raw_material(db: get_db = Depends()):
    result = RawMaterialService(db).all_raw_material()
    return result

@router.get("/transformed_list/", response_model=list[TransformedRawMaterialResponse])
async def read_transformed_raw_material(db: get_db = Depends()):
    result = RawMaterialService(db).all_transformed_raw_material()
    return result


@router.get("/get/", response_model=RawMaterialResponse)
async def get_raw_material(
    rm_code: str,
    db: get_db = Depends()
):
    result = RawMaterialService(db).get_raw_material(rm_code)
    return result

@router.put("/update/{rm_id}/", response_model=RawMaterialResponse)
async def update_raw_material(rm_id: UUID, raw_material_update: RawMaterialUpdate, db: get_db = Depends()):
    result = RawMaterialService(db).update_raw_material(rm_id, raw_material_update)
    return result


@router.put("/restore/{rm_id}/", response_model=RawMaterialResponse)
async def restore_raw_material(rm_id: UUID,  db: get_db = Depends()):
    result = RawMaterialService(db).restore_raw_material(rm_id)
    return result


@router.delete("/delete/{rm_id}/", response_model=RawMaterialResponse)
async def delete_raw_material(rm_id: UUID, db: get_db = Depends()):
    result = RawMaterialService(db).soft_delete_raw_material(rm_id)
    return result


@router.post("/import_raw_materials/")
async def import_stock_data(file: UploadFile = File(...), db: get_db = Depends()):
    # Ensure only Excel files are accepted
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only Excel (.xlsx) files are allowed.")

    try:
        # Read file content
        content = await file.read()

        # Process Excel content
        result = RawMaterialService(db).import_raw_material(content)

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)