"""step17 worker_heartbeats table

Revision ID: a1b2c3d4e5f6
Revises: ef40c9a51668
Create Date: 2026-09-10 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ef40c9a51668'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'worker_heartbeats',
        sa.Column('worker_id', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True, server_default='active'),
        sa.Column('current_job_id', sa.String(), nullable=True),
        sa.Column('completed_jobs', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_jobs', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('started_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('last_heartbeat', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('worker_id')
    )
    op.create_index(op.f('ix_worker_heartbeats_status'), 'worker_heartbeats', ['status'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_worker_heartbeats_status'), table_name='worker_heartbeats')
    op.drop_table('worker_heartbeats')
