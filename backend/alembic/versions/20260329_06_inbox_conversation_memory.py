"""Add inbox conversation memory and conversation links.

Revision ID: 20260329_06
Revises: 20260329_05
Create Date: 2026-03-29 23:58:00
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import func


revision = "20260329_06"
down_revision = "20260329_05"
branch_labels = None
depends_on = None


def _inspector(bind):
    return sa.inspect(bind)


def _has_table(bind, table_name: str) -> bool:
    return _inspector(bind).has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in _inspector(bind).get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    return any(item["name"] == index_name for item in _inspector(bind).get_indexes(table_name))


def _uuid_type(bind):
    return postgresql.UUID(as_uuid=True) if bind.dialect.name == "postgresql" else sa.Uuid()


def upgrade() -> None:
    bind = op.get_bind()
    uuid_type = _uuid_type(bind)

    if not _has_table(bind, "inbox_conversations"):
        op.create_table(
            "inbox_conversations",
            sa.Column("id", uuid_type, primary_key=True, nullable=False),
            sa.Column("page_id", sa.String(), sa.ForeignKey("facebook_pages.page_id"), nullable=True),
            sa.Column("sender_id", sa.String(), nullable=False),
            sa.Column("recipient_id", sa.String(), nullable=True),
            sa.Column("conversation_summary", sa.String(), nullable=True),
            sa.Column("current_intent", sa.String(), nullable=True),
            sa.Column("customer_facts", sa.JSON(), nullable=True),
            sa.Column("needs_human_handoff", sa.Boolean(), nullable=True, server_default=sa.false()),
            sa.Column("handoff_reason", sa.String(), nullable=True),
            sa.Column("latest_customer_message_id", sa.String(), nullable=True),
            sa.Column("latest_reply_message_id", sa.String(), nullable=True),
            sa.Column("last_customer_message_at", sa.DateTime(), nullable=True),
            sa.Column("last_ai_reply_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("page_id", "sender_id", name="uq_inbox_conversations_page_sender"),
        )
        op.create_index("ix_inbox_conversations_page_id", "inbox_conversations", ["page_id"], unique=False)
        op.create_index("ix_inbox_conversations_sender_id", "inbox_conversations", ["sender_id"], unique=False)

    if _has_table(bind, "inbox_message_logs") and not _has_column(bind, "inbox_message_logs", "conversation_id"):
        op.add_column("inbox_message_logs", sa.Column("conversation_id", uuid_type, nullable=True))
        if bind.dialect.name == "postgresql":
            op.create_foreign_key(
                "fk_inbox_message_logs_conversation_id",
                "inbox_message_logs",
                "inbox_conversations",
                ["conversation_id"],
                ["id"],
            )

    if _has_table(bind, "inbox_message_logs") and not _has_index(bind, "inbox_message_logs", "ix_inbox_message_logs_conversation_id"):
        op.create_index("ix_inbox_message_logs_conversation_id", "inbox_message_logs", ["conversation_id"], unique=False)

    if _has_table(bind, "inbox_conversations") and _has_table(bind, "inbox_message_logs"):
        metadata = sa.MetaData()
        conversations = sa.Table("inbox_conversations", metadata, autoload_with=bind)
        message_logs = sa.Table("inbox_message_logs", metadata, autoload_with=bind)

        distinct_pairs = bind.execute(
            sa.select(
                message_logs.c.page_id,
                message_logs.c.sender_id,
                func.max(message_logs.c.recipient_id).label("recipient_id"),
            )
            .where(
                message_logs.c.page_id.isnot(None),
                message_logs.c.sender_id.isnot(None),
            )
            .group_by(message_logs.c.page_id, message_logs.c.sender_id)
        ).all()

        for row in distinct_pairs:
            page_id = row.page_id
            sender_id = row.sender_id
            recipient_id = row.recipient_id
            if not page_id or not sender_id:
                continue

            existing = bind.execute(
                sa.select(conversations.c.id).where(
                    conversations.c.page_id == page_id,
                    conversations.c.sender_id == sender_id,
                )
            ).scalar()
            if existing is None:
                conversation_id = uuid.uuid4()
                bind.execute(
                    conversations.insert().values(
                        id=conversation_id,
                        page_id=page_id,
                        sender_id=sender_id,
                        recipient_id=recipient_id,
                        customer_facts={},
                    )
                )
            else:
                conversation_id = existing

            bind.execute(
                message_logs.update()
                .where(
                    message_logs.c.page_id == page_id,
                    message_logs.c.sender_id == sender_id,
                    message_logs.c.conversation_id.is_(None),
                )
                .values(conversation_id=conversation_id)
            )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "inbox_message_logs"):
        if _has_index(bind, "inbox_message_logs", "ix_inbox_message_logs_conversation_id"):
            op.drop_index("ix_inbox_message_logs_conversation_id", table_name="inbox_message_logs")
        if _has_column(bind, "inbox_message_logs", "conversation_id"):
            if bind.dialect.name == "postgresql":
                op.drop_constraint("fk_inbox_message_logs_conversation_id", "inbox_message_logs", type_="foreignkey")
            op.drop_column("inbox_message_logs", "conversation_id")

    if _has_table(bind, "inbox_conversations"):
        op.drop_table("inbox_conversations")
