"""
Provide configured SQLite connections.

This module provides a central factory for SQLite connections, ensuring
safe concurrent configuration (WAL mode, busy_timeout) for production use.
"""

import sqlite3
import threading

_local = threading.local()


def get_connection(db_path: str) -> sqlite3.Connection:
    """
    Create a configured SQLite connection with WAL mode enabled.
    Uses thread-local storage to reuse connections within the same thread.
    """
    if not hasattr(_local, "connections"):
        _local.connections = {}

    if db_path in _local.connections:
        try:
            # Check if connection is still alive
            _local.connections[db_path].cursor()
        except (sqlite3.ProgrammingError, sqlite3.OperationalError):
            del _local.connections[db_path]

    if db_path not in _local.connections:
        # timeout=5.0 configures the busy_timeout under the hood
        conn = sqlite3.connect(db_path, timeout=10.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-64000;")  # 64MB cache
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA mmap_size=268435456;")  # 256MB mmap
        conn.row_factory = sqlite3.Row
        _local.connections[db_path] = conn

    return _local.connections[db_path]
