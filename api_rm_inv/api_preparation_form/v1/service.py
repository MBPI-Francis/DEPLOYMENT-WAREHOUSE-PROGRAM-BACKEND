"""
Business Service Layer for Preparation Forms.

Coordinates:
1. Traveler Integration: Worksheet lookups and atomic batch posting across schemas.
2. Ledger Maintenance: Manual creation, listing, updating, soft-deleting, and restoring.
3. Transactional Audit Logging for both RM deductions and Traveler completions.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session

from core.base import BaseService
from api_rm_inv.api_preparation_form.v1.crud import PrepIntegrationCRUD
from api_rm_inv.api_preparation_form.v1.models import TempPreparationForm
from api_rm_inv.api_preparation_form.v1.schemas import (
    PrepLookupResponse,
    PrepDetailLookupItem,
    PrepFormSubmissionRequest,
    PrepSubmissionResponse,
    TempPreparationFormCreate,
    TempPreparationFormUpdate,
    TempPreparationFormResponse,
)
from core.logger import AuditLogger
from shared.users.models import User


class PrepIntegrationService(BaseService):
    """Business service coordinating preparation traveler reconciliation and inventory deductions."""

    def __init__(self, db: Session):
        super().__init__(db)
        self.crud = PrepIntegrationCRUD(db)

    def _resolve_codes_to_uuids(
        self,
        rm_code: str,
        wh_number: str,
        status_name: str
    ) -> tuple[UUID, UUID, UUID]:
        """Resolves natural keys into database UUIDs."""
        material = self.crud.resolve_raw_material(rm_code)
        if not material:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Raw Material with code '{rm_code}' does not exist in inventory catalog."
            )

        warehouse = self.crud.resolve_warehouse(wh_number)
        if not warehouse:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Warehouse with number/name '{wh_number}' does not exist."
            )

        status_record = self.crud.resolve_status(status_name)
        if not status_record:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Quality status '{status_name}' does not exist in lookup table."
            )

        return material.id, warehouse.id, status_record.id

    # -----------------------------------------------------------------------
    # 1. Traveler Integration Workflow
    # -----------------------------------------------------------------------

    def get_worksheet(
        self,
        prod_lot_no: Optional[str] = None,
        prep_form_no: Optional[str] = None,
        prod_id: Optional[str] = None
    ) -> PrepLookupResponse:
        """Retrieves line items from schema_whprep by Lot No, Prep Form No, or Product ID."""
        if not any([prod_lot_no, prep_form_no, prod_id]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide at least one search criterion: 'prod_lot_no', 'prep_form_no', or 'prod_id'."
            )

        run = self.crud.get_run_by_any_identifier(prod_lot_no=prod_lot_no, prep_form_no=prep_form_no, prod_id=prod_id)
        if not run:
            identifier_used = prod_lot_no or prep_form_no or prod_id
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No active traveler found matching '{identifier_used}'.")

        header = run.header
        if header and header.status and header.status.status_code.upper() == "COMPLETED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Preparation Form '{header.prep_form_no}' (Lot: {run.lotno_prod}) is already COMPLETED and posted.")

        if self.crud.check_lot_already_deducted(run.lotno_prod):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Inventory deductions for Lot '{run.lotno_prod}' have already been posted to schema_whrm.")

        default_wh = self.crud.resolve_warehouse("1")
        default_wh_id = default_wh.id if default_wh else None

        default_st = self.crud.resolve_status("good")
        default_st_id = default_st.id if default_st else None

        details = self.crud.get_details_by_run_id(run.id)
        items = []

        for row in details:
            mat = self.crud.resolve_raw_material(row.rm_code)
            items.append(
                PrepDetailLookupItem(
                    detail_id=row.id,
                    sequence_no=row.sequence_no,
                    rm_code=row.rm_code,
                    rm_code_id=mat.id if mat else None,
                    rm_name=mat.rm_name if mat else None,
                    qty_required=row.qty_required,
                    qty_prepared=row.qty_prepared,
                    add_qty=row.qty_additional or Decimal("0.00"),
                    qty_returned=row.qty_returned or Decimal("0.00"),
                    rm_lotno=row.rm_lotno,
                    default_warehouse_id=default_wh_id,
                    default_wh_number="1",
                    default_status_id=default_st_id,
                    default_status_name="good"
                )
            )

        prep_no_str = str(header.prep_form_no) if header and header.prep_form_no is not None else "N/A"
        prod_id_str = str(run.prod_id) if run and run.prod_id is not None else ""

        return PrepLookupResponse(
            prep_form_no=prep_no_str,
            version=header.version,
            prod_lot_no=run.lotno_prod,
            prod_id=prod_id_str,
            qty_prod=run.qty_prod,
            header_status=header.status.status_name if header and header.status else "PENDING",
            items=items
        )

    def confirm_and_deduct_inventory(
        self,
        payload: PrepFormSubmissionRequest,
        request: Request,
        current_user: User
    ) -> PrepSubmissionResponse:
        """Atomically updates traveler actuals in schema_whprep and writes deductions into schema_whrm."""
        run = self.crud.get_run_by_any_identifier(prod_lot_no=payload.prod_lot_no)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Production Lot '{payload.prod_lot_no}' was not found.")

        header = run.header
        if header and header.status and header.status.status_code.upper() == "COMPLETED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Traveler '{payload.prep_form_no}' is already completed.")

        if self.crud.check_lot_already_deducted(payload.prod_lot_no):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Deductions for lot '{payload.prod_lot_no}' already exist in inventory.")

        wh_cache, st_cache, rm_cache = {}, {}, {}

        try:
            # 1. Update physical actuals in schema_whprep
            detail_map = {d.id: d for d in self.crud.get_details_by_run_id(run.id)}
            for line in payload.items:
                detail_row = detail_map.get(line.detail_id)
                if not detail_row:
                    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Detail ID '{line.detail_id}' does not belong to lot '{payload.prod_lot_no}'.")

                detail_row.rm_lotno = line.rm_lot_no.strip()
                detail_row.qty_prepared = line.qty_prepared
                detail_row.qty_additional = line.add_qty
                detail_row.qty_returned = line.qty_returned
                detail_row.prepared_by_user_id = current_user.id

            # 2. Update traveler header to COMPLETED
            completed_status = self.crud.get_prep_status_by_code("COMPLETED")
            if completed_status and header:
                header.status_id = completed_status.id

            # 3. Insert inventory deductions into schema_whrm
            deduction_count = 0
            for line in payload.items:
                rm_id = line.rm_code_id
                if not rm_id:
                    if line.rm_code not in rm_cache:
                        mat = self.crud.resolve_raw_material(line.rm_code)
                        if not mat:
                            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Material '{line.rm_code}' not found.")
                        rm_cache[line.rm_code] = mat.id
                    rm_id = rm_cache[line.rm_code]

                wh_id = line.warehouse_id
                if not wh_id:
                    wh_key = line.wh_number or "1"
                    if wh_key not in wh_cache:
                        wh = self.crud.resolve_warehouse(wh_key)
                        if not wh:
                            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Warehouse '{wh_key}' not found.")
                        wh_cache[wh_key] = wh.id
                    wh_id = wh_cache[wh_key]

                st_id = line.status_id
                if not st_id:
                    st_key = line.status_name or "good"
                    if st_key not in st_cache:
                        st = self.crud.resolve_status(st_key)
                        if not st:
                            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status '{st_key}' not found.")
                        st_cache[st_key] = st.id
                    st_id = st_cache[st_key]

                total_issued = (Decimal(str(line.qty_prepared)) + Decimal(str(line.add_qty))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                deduction_entry = TempPreparationForm(
                    rm_code_id=rm_id,
                    warehouse_id=wh_id,
                    status_id=st_id,
                    ref_number=str(payload.prep_form_no),
                    prod_lot_no=payload.prod_lot_no,
                    qty_required=line.qty_required,
                    qty_prepared=total_issued,
                    add_qty=line.add_qty,
                    qty_return=line.qty_returned,
                    rm_lot_no=line.rm_lot_no.strip(),
                    preparation_date=payload.preparation_date,
                    created_by_id=current_user.id,
                    is_deleted=False,
                    is_cleared=False,
                    is_adjusted=False
                )
                self.crud.create_inventory_deduction(deduction_entry)
                deduction_count += 1

            # 4. Record Audit Log for the entire traveler batch deduction
            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="WH_PREPARATION",
                action="INSERT",
                table_name="tbl_preparation_forms",
                record_id=run.id,
                payload={
                    "prod_lot_no": payload.prod_lot_no,
                    "prep_form_no": payload.prep_form_no,
                    "deductions_count": deduction_count
                }
            )

            # 5. Atomic Multi-Schema Commit
            self.db.commit()

            return PrepSubmissionResponse(
                success=True,
                message=f"Successfully reconciled Lot '{payload.prod_lot_no}'. {deduction_count} deductions posted.",
                prep_form_no=str(payload.prep_form_no),
                prod_lot_no=payload.prod_lot_no,
                deductions_recorded=deduction_count
            )

        except HTTPException:
            self.db.rollback()
            raise
        except Exception as err:
            self.db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Atomic transaction failed: {str(err)}")

    # -----------------------------------------------------------------------
    # 2. Ledger Maintenance Services
    # -----------------------------------------------------------------------

    def create_preparation_entry(
        self,
        payload: TempPreparationFormCreate,
        request: Request,
        current_user: User
    ) -> TempPreparationFormResponse:
        """Creates a manual preparation deduction in schema_whrm.tbl_preparation_forms atomically."""
        rm_id, wh_id, st_id = self._resolve_codes_to_uuids(
            rm_code=payload.rm_code,
            wh_number=payload.wh_number,
            status_name=payload.status_name
        )

        issued_raw = Decimal(str(payload.qty_prepared)) + Decimal(str(payload.add_qty or 0))
        total_issued = issued_raw.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        try:
            record = TempPreparationForm(
                rm_code_id=rm_id,
                warehouse_id=wh_id,
                status_id=st_id,
                ref_number=payload.ref_number.strip(),
                prod_lot_no=payload.prod_lot_no.strip() if payload.prod_lot_no else None,
                preparation_date=payload.preparation_date,
                qty_required=payload.qty_required or Decimal("0.00"),
                qty_prepared=total_issued,
                add_qty=payload.add_qty or Decimal("0.00"),
                qty_return=payload.qty_return,
                rm_lot_no=payload.rm_lot_no.strip() if payload.rm_lot_no else None,
                created_by_id=current_user.id,
                is_deleted=False,
                is_cleared=False,
                is_adjusted=False
            )
            created = self.crud.create_inventory_deduction(record)

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="WH_PREPARATION",
                action="INSERT",
                table_name="tbl_preparation_forms",
                record_id=created.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(created)
            return created

        except Exception as e:
            self.db.rollback()
            raise e

    def update_preparation_entry(
        self,
        form_id: UUID,
        payload: TempPreparationFormUpdate,
        request: Request,
        current_user: User
    ) -> TempPreparationFormResponse:
        """Updates an existing preparation form entry and logs changes atomically."""
        record = self.crud.get_preparation_by_id(form_id)
        if not record or record.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Preparation Form record not found or already deleted."
            )

        if payload.rm_code:
            material = self.crud.resolve_raw_material(payload.rm_code)
            if not material:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Material '{payload.rm_code}' not found.")
            record.rm_code_id = material.id

        if payload.wh_number:
            wh = self.crud.resolve_warehouse(payload.wh_number)
            if not wh:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Warehouse '{payload.wh_number}' not found.")
            record.warehouse_id = wh.id

        if payload.status_name:
            st = self.crud.resolve_status(payload.status_name)
            if not st:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Status '{payload.status_name}' not found.")
            record.status_id = st.id

        try:
            if payload.ref_number is not None:
                record.ref_number = payload.ref_number.strip()
            if payload.prod_lot_no is not None:
                record.prod_lot_no = payload.prod_lot_no.strip()
            if payload.preparation_date is not None:
                record.preparation_date = payload.preparation_date
            if payload.qty_prepared is not None:
                record.qty_prepared = payload.qty_prepared
            if payload.qty_return is not None:
                record.qty_return = payload.qty_return
            if payload.qty_required is not None:
                record.qty_required = payload.qty_required
            if payload.add_qty is not None:
                record.add_qty = payload.add_qty
            if payload.rm_lot_no is not None:
                record.rm_lot_no = payload.rm_lot_no.strip()

            record.updated_by_id = current_user.id

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="WH_PREPARATION",
                action="UPDATE",
                table_name="tbl_preparation_forms",
                record_id=record.id,
                payload=payload
            )

            self.db.commit()
            self.db.refresh(record)
            return record

        except Exception as e:
            self.db.rollback()
            raise e

    def get_active_preparation_list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Returns paginated active deduction records."""
        return self.crud.list_active_preparation_records(limit=limit, offset=offset)

    def get_deleted_preparation_list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Returns paginated soft-deleted deduction records."""
        return self.crud.list_deleted_preparation_records(limit=limit, offset=offset)

    def get_historical_preparation_list(
        self,
        record_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Returns paginated historical computed deduction records."""
        return self.crud.list_historical_preparation_records(record_id=record_id, limit=limit, offset=offset)

    def soft_delete_preparation_entry(
        self,
        form_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Soft-deletes an entry and records the audit trail atomically."""
        record = self.crud.get_preparation_by_id(form_id)
        if not record or record.is_deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preparation Form record not found or already deleted.")

        try:
            record.is_deleted = True
            record.deleted_by_id = current_user.id

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="WH_PREPARATION",
                action="SOFT_DELETE",
                table_name="tbl_preparation_forms",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "soft_delete"}
            )

            self.db.commit()
            return {"message": "Preparation form entry soft-deleted successfully.", "id": str(form_id)}

        except Exception as e:
            self.db.rollback()
            raise e

    def restore_preparation_entry(
        self,
        form_id: UUID,
        request: Request,
        current_user: User
    ) -> Dict[str, Any]:
        """Restores a soft-deleted entry and records the audit trail atomically."""
        record = self.crud.get_preparation_by_id(form_id)
        if not record or not record.is_deleted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preparation Form record not found or already restored.")

        try:
            record.is_deleted = False

            AuditLogger.log_action(
                db=self.db,
                request=request,
                current_user=current_user,
                module="WH_PREPARATION",
                action="RESTORE",
                table_name="tbl_preparation_forms",
                record_id=record.id,
                payload={"ref_number": record.ref_number, "action": "restore"}
            )

            self.db.commit()
            return {"message": "Preparation form entry restored successfully.", "id": str(form_id)}

        except Exception as e:
            self.db.rollback()
            raise e