"""Add call transfer and follow-up tracking fields

Revision ID: 0003_enhance_calls
Revises: 0002_submodule
Create Date: 2026-05-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0003_enhance_calls'
down_revision = '0002_submodule'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('calls', sa.Column('priority', sa.String(20), server_default='medium', nullable=False))
    op.add_column('calls', sa.Column('transferred_to', sa.Integer(), nullable=True))
    op.add_column('calls', sa.Column('is_transferred', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('calls', sa.Column('follow_up_notes', sa.Text(), nullable=True))
    op.add_column('calls', sa.Column('follow_up_status', sa.String(30), nullable=True))

    op.create_foreign_key('fk_calls_transferred_to', 'calls', 'users', ['transferred_to'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_calls_transferred_to', 'calls', type_='foreignkey')
    op.drop_column('calls', 'follow_up_status')
    op.drop_column('calls', 'follow_up_notes')
    op.drop_column('calls', 'is_transferred')
    op.drop_column('calls', 'transferred_to')
    op.drop_column('calls', 'priority')
