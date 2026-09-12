"""step18 backup_records table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-10 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'backup_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('backup_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='RUNNING', nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('checksum', sa.String(length=128), nullable=True),
        sa.Column('database_version', sa.String(length=100), nullable=True),
        sa.Column('app_version', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backup_records_backup_id'), 'backup_records', ['backup_id'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_backup_records_backup_id'), table_name='backup_records')
    op.drop_table('backup_records')
