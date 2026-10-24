"""
Business Service Layer for Stock on Hand Module.

Features:
- Live SOH balance querying with pagination.
- High-performance batch Excel SOH importer with in-memory caching.
- SOH creation using human business keys (rm_code, wh_number, status_name).
- Atomic transaction and audit log recording.
"""

import io
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
import pandas as pd
import msoffcrypto
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from core.logger import AuditLogger
from shared.users.models import User
from api_rm_inv.api_stock_on_hand.v1.crud import StockOnHandCRUD
from api_rm_inv.api_stock_on_hand.v1.models import StockOnHand
from api_rm_inv.api_raw_materials.v1.models import RawMaterial
from shared.warehouses.models import Warehouse
from shared.statuses.models import Status
from api_rm_inv.api_stock_on_hand.v1.schemas import (
    StockOnHandCreate,
    StockOnHandUpdate,
    StockOnHandResponse
)


class StockOnHandService(BaseService):
    """Business service coordinating stock baseline snapshots and batch imports."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = StockOnHandCRUD(db)

    def create_rm_soh(
        self,
        payload: StockOnHandCreate,
        request: Request,
        current_user: User
    ) -> StockOnHandResponse:
        """Creates an initial stock on hand baseline entry using human codes atomically."""
        material = self.crud.resolve_raw_material(payload.rm_code)
        if not material:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Material '{payload.rm_code}' not found.")

        warehouse = self.crud.resolve_warehouse(payload.wh_number)
        if not warehouse:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Warehouse '{payload.wh_number}' not found.")

        status_rec = self.crud.resolve_status(payload.status_name)
        if not status_rec:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status '{payload.status_name}' not found.")

        recalc_count = payload.stock_recalculation_count or self.crud.get_latest_recalculation_count()

        try:
            record = StockOnHand(
                rm_code_id=material.id,
                warehouse_id=warehouse.id,
                status_id=status_rec.id,
                rm_soh=payload.rm_soh,
                stock_recalculation_count=recalc_count,
                stock_change_date=datetime.utcnow(),  # Pass naive datetime
                description=payload.description,
                created_by_id=current_user.id,
                is_deleted=False,
                is_imported=False
            )
            created = self.crud.create(record)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="INSERT",
                table_name="tbl_stock_on_hand",
                record_id=created.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def all_rm_soh(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieves paginated active SOH records."""
        return self.crud.list_all_paginated(limit=limit, offset=offset)

    def get_historical_stock_on_hand(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        mat_code: Optional[str] = None,
        location: Optional[str] = None,
        status_name: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieves computed historical SOH records with multi-field filtering and pagination."""
        return self.crud.get_historical_stock_on_hand(
            date_from=date_from,
            date_to=date_to,
            mat_code=mat_code,
            location=location,
            status=status_name,
            limit=limit,
            offset=offset
        )

    def update_rm_soh(
        self,
        soh_id: UUID,
        payload: StockOnHandUpdate,
        request: Request,
        current_user: User
    ) -> StockOnHand:
        """Modifies baseline SOH quantity or description atomically."""
        record = self.crud.get_by_id(soh_id)
        if not record or record.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock on Hand record not found or already deleted.")

        try:
            if payload.rm_soh is not None:
                record.rm_soh = payload.rm_soh
            if payload.description is not None:
                record.description = payload.description.strip()

            record.updated_by_id = current_user.id

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="UPDATE",
                table_name="tbl_stock_on_hand",
                record_id=record.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(record)
            return record

        except Exception as e:
            self.db.rollback()
            raise e

    def soft_delete_rm_soh(
        self,
        soh_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Soft-deletes an SOH entry and records the audit trail atomically."""
        record = self.crud.get_by_id(soh_id)
        if not record or record.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock on Hand record not found or already deleted.")

        try:
            record.is_deleted = True

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="SOFT_DELETE",
                table_name="tbl_stock_on_hand",
                record_id=record.id,
                payload={"soh_id": str(soh_id), "action": "soft_delete"}
            )

            self.db.commit()
            return {"message": "Stock on hand baseline soft-deleted successfully.", "id": str(soh_id)}

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_rm_soh(
        self,
        soh_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Restores a soft-deleted SOH entry atomically."""
        record = self.crud.get_by_id(soh_id)
        if not record or not record.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stock on Hand record is not in a deleted state.")

        try:
            record.is_deleted = False

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="RESTORE",
                table_name="tbl_stock_on_hand",
                record_id=record.id,
                payload={"soh_id": str(soh_id), "action": "restore"}
            )

            self.db.commit()
            return {"message": "Stock on hand baseline restored successfully.", "id": str(soh_id)}

        except Exception as e:
            self.db.rollback()
            raise e

    def import_rm_soh(
        self,
        content: bytes,
        request: Request,
        current_user: User,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        High-performance batch SOH importer:
        1. Pre-caches materials, warehouses, and statuses in memory.
        2. Batch-inserts all rows across all sheets in ONE atomic transaction with an audit log.
        """
        excel_data = io.BytesIO(content)
        office_file = msoffcrypto.OfficeFile(excel_data)
        decrypted_excel = io.BytesIO()

        if office_file.is_encrypted():
            try:
                pass_key = password or "maranatha101"
                office_file.load_key(password=pass_key)
                office_file.decrypt(decrypted_excel)
                df_sheets = pd.read_excel(decrypted_excel, sheet_name=None, engine='openpyxl', header=0)
            except Exception:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect password or unable to decrypt Excel file.")
        else:
            df_sheets = pd.read_excel(excel_data, sheet_name=None, engine='openpyxl', header=0)

        material_cache = {
            m.rm_code.strip().upper(): m.id
            for m in self.db.query(RawMaterial.rm_code, RawMaterial.id).all()
        }
        warehouse_cache = {
            str(w.wh_number).strip(): w.id
            for w in self.db.query(Warehouse.wh_number, Warehouse.id).all()
        }
        status_cache = {
            s.name.strip().lower(): s.id
            for s in self.db.query(Status.name, Status.id).all()
        }

        default_status_id = status_cache.get("good")
        latest_count = self.crud.get_latest_recalculation_count()

        sheet_to_wh_num = {
            "whse1": "1",
            "whse2": "2",
            "whse4": "4",
        }

        new_soh_records = []
        new_materials_to_create = {}

        try:
            for sheet_name, data in df_sheets.items():
                wh_num = sheet_to_wh_num.get(sheet_name.strip().lower())
                if not wh_num or data.empty:
                    continue

                wh_id = warehouse_cache.get(wh_num)
                if not wh_id:
                    continue

                try:
                    raw_header = str(data.columns[0]).strip()
                    snapshot_date = pd.to_datetime(raw_header, errors='coerce').date()
                    if pd.isna(snapshot_date):
                        snapshot_date = date.today()
                except Exception:
                    snapshot_date = date.today()

                data.columns = data.iloc[0]
                data = data[0:].reset_index(drop=True)

                if len(data.columns) >= 6:
                    data.columns = [f"COL_{i}" for i in range(len(data.columns))]
                else:
                    continue

                for _, row in data.iterrows():
                    raw_code = row.get("COL_0")
                    if pd.isna(raw_code) or not str(raw_code).strip():
                        continue

                    cleaned_rm_code = str(raw_code).strip().upper()

                    rm_id = material_cache.get(cleaned_rm_code)
                    if not rm_id:
                        if cleaned_rm_code not in new_materials_to_create:
                            new_mat = RawMaterial(
                                rm_code=cleaned_rm_code,
                                rm_name=cleaned_rm_code,
                                description="Auto-generated during SOH Excel Import",
                                created_by_id=current_user.id
                            )
                            self.db.add(new_mat)
                            self.db.flush()
                            material_cache[cleaned_rm_code] = new_mat.id
                            rm_id = new_mat.id
                        else:
                            rm_id = new_materials_to_create[cleaned_rm_code]

                    raw_qty = row.get("COL_4", 0)
                    try:
                        qty = Decimal(str(raw_qty)).quantize(Decimal("0.01"))
                    except Exception:
                        qty = Decimal("0.00")

                    raw_st = row.get("COL_5")
                    st_id = default_status_id
                    if not pd.isna(raw_st) and str(raw_st).strip():
                        st_id = status_cache.get(str(raw_st).strip().lower(), default_status_id)

                    new_soh_records.append(
                        StockOnHand(
                            rm_code_id=rm_id,
                            warehouse_id=wh_id,
                            status_id=st_id,
                            rm_soh=qty,
                            stock_recalculation_count=latest_count,
                            date_computed=snapshot_date,
                            created_by_id=current_user.id,
                            is_imported=True,
                            is_deleted=False
                        )
                    )

            total_inserted = self.crud.bulk_insert_soh(new_soh_records)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="RM_INVENTORY",
                action="INSERT",
                table_name="tbl_stock_on_hand",
                record_id=current_user.id,
                payload={"records_imported": total_inserted, "recalc_count": latest_count}
            )

            self.db.commit()

            return {
                "message": "Stock on Hand data imported successfully.",
                "records_imported": total_inserted,
                "recalculation_count": latest_count
            }

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            raise e