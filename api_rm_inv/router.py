"""
Master Router for the Raw Materials Inventory (RM) System.

Collects and mounts all RM-specific feature routers under one unified module.
"""

from fastapi import APIRouter

# Import all your existing feature routers
from api_rm_inv.api_users.v1 import router as user_router
from api_rm_inv.api_warehouses.v1 import router as warehouse_router
from api_rm_inv.api_raw_materials.v1 import router as raw_material_router
from api_rm_inv.api_status.v1 import router as status_router
from api_rm_inv.api_stock_on_hand.v1.router import router as soh_router
from api_rm_inv.api_product_kinds.v1 import router as product_kind_router
from api_rm_inv.api_auth_users.v1 import router as auth_router
from api_rm_inv.api_notes.v1 import router as notes_router_temp

from api_rm_inv.api_receiving_report.v1.router import router as receiving_report_router
from api_rm_inv.api_outgoing_report.v1.router import router as v2_outgoing_report_router
from api_rm_inv.api_transfer_form.v1.router import router as transfer_form_router
from api_rm_inv.api_reports.v1.router import router as reports_router


from api_rm_inv.api_change_status_form.v1 import router as held_form_router
from api_rm_inv.api_others import router as create_view_router
from api_rm_inv.api_adjustment_form.v1_spillage.router import router as spillage_adjustment_router
from api_rm_inv.api_adjustment_form.v1_form_entries.router import router as form_entries_adjustment_router
from api_rm_inv.api_supplies_outgoing_report.v1 import router as supplies_outgoing_router
from api_rm_inv.api_preparation_form.v1.router import router as prep_forms_router

# All endpoints in this router can optionally be prefixed with /rm or kept as-is
rm_router = APIRouter()

# Mount all RM routers
rm_router.include_router(user_router.router)
rm_router.include_router(warehouse_router.router)
rm_router.include_router(raw_material_router.router)
rm_router.include_router(status_router.router)
rm_router.include_router(product_kind_router.router)
rm_router.include_router(notes_router_temp.router)

rm_router.include_router(auth_router.router)

# 1. New standardized prefix
rm_router.include_router(receiving_report_router)
rm_router.include_router(transfer_form_router)
rm_router.include_router(v2_outgoing_report_router)
rm_router.include_router(prep_forms_router)
rm_router.include_router(spillage_adjustment_router)
rm_router.include_router(form_entries_adjustment_router)
rm_router.include_router(soh_router)
rm_router.include_router(reports_router)


rm_router.include_router(held_form_router.router)
rm_router.include_router(create_view_router.router)
rm_router.include_router(supplies_outgoing_router.router)
