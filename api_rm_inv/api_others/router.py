"""
API Router for Stock Validation, System Recalculation, and Accounting Closures.

Coordinates:
1. Live stock availability pre-flight checks against schema_whrm.view_adjusted_ending_balance.
2. High-speed bulk stock snapshot crystallization into tbl_stock_on_hand.
3. Accounting period date computation stamping and clearing across all active ledger tables.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from sqlalchemy import text, update
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user
from core.logger import AuditLogger
from shared.users.models import User

# Entity Models
from api_rm_inv.api_notes.v1.models import TempNotes
from api_rm_inv.api_preparation_form.v1.models import TempPreparationForm
from api_rm_inv.api_transfer_form.v1.models import TempTransferForm
from api_rm_inv.api_adjustment_form.v1_spillage.models import SpillageAdjustmentForm
from api_rm_inv.api_adjustment_form.v1_form_entries.models import AdjustmentFormCorrect
from api_rm_inv.api_outgoing_report.v1.models import TempOutgoingReport
from api_rm_inv.api_receiving_report.v1.models import TempReceivingReport
from api_rm_inv.api_stock_on_hand.v1.models import StockOnHand
from api_rm_inv.api_change_status_form.v1.models import TempHeldForm

router = APIRouter(prefix="/system", tags=["System Recalculation & Balance Validation"])


# ===========================================================================
# 1. Live SOH Balances (Paginated & Mapped)
# ===========================================================================

@router.get("/soh/adjusted-ending/", summary="Get live adjusted ending balance (Excludes 0.00)")
def get_adjusted_ending_balance(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Queries schema_whrm.view_adjusted_ending_balance for non-zero stock balances."""
    query = text("""
        SELECT * FROM schema_whrm.view_adjusted_ending_balance 
        WHERE new_beginning_balance != 0.00
        LIMIT :limit OFFSET :offset
    """)
    result = db.execute(query, {"limit": limit, "offset": offset})
    return [dict(row) for row in result.mappings().all()]


