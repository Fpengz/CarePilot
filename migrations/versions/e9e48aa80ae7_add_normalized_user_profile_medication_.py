"""Add normalized user profile, medication, reminder, meal, and symptom models

Revision ID: e9e48aa80ae7
Revises: 65e0dd6d9d4b
Create Date: 2026-03-27 01:24:00.362953

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'e9e48aa80ae7'
down_revision: str | Sequence[str] | None = '65e0dd6d9d4b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
