"""
Provide configured SQLite connections.

This module provides a central factory for SQLite connections, ensuring
safe concurrent configuration (WAL mode, busy_timeout) for production use.
"""

import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    """Create a configured SQLite connection with WAL mode enabled."""
    # timeout=5.0 configures the busy_timeout under the hood
    conn = sqlite3.connect(db_path, timeout=5.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn
