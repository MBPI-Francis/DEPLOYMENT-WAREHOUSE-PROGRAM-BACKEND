"""
Preparation Form Database Models.

Defines cross-schema entities for:
1. schema_whprep: Upstream recipe generation, run details, and physical actuals.
2. schema_whrm: Downstream inventory deduction ledgers and traceability audit records.
"""

import uuid
from datetime import datetime, timezone, date
from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, Date, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


# ===========================================================================
# 1. UPSTREAM SCHEMA: schema_whprep (Preparation System)
# ===========================================================================

class PrepStatus(Base):
    """Status lookup for prep travelers (e.g., PENDING, IN_PROGRESS, COMPLETED)."""
    __tablename__ = "tbl_prep_status"
    __table_args__ = {"schema": "schema_whprep"}

    id = Column(Integer, primary_key=True, index=True)
    status_code = Column(String(50), unique=True, nullable=False)
    status_name = Column(String(100), nullable=False)


class PrepFormHeader(Base):
    """Header record for a printed preparation traveler."""
    __tablename__ = "tbl_prepform_header"
    __table_args__ = {"schema": "schema_whprep"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    prep_form_no = Column(String(50), unique=True, nullable=False, index=True)
    status_id = Column(Integer, ForeignKey("schema_whprep.tbl_prep_status.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  # <-- Added is_active column
    version = Column(Integer, nullable=False)
    last_modified_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    status = relationship("PrepStatus")
    runs = relationship("PrepFormRun", back_populates="header")


class PrepFormRun(Base):
    """Production batch run linking the traveler to a finished good lot number."""
    __tablename__ = "tbl_prepform_runs"
    __table_args__ = {"schema": "schema_whprep"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    header_id = Column(UUID(as_uuid=True), ForeignKey("schema_whprep.tbl_prepform_header.id"), nullable=False)
    lotno_prod = Column(String(128), unique=True, nullable=False, index=True)
    prod_id = Column(String(50), nullable=False)
    qty_prod = Column(Numeric(10, 2), nullable=False, default=0.00)

    header = relationship("PrepFormHeader", back_populates="runs")
    details = relationship("PrepFormDetail", back_populates="run", order_by="PrepFormDetail.sequence_no")


class PrepFormDetail(Base):
    """
    Individual raw material recipe ingredient line items.
    Holds both planned targets and handwritten floor actuals.
    """
    __tablename__ = "tbl_prepform_detail"
    __table_args__ = {"schema": "schema_whprep"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("schema_whprep.tbl_prepform_runs.id"), nullable=False)
    sequence_no = Column(Integer, nullable=False)
    rm_code = Column(String(50), nullable=False)

    # Pre-printed recipe target
    qty_required = Column(Numeric(10, 2), nullable=False, default=0.00)

    # Handwritten floor actuals returned on paper
    qty_prepared = Column(Numeric(10, 2), nullable=True)
    qty_additional = Column(Numeric(10, 2), nullable=True, default=0.00)
    qty_returned = Column(Numeric(10, 2), nullable=True, default=0.00)
    rm_lotno = Column(String(50), nullable=True)

    prepared_by_user_id = Column(UUID(as_uuid=True), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)

    run = relationship("PrepFormRun", back_populates="details")


# ===========================================================================
# 2. DOWNSTREAM SCHEMA: schema_whrm (Inventory Ledger)
# ===========================================================================

class TempPreparationForm(Base):
    """
    Inventory deduction ledger for Raw Materials.
    Every row here deducts material balance in view_ending_stocks_balance.
    """
    __tablename__ = "tbl_preparation_forms"
    __table_args__ = {"schema": "schema_whrm"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    rm_code_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_raw_materials.id"), nullable=False)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_warehouses.id"), nullable=False)
    status_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_status.id"), nullable=False)

    ref_number = Column(String(50), nullable=False)
    prod_lot_no = Column(String(128), nullable=True, index=True)

    # Quantities tracking formula: Net Consumed = (qty_prepared) - qty_return
    qty_required = Column(Numeric(10, 2), nullable=False, default=0.00)
    qty_prepared = Column(Numeric(10, 2), nullable=False, default=0.00)  # Holds (qty_prepared + add_qty)
    add_qty = Column(Numeric(10, 2), nullable=False, default=0.00)
    qty_return = Column(Numeric(10, 2), nullable=False, default=0.00)

    rm_lot_no = Column(String(50), nullable=True)
    preparation_date = Column(Date, nullable=False, default=date.today)

    # Audit & Status Flags
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_cleared = Column(Boolean, default=False, nullable=False)
    is_adjusted = Column(Boolean, default=False, nullable=False)
    date_computed = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    created_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)
    deleted_by_id = Column(UUID(as_uuid=True), ForeignKey("schema_whrm.tbl_users.id"), nullable=True)

    # Relationships
    rm_code = relationship("RawMaterial", foreign_keys=[rm_code_id])
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    status = relationship("Status", foreign_keys=[status_id])