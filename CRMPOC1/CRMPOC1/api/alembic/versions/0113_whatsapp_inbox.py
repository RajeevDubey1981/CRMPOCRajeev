"""WhatsApp inbox: conversations, messages, webhook events, notes, and the whatsapp permission row for admin

Revision ID: 0113_whatsapp_inbox
Revises: 0112_email_confirmations
"""
import sqlalchemy as sa
from alembic import op

revision = "0113_whatsapp_inbox"
down_revision = "0112_email_confirmations"
branch_labels = None
depends_on = None


def _has(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    now = sa.func.now()
    if not _has("wa_conversations"):
        op.create_table(
            "wa_conversations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("wa_phone", sa.String(20), nullable=False),
            sa.Column("contact_name", sa.String(255)),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("ai_paused", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_inbound_at", sa.DateTime(timezone=True)),
            sa.Column("last_message_at", sa.DateTime(timezone=True)),
            sa.Column("last_message_preview", sa.String(200)),
            sa.Column("opted_out", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=now, nullable=False),
        )
        op.create_index("ix_wa_conversations_wa_phone", "wa_conversations", ["wa_phone"], unique=True)
        op.create_index("ix_wa_conversations_status", "wa_conversations", ["status"])
        op.create_index("ix_wa_conversations_last_message_at", "wa_conversations", ["last_message_at"])
    if not _has("wa_messages"):
        op.create_table(
            "wa_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("wa_conversations.id"), nullable=False),
            sa.Column("direction", sa.String(3), nullable=False),
            sa.Column("wa_message_id", sa.String(120)),
            sa.Column("msg_type", sa.String(20), nullable=False, server_default="text"),
            sa.Column("body", sa.Text()),
            sa.Column("media_id", sa.String(200)),
            sa.Column("media_mime", sa.String(100)),
            sa.Column("media_name", sa.String(255)),
            sa.Column("status", sa.String(20), nullable=False, server_default="received"),
            sa.Column("error", sa.String(500)),
            sa.Column("sent_by", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_wa_messages_conversation_id", "wa_messages", ["conversation_id"])
        op.create_index("ix_wa_messages_created_at", "wa_messages", ["created_at"])
        op.create_index("ux_wa_messages_wa_message_id", "wa_messages", ["wa_message_id"], unique=True)
    if not _has("wa_webhook_events"):
        op.create_table(
            "wa_webhook_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("error", sa.String(500)),
            sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _has("wa_notes"):
        op.create_table(
            "wa_notes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("wa_conversations.id"), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_wa_notes_conversation_id", "wa_notes", ["conversation_id"])

    # Role card: admin gets the whatsapp module. Other roles are switched on from the Permissions page.
    roles = sa.table("roles", sa.column("id", sa.Integer), sa.column("name", sa.String))
    perms = sa.table(
        "permissions",
        sa.column("role_id", sa.Integer), sa.column("module", sa.String), sa.column("sub_module", sa.String),
        sa.column("can_view", sa.Boolean), sa.column("can_create", sa.Boolean), sa.column("can_edit", sa.Boolean),
        sa.column("can_delete", sa.Boolean), sa.column("can_export", sa.Boolean),
    )
    role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "admin")).scalar()
    if role_id is not None and not bind.execute(
        sa.select(perms.c.role_id).where(perms.c.role_id == role_id, perms.c.module == "whatsapp", perms.c.sub_module.is_(None))
    ).first():
        op.bulk_insert(perms, [{"role_id": role_id, "module": "whatsapp", "sub_module": None,
                                "can_view": True, "can_create": True, "can_edit": True, "can_delete": True, "can_export": True}])


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM permissions WHERE module = 'whatsapp'"))
    for table in ("wa_notes", "wa_webhook_events", "wa_messages", "wa_conversations"):
        if _has(table):
            op.drop_table(table)
