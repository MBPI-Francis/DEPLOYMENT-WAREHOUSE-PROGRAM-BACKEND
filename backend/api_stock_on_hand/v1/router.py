from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from backend.api_stock_on_hand.v1.schemas import (StockOnHandCreate,
                                                  StockOnHandUpdate,
                                                  StockOnHandResponse,
                                                  HistoricalStockOnHandResponse
                                                  )

from backend.api_stock_on_hand.v1.service import StockOnHandService
from backend.settings.database import get_db
from uuid import UUID
from fastapi.responses import JSONResponse
from typing import List

router = APIRouter(prefix="/api/rm_stock_on_hand/v1")

@router.post("/create/", response_model=StockOnHandResponse)
async def create_rm_soh(rm_soh: StockOnHandCreate, db: get_db = Depends()):
    result = StockOnHandService(db).create_rm_soh(rm_soh)
    return result

@router.get("/list/", response_model=list[StockOnHandResponse])
async def read_rm_soh(db: get_db = Depends()):
    result = StockOnHandService(db).all_rm_soh()
    return result


# What is this about? Still identiying what is it for
# @router.get("/get/", response_model=StockOnHandResponse)
# async def get_rm_soh(
#         warehouse_id: UUID,
#         rm_code_id: UUID,
#         db: get_db = Depends()):
#     result = StockOnHandService(db).get_rm_soh(warehouse_id, rm_code_id)
#     return result



# What is this about? Still identifying what is it for
@router.get("/list/historical/", response_model=List[HistoricalStockOnHandResponse])
async def get_rm_soh(
        date_computed: str = None,
        db: get_db = Depends()):
    result = StockOnHandService(db).get_historical_stock_on_hand(date_computed)
    return result



@router.put("/update/{rm_soh_id}/", response_model=StockOnHandResponse)
async def update_rm_soh(rm_soh_id: UUID, rm_soh_update: StockOnHandUpdate, db: get_db = Depends()):
    result = StockOnHandService(db).update_rm_soh(rm_soh_id, rm_soh_update)
    return result


@router.put("/restore/{rm_soh_id}/", response_model=StockOnHandResponse)
async def restore_rm_soh(rm_soh_id: UUID,  db: get_db = Depends()):
    result = StockOnHandService(db).restore_rm_soh(rm_soh_id)
    return result


@router.delete("/delete/{rm_soh_id}/", response_model=StockOnHandResponse)
async def delete_rm_soh(rm_soh_id: UUID, db: get_db = Depends()):
    result = StockOnHandService(db).soft_delete_rm_soh(rm_soh_id)
    return result


@router.post("/import_stock_data/", response_model=HistoricalStockOnHandResponse)
async def import_stock_data(file: UploadFile = File(...), db: get_db = Depends()):
    try:
        # Process the Excel file and insert data
        content = await file.read()
        StockOnHandService(db).import_rm_soh(content)
        return JSONResponse(content={"message": "Data imported successfully!"}, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)