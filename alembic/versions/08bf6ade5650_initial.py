"""initial

Revision ID: 08bf6ade5650
Revises: 
Create Date: 2026-04-08 19:41:43.721190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08bf6ade5650'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial users and events tables."""
    op.create_table(
        'users',
        sa.Column('username', sa.VARCHAR(length=50), nullable=False),
        sa.Column('password_hash', sa.VARCHAR(length=200), nullable=False),
        sa.Column('email', sa.VARCHAR(length=120), nullable=True),
        sa.Column('phone', sa.VARCHAR(length=20), nullable=True),
        sa.PrimaryKeyConstraint('username'),
        sa.UniqueConstraint('username'),
    )
    op.create_table(
        'events',
        sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column('title', sa.VARCHAR(length=100), nullable=False),
        sa.Column('description', sa.VARCHAR(length=500), nullable=True),
        sa.Column('type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('start_time', sa.VARCHAR(length=50), nullable=True),
        sa.Column('end_time', sa.VARCHAR(length=50), nullable=True),
        sa.Column('latitude', sa.FLOAT(), nullable=False),
        sa.Column('longitude', sa.FLOAT(), nullable=False),
        sa.Column('submitter', sa.VARCHAR(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Drop initial tables."""
    op.drop_table('events')
    op.drop_table('users')
