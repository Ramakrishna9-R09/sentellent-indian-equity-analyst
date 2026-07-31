"""Add mentioned_tickers to article_signal.

Revision ID: 0002_article_signal_mentioned_tickers
Revises: 0001_initial_schema
Create Date: 2026-07-31
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_article_signal_mentioned"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "article_signal",
        sa.Column("mentioned_tickers", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("article_signal", "mentioned_tickers")
