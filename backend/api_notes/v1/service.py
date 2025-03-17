from backend.api_notes.v1.exceptions import NotesCreateException, NotesNotFoundException
from backend.api_notes.v1.main import AppService
from backend.api_notes.v1.crud import TempNotesCRUD
from backend.api_notes.v1.schemas import NotesCreate, NotesUpdate
from uuid import UUID




# These are the code for the business logic like calculation etc.
class NotesService(AppService):
    def create_notes(self, item: NotesCreate):
        try:
            notes_item = TempNotesCRUD(self.db).create_notes(item)

        except Exception as e:
            raise NotesCreateException(detail=f"Error: {str(e)}")

        return notes_item

    def get_notes(self):
        try:
            notes_item = TempNotesCRUD(self.db).get_notes()

        except Exception as e:
            raise NotesNotFoundException(detail=f"Error: {str(e)}")
        return notes_item



    # This service or logical function calls the get_deleted_notes function from the TempNotesCRUD class
    def get_deleted_notes(self):
        try:
            notes_item = TempNotesCRUD(self.db).get_deleted_notes()

        except Exception as e:
            raise NotesNotFoundException(detail=f"Error: {str(e)}")
        return notes_item


    # This service or logical function calls the get_historical_notes function from the TempNotesCRUD class
    def get_historical_notes(self):
        try:
            notes_item = TempNotesCRUD(self.db).get_historical_notes()

        except Exception as e:
            raise NotesNotFoundException(detail=f"Error: {str(e)}")
        return notes_item



    # This is the service/business logic in updating the notes.
    def update_notes(self, notes_id: UUID, notes_update: NotesUpdate):
        notes = TempNotesCRUD(self.db).update_notes(notes_id, notes_update)
        return notes

    # This is the service/business logic in soft deleting the notes.
    def soft_delete_notes(self, notes_id: UUID):
        notes = TempNotesCRUD(self.db).soft_delete_notes(notes_id)
        return notes


    # This is the service/business logic in soft restoring the notes.
    def restore_notes(self, notes_id: UUID):
        notes = TempNotesCRUD(self.db).restore_notes(notes_id)
        return notes





