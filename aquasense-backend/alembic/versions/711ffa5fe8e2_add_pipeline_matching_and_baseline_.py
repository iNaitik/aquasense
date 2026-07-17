"""add pipeline matching and baseline fields

Revision ID: 711ffa5fe8e2
Revises: b2c3d4e5f6a7
Create Date: 2026-07-18 01:11:26.311762

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '711ffa5fe8e2'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('complaints', sa.Column('matched_pipeline_id', sa.Integer(), nullable=True))
    op.add_column('complaints', sa.Column('pipeline_distance_m', sa.Float(), nullable=True))
    op.create_index(op.f('ix_complaints_matched_pipeline_id'), 'complaints', ['matched_pipeline_id'], unique=False)
    op.create_foreign_key(
        'fk_complaints_matched_pipeline_id_pipelines',
        'complaints',
        'pipelines',
        ['matched_pipeline_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.add_column('pipelines', sa.Column('baseline_complaints_30d', sa.Integer(), nullable=True))
    op.add_column('pipelines', sa.Column('baseline_leakage_complaints_30d', sa.Integer(), nullable=True))
    
    # Safely backfill baseline fields from existing pipeline data
    op.execute(
        "UPDATE pipelines SET "
        "baseline_complaints_30d = complaints_last_30_days, "
        "baseline_leakage_complaints_30d = leakage_complaints_30d"
    )
    
    op.alter_column('pipelines', 'baseline_complaints_30d', nullable=False)
    op.alter_column('pipelines', 'baseline_leakage_complaints_30d', nullable=False)


def downgrade() -> None:
    op.drop_column('pipelines', 'baseline_leakage_complaints_30d')
    op.drop_column('pipelines', 'baseline_complaints_30d')
    op.drop_constraint('fk_complaints_matched_pipeline_id_pipelines', 'complaints', type_='foreignkey')
    op.drop_index(op.f('ix_complaints_matched_pipeline_id'), table_name='complaints')
    op.drop_column('complaints', 'pipeline_distance_m')
    op.drop_column('complaints', 'matched_pipeline_id')
