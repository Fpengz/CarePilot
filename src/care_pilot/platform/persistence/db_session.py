"""
Manages SQLModel database sessions for authentication operations.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlmodel import Session

# Assume engine is configured and available, e.g., from care_pilot.platform.persistence.engine
# For now, placeholder:
# engine = create_engine("sqlite:///./auth.db") # Example connection string


class AuthSQLModelSessionManager:
    def __init__(self, engine: Engine):
        self.engine = engine

    @contextmanager
    def get_session(self) -> Iterator[Session]:
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
