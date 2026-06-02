"""add payment context to transactions

Revision ID: 3f1c9e8a2b74
Revises: 96b3a9d50eb1
Create Date: 2026-06-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3f1c9e8a2b74'
down_revision: Union[str, Sequence[str], None] = '96b3a9d50eb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transactions', sa.Column('merchant_request_id', sa.String(), nullable=True))
    op.add_column(
        'transactions',
        sa.Column(
            'tier',
            postgresql.ENUM('FREE', 'BASIC', 'PRO', name='subscriptiontierinfo', create_type=False),
            nullable=True,
        ),
    )
    op.add_column('transactions', sa.Column('failure_reason', sa.Text(), nullable=True))
    op.create_index(op.f('ix_transactions_merchant_request_id'), 'transactions', ['merchant_request_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_transactions_merchant_request_id'), table_name='transactions')
    op.drop_column('transactions', 'failure_reason')
    op.drop_column('transactions', 'tier')
    op.drop_column('transactions', 'merchant_request_id')
