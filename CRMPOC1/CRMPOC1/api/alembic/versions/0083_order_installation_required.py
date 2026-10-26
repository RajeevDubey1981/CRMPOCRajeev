"""Allow an order to be delivered without an installation workflow."""
from alembic import op
import sqlalchemy as sa

revision = "0083_order_installation_required"
down_revision = "0082_order_item_consignee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("installation_required", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("order_items", sa.Column("installation_auto_completed", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("order_items", "installation_auto_completed")
    op.drop_column("orders", "installation_required")
