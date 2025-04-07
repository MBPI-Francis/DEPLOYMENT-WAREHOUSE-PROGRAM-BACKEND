from fastapi import HTTPException
from fastapi import APIRouter, Depends
from backend.settings.database import get_db
from sqlalchemy import text
from datetime import date
from sqlalchemy import update
from uuid import UUID
from backend.api_preparation_form.v1.models import TempPreparationForm
from backend.api_notes.v1.models import TempNotes
from backend.api_transfer_form.v1.models import TempTransferForm
from backend.api_outgoing_report.v1.models import TempOutgoingReport
from backend.api_receiving_report.v1.models import TempReceivingReport
from backend.api_stock_on_hand.v1.models import StockOnHand
from backend.api_change_status_form.v1.models import TempHeldForm
from typing import Optional
from datetime import datetime, timedelta



router = APIRouter(prefix="/api")


@router.get("/get/new_soh/")
async def get_new_soh(db: get_db = Depends()):
    try:
        query = text("SELECT * FROM view_ending_stocks_balance WHERE new_beginning_balance != 0.00")
        result = db.execute(query)
        rows = result.fetchall()
        # Convert rows to a list of dictionaries
        # Use explicit extraction of column values
        data = [
            {column: value for column, value in row._mapping.items()}
            for row in rows
        ]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get/new_soh/with_zero/")
async def get_new_soh(db: get_db = Depends()):
    try:
        query = text("SELECT * FROM view_ending_stocks_balance")
        result = db.execute(query)
        rows = result.fetchall()
        # Convert rows to a list of dictionaries
        # Use explicit extraction of column values
        data = [
            {column: value for column, value in row._mapping.items()}
            for row in rows
        ]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/get/beginning_balance/")
async def get_beginning_balance(db: get_db = Depends()):
    try:
        query = text("SELECT * FROM view_beginning_soh")
        result = db.execute(query)
        rows = result.fetchall()
        # Convert rows to a list of dictionaries
        # Use explicit extraction of column values
        data = [
            {column: value for column, value in row._mapping.items()}
            for row in rows
        ]
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# This api checks if the record is existing in the new beginning soh.
@router.get("/check/raw_material/")
async def get_record(
        rm_id: UUID,
        warehouse_id: UUID,
        status_id: Optional[UUID]=None,
        db: get_db = Depends()):
    try:

        # Check if the status id is null
        if status_id:
            query = text(f"""SELECT * FROM view_ending_stocks_balance
                                       WHERE warehouseid = '{warehouse_id}'
                                               AND statusid = '{status_id}'
                                               AND rawmaterialid = '{rm_id}'""")

        else:
            query = text(f"""SELECT * FROM view_ending_stocks_balance
                            WHERE warehouseid = '{warehouse_id}'
                                    AND rawmaterialid = '{rm_id}'""")
        result = db.execute(query)
        rows = result.fetchall()

        # Returns true if the rows have racords based on the paramaters
        if rows:
            return True

        else:
            return False
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Helping function for the api
def update_date_computed_for_table(table, db):
    """
    Updates the `date_computed` column to the current date for records where it is NULL in the given table.
    """
    try:
        # Generate the current date
        current_date = date.today()

        # Create an update query
        stmt = (
            update(table)
            .where(table.date_computed.is_(None),
                   table.is_cleared == False,
                   table.is_deleted == False)
            .values(date_computed=current_date)
        )

        # Execute the query
        db.execute(stmt)
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update table {table.__tablename__}: {e}")

@router.post("/update-date-computed")
async def update_date_computed(db: get_db = Depends()):
    """
    Updates the `date_computed` column to the current date for all specified tables.
    """
    tables = [
        TempNotes,
        TempPreparationForm,
        TempTransferForm,
        TempOutgoingReport,
        TempReceivingReport,
        TempHeldForm,
    ]

    updated_tables = []

    for table in tables:
        success = update_date_computed_for_table(table, db)
        if success:
            updated_tables.append(table.__tablename__)

    return {"message": "Update successful", "updated_tables": updated_tables}