@router.get("/soh/adjusted-ending/all/", summary="Get live adjusted ending balance (Includes 0.00)")
def get_adjusted_ending_balance_all(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Queries schema_whrm.view_adjusted_ending_balance including zero balances."""
    query = text("""
        SELECT * FROM schema_whrm.view_adjusted_ending_balance 
        LIMIT :limit OFFSET :offset
    """)
    result = db.execute(query, {"limit": limit, "offset": offset})
    return [dict(row) for row in result.mappings().all()]


@router.get("/soh/beginning-balance/", summary="Get beginning SOH baseline balance")
def get_beginning_balance(
    limit: int = Query(100, ge=1, le=1000, description="Items to fetch"),
    offset: int = Query(0, ge=0, description="Items to skip"),
    db: Session = Depends(get_db)
):
    """Queries schema_whrm.view_beginning_soh."""
    query = text("""
        SELECT * FROM schema_whrm.view_beginning_soh 
        LIMIT :limit OFFSET :offset
    """)
    result = db.execute(query, {"limit": limit, "offset": offset})
    return [dict(row) for row in result.mappings().all()]


@router.get("/soh/check-existence/", summary="Check if material has baseline in view_adjusted_ending_balance")
def check_material_existence(
    rm_id: UUID,
    warehouse_id: UUID,
    status_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> bool:
    """Verifies parameterized record existence safely without raw string interpolation."""
    params: Dict[str, Any] = {"rm_id": rm_id, "warehouse_id": warehouse_id}

    if status_id:
        query_sql = """
            SELECT 1 FROM schema_whrm.view_adjusted_ending_balance
            WHERE rawmaterialid = :rm_id AND warehouseid = :warehouse_id AND statusid = :status_id
            LIMIT 1
        """
        params["status_id"] = status_id
    else:
        query_sql = """
            SELECT 1 FROM schema_whrm.view_adjusted_ending_balance
            WHERE rawmaterialid = :rm_id AND warehouseid = :warehouse_id
            LIMIT 1
        """

    record = db.execute(text(query_sql), params).fetchone()
    return record is not None


# ===========================================================================
# 2. Accounting Period Stamping & Crystalizing SOH
# ===========================================================================

@router.post("/accounting/update-date-computed/", summary="Stamp date_computed on all uncomputed active rows")
def update_date_computed(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes atomic date_computed stamping across all warehouse ledgers simultaneously.
    """
    tables = [
        TempNotes,
        TempPreparationForm,
        TempTransferForm,
        TempOutgoingReport,
        TempReceivingReport,
        TempHeldForm,
        SpillageAdjustmentForm,
        AdjustmentFormCorrect
    ]

    current_date = date.today()
    updated_tables = []

    try:
        for model in tables:
            stmt = (
                update(model)
                .where(
                    model.date_computed.is_(None),
                    model.is_cleared == False,
                    model.is_deleted == False
                )
                .values(date_computed=current_date)
            )
            db.execute(stmt)
            updated_tables.append(model.__tablename__)

        AuditLogger.log_action(
            db=db,
            request=request,
            current_user=current_user,
            module="SYSTEM",
            action="UPDATE",
            table_name="tbl_accounting_closure",
            record_id=current_user.id,
            payload={"action": "update_date_computed", "tables": updated_tables, "date": str(current_date)}
        )

        db.commit()
        return {"message": "date_computed stamped successfully.", "updated_tables": updated_tables}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update date_computed: {str(e)}")


@router.post(
    "/accounting/crystallize-stock-on-hand/",
    summary="Snapshot live ending balances into SOH baseline (Blocks if negative balances exist)",
    responses={
        422: {"description": "Negative stock balances detected in one or more warehouses"}
    }
)
def crystallize_stock_on_hand(
    params_date: str = Query(..., description="Snapshot date (YYYY-MM-DD)"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    High-performance snapshot engine:
    1. Scans view_adjusted_ending_balance for negative balances (< 0.00 kg).
       - If found: Rejects the request with HTTP 422 and returns the full deficit report.
    2. Takes valid ending balances and crystalizes them into tbl_stock_on_hand in < 50ms.
    3. Records an atomic audit log under module 'SYSTEM'.
    """
    try:
        parsed_date = datetime.strptime(params_date.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid date format. Expected YYYY-MM-DD."
        )

    # -----------------------------------------------------------------------
    # Step 1: Pre-flight Check for Negative Stock Balances (< 0.00 kg)
    # -----------------------------------------------------------------------
    # We join RawMaterial, Warehouse, and Status to give readable error details
    # so warehouse supervisors know exactly which item and location needs correction.
    check_negative_query = text("""
        SELECT 
            rm.rm_code,
            rm.rm_name,
            wh.wh_number,
            wh.wh_name,
            st.name AS status_name,
            v.new_beginning_balance
        FROM schema_whrm.view_adjusted_ending_balance v
        JOIN schema_whrm.tbl_raw_materials rm ON v.rawmaterialid = rm.id
        JOIN schema_whrm.tbl_warehouses wh ON v.warehouseid = wh.id
        LEFT JOIN schema_whrm.tbl_status st ON v.statusid = st.id
        WHERE v.new_beginning_balance < 0.00
        ORDER BY v.new_beginning_balance ASC
    """)

    negative_rows = db.execute(check_negative_query).fetchall()

    if negative_rows:
        deficits = [
            {
                "rm_code": row.rm_code,
                "rm_name": row.rm_name,
                "wh_number": str(row.wh_number),
                "wh_name": row.wh_name,
                "status": row.status_name or "unknown",
                "negative_balance": f"{float(row.new_beginning_balance):.2f} kg"
            }
            for row in negative_rows
        ]

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Crystallization Blocked: Negative stock balance detected.",
                "message": (
                    f"Found {len(deficits)} raw material(s) with negative stock balances. "
                    "Physical inventory cannot drop below zero. Please review the items below "
                    "and submit an adjustment form before closing the period."
                ),
                "negative_records": deficits
            }
        )

    # -----------------------------------------------------------------------
    # Step 2: Crystallize Valid Balances into tbl_stock_on_hand
    # -----------------------------------------------------------------------
    try:
        # Get next sequential recalculation count
        latest_count_query = text("SELECT MAX(stock_recalculation_count) FROM schema_whrm.tbl_stock_on_hand")
        max_count = db.execute(latest_count_query).scalar()
        next_count = (max_count + 1) if max_count is not None else 1

        # Query all live balances
        view_query = text("""
            SELECT rawmaterialid, warehouseid, new_beginning_balance, statusid 
            FROM schema_whrm.view_adjusted_ending_balance
        """)
        rows = db.execute(view_query).all()

        soh_objects = []
        for row in rows:
            soh_objects.append(
                StockOnHand(
                    rm_code_id=row[0],
                    warehouse_id=row[1],
                    rm_soh=Decimal(str(row[2])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    status_id=row[3],
                    stock_change_date=datetime.utcnow(),  # Matches PostgreSQL 'timestamp without time zone'
                    date_computed=parsed_date,
                    stock_recalculation_count=next_count,
                    created_by_id=current_user.id,
                    is_deleted=False,
                    is_imported=False
                )
            )

        if soh_objects:
            db.bulk_save_objects(soh_objects)

        # -------------------------------------------------------------------
        # Step 3: Record Audit Log
        # -------------------------------------------------------------------
        AuditLogger.log_action(
            db=db,
            request=request,
            current_user=current_user,
            module="SYSTEM",
            action="INSERT",
            table_name="tbl_stock_on_hand",
            record_id=current_user.id,
            payload={
                "action": "crystallize_stock_on_hand",
                "snapshot_date": str(parsed_date),
                "recalculation_count": next_count,
                "records_crystallized": len(soh_objects)
            }
        )

        db.commit()

        return {
            "message": "Stock on hand crystallized successfully. All balances verified non-negative.",
            "records_created": len(soh_objects),
            "recalculation_count": next_count,
            "snapshot_date": str(parsed_date)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crystallization transaction failed: {str(e)}"
        )

@router.post("/accounting/clear-table-data/", summary="Archive/clear active transactions by category")
def clear_table_data(
    category: str = Query(..., description="'notes', 'preparation', 'transfers', 'outgoing', 'receiving', 'change_status', 'spillage', 'all'"),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Marks transactions as is_cleared = True to archive active ledger views."""
    category_map = {
        "notes": [TempNotes],
        "preparation": [TempPreparationForm],
        "transfers": [TempTransferForm],
        "outgoing": [TempOutgoingReport],
        "receiving": [TempReceivingReport],
        "change_status": [TempHeldForm],
        "spillage": [SpillageAdjustmentForm],
        "all": [
            TempNotes,
            TempPreparationForm,
            TempTransferForm,
            TempOutgoingReport,
            TempReceivingReport,
            TempHeldForm,
            SpillageAdjustmentForm
        ]
    }

    selected_models = category_map.get(category.strip().lower())
    if not selected_models:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid category '{category}'. Available: {list(category_map.keys())}"
        )

    try:
        updated_tables = []
        for model in selected_models:
            stmt = (
                update(model)
                .where((model.is_cleared.is_(None)) | (model.is_cleared == False))
                .values(is_cleared=True)
            )
            db.execute(stmt)
            updated_tables.append(model.__tablename__)

        AuditLogger.log_action(
            db=db,
            request=request,
            current_user=current_user,
            module="SYSTEM",
            action="UPDATE",
            table_name="tbl_cleared_archive",
            record_id=current_user.id,
            payload={"category": category, "tables": updated_tables}
        )

        db.commit()
        return {"message": "Tables cleared successfully.", "updated_tables": updated_tables}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Clear operation failed: {str(e)}")


# ===========================================================================
# 3. Client Pre-flight Stock Overdraft Validations (Commercial Precision)
# ===========================================================================

def _query_live_stock(db: Session, rm_id: UUID, warehouse_id: UUID, status_id: Optional[UUID]) -> Decimal:
    """Safely executes parameterized balance lookup returning commercial Decimal."""
    params: Dict[str, Any] = {"rm_id": rm_id, "wh_id": warehouse_id}
    if status_id:
        query = text("""
            SELECT COALESCE(new_beginning_balance, 0.00) 
            FROM schema_whrm.view_adjusted_ending_balance
            WHERE rawmaterialid = :rm_id AND warehouseid = :wh_id AND statusid = :st_id
            LIMIT 1
        """)
        params["st_id"] = status_id
    else:
        query = text("""
            SELECT COALESCE(new_beginning_balance, 0.00) 
            FROM schema_whrm.view_adjusted_ending_balance
            WHERE rawmaterialid = :rm_id AND warehouseid = :wh_id
            LIMIT 1
        """)

    result = db.execute(query, params).fetchone()
    if result and result[0] is not None:
        return Decimal(str(result[0]))
    return Decimal("0.00")


@router.get("/validate/stock-availability/", summary="Pre-validate standard outbound quantity")
def validate_standard_stock(
    rm_id: UUID,
    warehouse_id: UUID,
    entered_qty: Decimal,
    status_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> bool:
    """Returns True if live stock can fulfill the requested deduction."""
    balance = _query_live_stock(db, rm_id, warehouse_id, status_id)
    return balance >= entered_qty


@router.get("/validate/stock-availability/for-update/", summary="Pre-validate outbound update with credit")
def validate_stock_for_update(
    rm_id: UUID,
    warehouse_id: UUID,
    prev_entered_qty: Decimal,
    new_entered_qty: Decimal,
    status_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> bool:
    """Gives credit for the previous entry's quantity to avoid false overdrafts."""
    balance = _query_live_stock(db, rm_id, warehouse_id, status_id)
    effective_balance = balance + prev_entered_qty
    return effective_balance >= new_entered_qty


@router.get("/validate/spillage/", summary="Pre-validate spillage algebraic value")
def validate_spillage_stock(
    rm_id: UUID,
    warehouse_id: UUID,
    entered_qty: Decimal,
    status_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> bool:
    """
    Validates physical spillage:
    Positive (+) = Addition, always valid.
    Negative (-) = Deduction, verified against live stock.
    """
    balance = _query_live_stock(db, rm_id, warehouse_id, status_id)
    return (balance + entered_qty) >= Decimal("0.00")


@router.get("/validate/spillage/for-update/", summary="Pre-validate spillage update with credit")
def validate_spillage_stock_for_update(
    rm_id: UUID,
    warehouse_id: UUID,
    prev_entered_qty: Decimal,
    new_entered_qty: Decimal,
    status_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> bool:
    """Pre-validates spillage update giving credit for previous sign and amount."""
    balance = _query_live_stock(db, rm_id, warehouse_id, status_id)
    base_balance = balance - prev_entered_qty
    return (base_balance + new_entered_qty) >= Decimal("0.00")


@router.get("/validate/preparation-worksheet/", summary="Pre-validate preparation floor actuals")
def validate_preparation_actuals(
    rm_id: UUID,
    warehouse_id: UUID,
    qty_prep: Decimal,
    qty_returned: Decimal,
    status_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> bool:
    """Validates net consumption = qty_prep - qty_returned against live stock."""
    balance = _query_live_stock(db, rm_id, warehouse_id, status_id)
    net_consumption = (qty_prep - qty_returned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return balance >= net_consumption


@router.get("/validate/preparation-worksheet/for-update/", summary="Pre-validate preparation update with credit")
def validate_preparation_actuals_for_update(
    rm_id: UUID,
    warehouse_id: UUID,
    prev_consumption: Decimal,
    new_consumption: Decimal,
    status_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
) -> bool:
    """Pre-validates net consumption update with credit for prior consumption."""
    balance = _query_live_stock(db, rm_id, warehouse_id, status_id)
    effective_balance = balance + prev_consumption
    return effective_balance >= new_consumption