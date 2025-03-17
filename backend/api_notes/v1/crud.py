from backend.api_notes.v1.exceptions import (NotesNotFoundException,
                                             NotesUpdateException, NotesSoftDeleteException, NotesRestoreException)
from backend.api_notes.v1.main import AppCRUD
from backend.api_notes.v1.models import TempNotes
from backend.api_notes.v1.schemas import NotesCreate, NotesUpdate
from uuid import UUID
from sqlalchemy import or_

# These are the code for the app to communicate to the database
# This is where the program communicate in the database
class TempNotesCRUD(AppCRUD):
    def create_notes(self, notes: NotesCreate):
        notes_item = TempNotes(product_code=notes.product_code,
                                  lot_number=notes.lot_number,
                                    product_kind_id=notes.product_kind_id,
                                    stock_change_date=notes.stock_change_date,
                                   updated_by_id=notes.updated_by_id,
                                   created_by_id=notes.created_by_id)
        self.db.add(notes_item)
        self.db.commit()
        self.db.refresh(notes_item)
        return notes_item

    def get_notes(self):
        # Query TempNotes with filters applied to is_cleared and is_deleted columns
        notes_item = self.db.query(TempNotes).filter(
            or_(
                TempNotes.is_cleared.is_(None),  # NULL check for is_cleared
                TempNotes.is_cleared == False # False check for is_cleared

            ),
            or_(
                TempNotes.is_deleted.is_(None),  # NULL check for is_deleted
                TempNotes.is_deleted == False  # False check for is_deleted
            )

        ).all()

        # Return the filtered records, or an empty list if no records are found
        if notes_item:
            return notes_item
        return []

    def get_deleted_notes(self):
        # Query TempNotes with filters applied to is_cleared and is_deleted columns
        notes_item = self.db.query(TempNotes).filter(
            or_(
                TempNotes.is_cleared == True  # False check for is_cleared

            ),
            or_(
                TempNotes.is_deleted == True  # False check for is_deleted
            )

        ).all()

        # Return the filtered records, or an empty list if no records are found
        if notes_item:
            return notes_item
        return []



    def get_historical_notes(self):
        # Query TempNotes with filters applied to is_cleared and is_deleted columns
        notes_item = self.db.query(TempNotes).filter(
            # TempNotes.is_cleared == True, # False check for is_cleared
            TempNotes.date_computed.is_not(None)
            ,
            or_(
                TempNotes.is_deleted.is_(None),  # NULL check for is_deleted
                TempNotes.is_deleted == False  # False check for is_deleted
            )

        ).all()

        # Return the filtered records, or an empty list if no records are found
        if notes_item:
            return notes_item
        return []





    def update_notes(self, notes_id: UUID, notes_update: NotesUpdate):
        try:
            notes = self.db.query(TempNotes).filter(TempNotes.id == notes_id).first()
            if not notes or notes.is_deleted:
                raise NotesNotFoundException(detail="Notes not found or already deleted.")

            for key, value in notes_update.model_dump(exclude_unset=True).items():
                setattr(notes, key, value)
            self.db.commit()
            self.db.refresh(notes)
            return notes

        except Exception as e:
            raise NotesUpdateException(detail=f"Error: {str(e)}")

    def soft_delete_notes(self, notes_id: UUID):
        try:
            notes = self.db.query(TempNotes).filter(TempNotes.id == notes_id).first()
            if not notes or notes.is_deleted:
                raise NotesNotFoundException(detail="Notes not found or already deleted.")

            notes.is_deleted = True
            self.db.commit()
            self.db.refresh(notes)
            return notes

        except Exception as e:
            raise NotesSoftDeleteException(detail=f"Error: {str(e)}")


    def restore_notes(self, notes_id: UUID):
        try:
            notes = self.db.query(TempNotes).filter(TempNotes.id == notes_id).first()
            if not notes or not notes.is_deleted:
                raise NotesNotFoundException(detail="Notes not found or already restored.")

            notes.is_deleted = False
            self.db.commit()
            self.db.refresh(notes)
            return notes

        except Exception as e:
            raise NotesRestoreException(detail=f"Error: {str(e)}")
