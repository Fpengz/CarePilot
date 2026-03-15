"""
Implement the SQLite application store.

This module aggregates SQLite repositories into a shared application store.
"""

from .sqlite_repository import SQLiteRepository


class SQLiteAppStore(SQLiteRepository):
    pass
