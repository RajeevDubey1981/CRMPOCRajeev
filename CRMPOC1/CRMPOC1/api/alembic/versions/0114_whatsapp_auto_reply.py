"""WhatsApp automatic replies: pending_action on conversations, wa_ai_runs, wa_settings

Revision ID: 0114_whatsapp_auto_reply
Revises: 0113_whatsapp_inbox
"""
import sqlalchemy as sa
from alembic import op

revision = "0114_whatsapp_auto_reply"
down_revision = "0113_whatsapp_inbox"
branch_labels = None
depends_on = None


def _has(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("wa_conversations")}
    if "pending_action" not in cols:
        op.add_column("wa_conversations", sa.Column("pending_action", sa.Text(), nullable=True))
    if not _has("wa_ai_runs"):
        op.create_table(
            "wa_ai_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("wa_conversations.id"), nullable=False),
            sa.Column("inbound_message_id", sa.Integer(), sa.ForeignKey("wa_messages.id"), nullable=False),
            sa.Column("outcome", sa.String(30)),
            sa.Column("action", sa.String(30)),
            sa.Column("detail", sa.String(500)),
            sa.Column("tokens", sa.Integer()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_wa_ai_runs_conversation_id", "wa_ai_runs", ["conversation_id"])
        op.create_index("ux_wa_ai_runs_inbound", "wa_ai_runs", ["inbound_message_id"], unique=True)
    if not _has("wa_settings"):
        op.create_table(
            "wa_settings",
            sa.Column("key", sa.String(60), primary_key=True),
            sa.Column("value", sa.String(500)),
            sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )


def downgrade() -> None:
    for table in ("wa_settings", "wa_ai_runs"):
        if _has(table):
            op.drop_table(table)
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("wa_conversations")}
    if "pending_action" in cols:
        op.drop_column("wa_conversations", "pending_action")
