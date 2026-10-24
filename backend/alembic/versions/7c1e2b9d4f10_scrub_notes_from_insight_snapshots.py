"""scrub parent notes from stored insight snapshots

Notes are no longer sent to the model or kept in input_snapshot. This removes them
from snapshots saved before that change.

Revision ID: 7c1e2b9d4f10
Revises: 339994bba3e9
Create Date: 2026-10-24 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7c1e2b9d4f10'
down_revision: Union[str, Sequence[str], None] = '339994bba3e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE career_insights SET input_snapshot = input_snapshot - 'notes' WHERE input_snapshot ? 'notes'")


def downgrade() -> None:
    """Downgrade schema."""
    # Irreversible by design: the removed notes are not restored.
    pass
