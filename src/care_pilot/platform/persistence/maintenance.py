"""
Database maintenance and backup utilities.
"""

import sqlite3
import time
from pathlib import Path

from care_pilot.platform.observability import get_logger

logger = get_logger(__name__)


def backup_sqlite_db(db_path: str, backup_dir: str) -> str:
    """
    Safely backup a SQLite database using the backup API.
    Ensures the backup is consistent even if the database is being written to.
    """
    db_path_obj = Path(db_path)
    if not db_path_obj.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    backup_dir_obj = Path(backup_dir)
    backup_dir_obj.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir_obj / f"{db_path_obj.name}.{timestamp}.bak"

    logger.info("db_backup_start source=%s target=%s", db_path, backup_path)

    # Use SQLite's backup API for safe online backup
    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(str(backup_path))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()

    logger.info("db_backup_complete source=%s target=%s", db_path, backup_path)
    return str(backup_path)


def rotate_backups(backup_dir: str, keep_count: int = 7) -> None:
    """Keep only the latest N backups in the directory."""
    backup_dir_obj = Path(backup_dir)
    backups = sorted(backup_dir_obj.glob("*.bak"), key=lambda p: p.stat().st_mtime)

    if len(backups) > keep_count:
        for old_backup in backups[:-keep_count]:
            old_backup.unlink()
            logger.info("db_backup_rotated path=%s", old_backup)
