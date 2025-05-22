from fastapi import FastAPI
from backend.api_users.v1 import router as user_router
from backend.api_warehouses.v1 import router as warehouse_router
from backend.api_raw_materials.v1 import router as raw_material_router
from backend.api_status.v1 import router as status_router
from backend.api_stock_on_hand.v1 import router as soh_router
from backend.api_product_kinds.v1 import router as product_kind_router
from backend.api_auth_users.v1 import router as auth_router
from backend.api_notes.v1 import router as notes_router_temp
from backend.api_receiving_report.v1 import router as temp_receiving_report_router
from backend.api_outgoing_report.v1 import router as temp_outgoing_report_router
from backend.api_transfer_form.v1 import router as temp_transfer_form_router
from backend.api_preparation_form.v1 import router as temp_preparation_form_router
from backend.api_change_status_form.v1 import router as temp_held_form_router
from backend.api_others import router as create_view_router
from backend.settings.database import engine, Base
from backend.settings.create_view_table import (create_ending_view_table,
                                                create_beginning_view_table,
                                                create_adjusted_ending_view_table)
from backend.settings.create_product_kind import create_product_kind
from backend.api_adjustment_form.v1_spillage import router as adjustment_form_router





# Initialize FastAPI app
app = FastAPI(title="Warehouse Program API")

@app.on_event("startup")
def startup_event():
    """Runs automatically when FastAPI starts."""
    create_beginning_view_table()  # Automatically create the view
    create_ending_view_table()
    create_product_kind()
    create_adjusted_ending_view_table()


# These code includes all the routers/endpoint of the api_users
app.include_router(user_router.router)

# These code includes all the routers/endpoint of the api_warehouses
app.include_router(warehouse_router.router)

# These code includes all the routers/endpoint of the api_raw_materials
app.include_router(raw_material_router.router)

# These code includes all the routers/endpoint of the api_status
app.include_router(status_router.router)

# These code includes all the routers/endpoint of the api_stock_on_hand
app.include_router(soh_router.router)

# These code includes all the routers/endpoint of the api_product_kind
app.include_router(product_kind_router.router)

# These code includes all the routers/endpoint of the api_notes_temp
app.include_router(notes_router_temp.router)

# These code includes all the routers/endpoint of the api_auth_users
app.include_router(auth_router.router)

# These code includes all the routers/endpoint of the api_receiving_report
app.include_router(temp_receiving_report_router.router)

# These code includes all the routers/endpoint of the api_outgoing_report
app.include_router(temp_outgoing_report_router.router)

# These code includes all the routers/endpoint of the api_transfer_form
app.include_router(temp_transfer_form_router.router)

# These code includes all the routers/endpoint of the api_preparation_form
app.include_router(temp_preparation_form_router.router)

# These code includes all the routers/endpoint of the api_change_status_form
app.include_router(temp_held_form_router.router)

# These code includes all the routers/endpoint of the api_create_view_table
app.include_router(create_view_router.router)

# These code includes all the routers/endpoint of the api_adjustment_form
app.include_router(adjustment_form_router.router)

# Code for Creating database tables
Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "Welcome to the RM Inventory Management System (RM-IMS) Backend API"}
