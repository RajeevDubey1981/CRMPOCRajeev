"""wa_knowledge: the WhatsApp assistant's knowledge, managed from the CRM

Revision ID: 0115_whatsapp_knowledge
Revises: 0114_whatsapp_auto_reply
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import LONGTEXT

revision = "0115_whatsapp_knowledge"
down_revision = "0114_whatsapp_auto_reply"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "wa_knowledge" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "wa_knowledge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False, server_default=""),
        sa.Column("body", sa.Text().with_variant(LONGTEXT(), "mysql"), nullable=False),
        sa.Column("always_send", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("source", sa.String(20), nullable=False, server_default="typed"),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    if "wa_knowledge" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("wa_knowledge")