@router.post("/update_stock_on_hand/")
async def update_stock_on_hand(params_date: str, db=Depends(get_db)):
    """
    Endpoint to update the stock-on-hand records from an external API.

    Args:
        db: Database session dependency injected by FastAPI.

    Returns:
        A JSON response indicating the success of the operation.
    """

    params_date = datetime.strptime(params_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    query = text("SELECT * FROM view_ending_stocks_balance")

    def get_latest_count():
        # Get the largest stock recalculation count
        existing_query = text("""SELECT MAX(stock_recalculation_count) AS largest_modification 
                                FROM tbl_stock_on_hand;
                                """)

        largest_count = db.execute(
            existing_query).fetchone()  # or .fetchall() if expecting multiple rows
        if largest_count[0]:
            new_stock_recalculation_count = largest_count[0] + 1
        else:
            new_stock_recalculation_count = 1

        return new_stock_recalculation_count


    try:
        # Execute the query and fetch all rows
        result = db.execute(query).fetchall()
        latest_count = get_latest_count()

        # Convert the result into a list of dictionaries
        records = [
            {
                "rawmaterialid": row[0],
                "warehouseid": row[2],
                "new_beginning_balance": row[5],
                "statusid": row[7]
            }
            for row in result
        ]

        # Step 2: Transform and insert the data into the database
        for record in records:
            rm_soh_item = StockOnHand(rm_code_id=record["rawmaterialid"],
                                      warehouse_id=record["warehouseid"],
                                      rm_soh=record["new_beginning_balance"],
                                      status_id= record["statusid"],
                                      date_computed=params_date,
                                      stock_recalculation_count=latest_count)
            db.add(rm_soh_item)
            db.commit()
            db.refresh(rm_soh_item)

        # Return a success message upon successful insertion
        return {"message": "The raw material stock updated successfully."}

    except Exception as e:
        # Handle any unexpected exceptions and return a 500 error with details
        raise HTTPException(status_code=500, detail=str(e))


# Helping function for the api
def clear_table_func(table, db):
    """
    Updates the `date_computed` column to the current date for records where it is NULL in the given table.
    """
    try:

        # Create an update query
        stmt = (
            update(table)
            .where((table.is_cleared.is_(None)) | (table.is_cleared == False))  # Check for NULL or False
            .values(is_cleared=True)  # Set is_clear to True
        )

        # Only uncomment this for unclearing the records
        # stmt = (
        #     update(table)
        #     .where((table.is_cleared == True))  # Check for NULL or False
        #     .values(is_cleared=False)  # Set is_clear to True
        # )

        # Execute the query
        db.execute(stmt)
        db.commit()
        return True

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update table {table.__tablename__}: {e}")

@router.post("/clear-table-data")
async def clear_table_data(tbl: str, db: get_db = Depends()):
    """
    Updates the `is_cleared` column to True for all specified tables.
    """

    if tbl == 'notes':
        tables = [
            TempNotes,
           ]

    elif tbl == 'preparation forms':
        tables = [
            TempPreparationForm,
        ]

    elif tbl == 'transfer forms':
        tables = [
            TempTransferForm,
        ]

    elif tbl == 'outgoing forms':
        tables = [
            TempOutgoingReport,
        ]

    elif tbl == 'receiving forms':
        tables = [
            TempReceivingReport,
        ]

    elif tbl == 'change status forms':
        tables = [
            TempHeldForm,
        ]

    elif tbl == 'all':
        tables = [
            TempNotes,
            TempPreparationForm,
            TempTransferForm,
            TempOutgoingReport,
            TempReceivingReport,
            TempHeldForm,
        ]

    updated_tables = []

    for table in tables:
        success = clear_table_func(table, db)
        if success:
            updated_tables.append(table.__tablename__)

    return {"message": "Update successful", "updated_tables": updated_tables}


@router.get("/check/rm-stock-value/")
async def check_stock(rm_id: UUID, warehouse_id: UUID, entered_qty: float, status_id: Optional[UUID]=None, db: get_db = Depends()):
    try:


        new_beginning_query = text(f"""SELECT new_beginning_balance FROM public.view_ending_stocks_balance
                                   WHERE warehouseid = '{warehouse_id}'
                                           AND statusid = '{status_id}'
                                           AND rawmaterialid = '{rm_id}'
                                            """)

        result = db.execute(new_beginning_query)
        beginning_balance = result.fetchone()
        # Check if there is a record after executing the query


        if beginning_balance:

            # Check if the entered_qty is less or equal than the beginning balance
            #  Returns true if the entered quantity is less or equal
            # Returns false if the entered quantity exceeds

            if float(beginning_balance[0]) >= entered_qty:

                return True

            else:
                return False

        else:
            return False
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/check/rm-stock-value/for-update/")
async def check_stock_for_update(rm_id: UUID,
                                 warehouse_id: UUID,
                                 prev_entered_qty: float,
                                 new_entered_qty: float,
                                 status_id: Optional[UUID]=None,
                                 db: get_db = Depends()
                                 ):
    try:
        # Check if the status id is null
        ending_balance_query = text(f"""SELECT new_beginning_balance FROM public.view_ending_stocks_balance
                                   WHERE warehouseid = '{warehouse_id}'
                                           AND statusid = '{status_id}'
                                           AND rawmaterialid = '{rm_id}'    
                                            """)

        ending_balance_result = db.execute(ending_balance_query)
        ending_balance = ending_balance_result.fetchone()

        sum_of_beginning_and_entered_qty = float(ending_balance[0]) + float(prev_entered_qty)
        print(sum_of_beginning_and_entered_qty)

        difference = sum_of_beginning_and_entered_qty - float(new_entered_qty)
        print(difference)

        if difference >= 0:
            return True
        else:
            return False

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))