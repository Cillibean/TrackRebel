"""add new columns

Revision ID: d3df17eb0384
Revises: 08bf6ade5650
Create Date: 2026-04-09 12:04:18.080181

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3df17eb0384'
down_revision: Union[str, Sequence[str], None] = '08bf6ade5650'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category, link, and contact columns to events."""
    op.add_column('events', sa.Column('category', sa.VARCHAR(length=50), nullable=True))
    op.add_column('events', sa.Column('link', sa.VARCHAR(length=255), nullable=True))
    op.add_column('events', sa.Column('contact', sa.VARCHAR(length=50), nullable=True))


def downgrade() -> None:
    """Remove category, link, and contact columns from events."""
    op.drop_column('events', 'contact')
    op.drop_column('events', 'link')
    op.drop_column('events', 'category')
