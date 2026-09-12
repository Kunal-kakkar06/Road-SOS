"""step19 backup_replicas table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-10 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'backup_replicas',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('backup_id', sa.String(length=255), nullable=False),
        sa.Column('storage_provider', sa.String(length=50), server_default='s3', nullable=False),
        sa.Column('bucket', sa.String(length=255), nullable=False),
        sa.Column('object_key', sa.String(length=500), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=True),
        sa.Column('encryption_mode', sa.String(length=50), server_default='AES256', nullable=True),
        sa.Column('encryption_key_id', sa.String(length=255), nullable=True),
        sa.Column('remote_etag', sa.String(length=128), nullable=True),
        sa.Column('remote_sha256', sa.String(length=128), nullable=True),
        sa.Column('remote_size_bytes', sa.Integer(), nullable=True),
        sa.Column('upload_started_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('restore_verified_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='RUNNING', nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='1', nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['backup_id'], ['backup_records.backup_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_backup_replicas_backup_id'), 'backup_replicas', ['backup_id'], unique=False)
    op.create_index(op.f('ix_backup_replicas_object_key'), 'backup_replicas', ['object_key'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_backup_replicas_object_key'), table_name='backup_replicas')
    op.drop_index(op.f('ix_backup_replicas_backup_id'), table_name='backup_replicas')
    op.drop_table('backup_replicas')
