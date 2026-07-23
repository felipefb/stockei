"""receiving, losses e custo de produto (P10/P11/P5)

Revision ID: a1e7c40d21f0
Revises: 9b0c0ba77354
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1e7c40d21f0'
down_revision: Union[str, Sequence[str], None] = '9b0c0ba77354'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('products', sa.Column('cost_price', sa.Float(), nullable=False,
                                        server_default='0'))
    op.add_column('movements', sa.Column('reason', sa.String(length=30), nullable=False,
                                         server_default=''))
    op.add_column('movements', sa.Column('note', sa.String(length=255), nullable=False,
                                         server_default=''))
    op.add_column('movements', sa.Column('unit_value', sa.Float(), nullable=False,
                                         server_default='0'))

    op.create_table(
        'receiving_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('store_id', sa.Integer(), sa.ForeignKey('stores.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('nfe_key', sa.String(length=60), nullable=False, server_default=''),
        sa.Column('supplier', sa.String(length=255), nullable=False, server_default=''),
        sa.Column('issued_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_receiving_sessions_store_id', 'receiving_sessions', ['store_id'])
    op.create_index('ix_receiving_sessions_nfe_key', 'receiving_sessions', ['nfe_key'])

    op.create_table(
        'receiving_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(),
                  sa.ForeignKey('receiving_sessions.id'), nullable=False),
        sa.Column('ean', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('description', sa.String(length=500), nullable=False, server_default=''),
        sa.Column('expected_qty', sa.Float(), nullable=False, server_default='0'),
        sa.Column('checked_qty', sa.Float(), nullable=False, server_default='0'),
        sa.Column('unit_cost', sa.Float(), nullable=False, server_default='0'),
        sa.Column('item_status', sa.String(length=20), nullable=False,
                  server_default='pendente'),
    )
    op.create_index('ix_receiving_items_session_id', 'receiving_items', ['session_id'])
    op.create_index('ix_recv_session_ean', 'receiving_items', ['session_id', 'ean'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('receiving_items')
    op.drop_table('receiving_sessions')
    op.drop_column('movements', 'unit_value')
    op.drop_column('movements', 'note')
    op.drop_column('movements', 'reason')
    op.drop_column('products', 'cost_price')
