"""Backward-compatible re-exports from core.base."""
from core.base import BaseService as AppService, BaseRepository as AppCRUD

__all__ = ["AppService", "AppCRUD"]