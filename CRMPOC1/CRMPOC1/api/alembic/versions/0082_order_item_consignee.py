"""Link each order line item to its own consignee address."""
from alembic import op
import sqlalchemy as sa

revision = "0082_order_item_consignee"
down_revision = "0081_query_purge_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("order_items") as batch:
        batch.add_column(sa.Column("consignee_address_id", sa.Integer(), nullable=True))
        batch.create_index("ix_order_items_consignee_address_id", ["consignee_address_id"])
        batch.create_foreign_key(
            "fk_order_items_consignee_address_id", "order_consignee_addresses",
            ["consignee_address_id"], ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("order_items") as batch:
        batch.drop_constraint("fk_order_items_consignee_address_id", type_="foreignkey")
        batch.drop_index("ix_order_items_consignee_address_id")
        batch.drop_column("consignee_address_id")
