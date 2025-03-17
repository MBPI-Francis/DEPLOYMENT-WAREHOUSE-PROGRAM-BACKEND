
from backend.api_product_kinds.v1.models import ProductKind
from backend.settings.database import SessionLocal


def create_product_kind():
    """Creates product kinds in the database if they do not already exist."""

    session = SessionLocal()  # Create a session

    try:
        # Check if records already exist to prevent duplicates
        if not session.query(ProductKind).filter(ProductKind.id == 'MB').first():
            masterbatch = ProductKind(id='MB', name='Masterbatch')
            session.add(masterbatch)

        if not session.query(ProductKind).filter(ProductKind.id == 'DC').first():
            drycolor = ProductKind(id='DC', name='Dry Color')
            session.add(drycolor)

        session.commit()  # Commit transaction
    except Exception as e:
        session.rollback()  # Rollback on error
        print(f"Error creating product kinds: {e}")
    finally:
        session.close()  # Ensure session is closed
