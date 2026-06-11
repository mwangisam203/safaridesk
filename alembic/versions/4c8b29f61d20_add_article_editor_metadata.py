"""add article editor metadata

Revision ID: 4c8b29f61d20
Revises: 92fb86435125
Create Date: 2026-06-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c8b29f61d20"
down_revision: Union[str, Sequence[str], None] = "92fb86435125"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("category", sa.String(length=100), nullable=True))
    op.add_column(
        "articles", sa.Column("cover_image_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "articles", sa.Column("cover_image_alt", sa.String(length=255), nullable=True)
    )
    op.add_column("articles", sa.Column("seo_title", sa.String(length=255), nullable=True))
    op.add_column(
        "articles", sa.Column("seo_description", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "articles",
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("articles", "is_featured")
    op.drop_column("articles", "seo_description")
    op.drop_column("articles", "seo_title")
    op.drop_column("articles", "cover_image_alt")
    op.drop_column("articles", "cover_image_url")
    op.drop_column("articles", "category")
