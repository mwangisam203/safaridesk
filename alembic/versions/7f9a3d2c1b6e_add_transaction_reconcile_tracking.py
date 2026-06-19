"""add transaction reconcile tracking

Revision ID: 7f9a3d2c1b6e
Revises: 4c8b29f61d20
Create Date: 2026-06-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f9a3d2c1b6e"
down_revision: Union[str, Sequence[str], None] = "4c8b29f61d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "reconcile_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "transactions",
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transactions", "last_reconciled_at")
    op.drop_column("transactions", "reconcile_attempts")
