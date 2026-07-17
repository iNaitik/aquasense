"""create complaint_status_history table

Revision ID: b2c3d4e5f6a7
Revises: 3ede0032390d
Create Date: 2026-07-17 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = '3ede0032390d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The complaint_status_enum type already exists in PostgreSQL (created by
    # the complaints table migration).  We reference it via raw SQL to avoid
    # SQLAlchemy trying to CREATE TYPE again.
    op.create_table(
        'complaint_status_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('complaint_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['complaint_id'], ['complaints.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_complaint_status_history_complaint_id', 'complaint_status_history', ['complaint_id'])

    # Now alter the column type to use the existing PG enum
    op.execute(
        "ALTER TABLE complaint_status_history "
        "ALTER COLUMN status TYPE complaint_status_enum "
        "USING status::complaint_status_enum"
    )


def downgrade() -> None:
    op.drop_index('ix_complaint_status_history_complaint_id', table_name='complaint_status_history')
    op.drop_table('complaint_status_history')
