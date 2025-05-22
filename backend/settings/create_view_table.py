from sqlalchemy import text
from backend.settings.database import engine
from backend.settings.view_table_queries import (CREATE_BEGGINING_VIEW_QUERY,
                                                 CREATE_ENDING_VIEW_QUERY,
                                                 CREATE_ADJUSTED_ENDING_VIEW_QUERY
                                                 )


def create_beginning_view_table():
    """Ensures the view is created when FastAPI starts."""
    with engine.connect() as connection:
        connection.execute(text(CREATE_BEGGINING_VIEW_QUERY))
        connection.commit()
        print("✅ View `view_beginning_soh` created successfully!")


def create_ending_view_table():
    """Ensures the view is created when FastAPI starts."""
    with engine.connect() as connection:
        connection.execute(text(CREATE_ENDING_VIEW_QUERY))
        connection.commit()
        print("✅ View `view_ending_stocks_balance` created successfully!")


def create_adjusted_ending_view_table():
    """Ensures the view is created when FastAPI starts."""
    with engine.connect() as connection:
        connection.execute(text(CREATE_ADJUSTED_ENDING_VIEW_QUERY))
        connection.commit()
        print("✅ View `view_stock_ending_balance` created successfully!")



