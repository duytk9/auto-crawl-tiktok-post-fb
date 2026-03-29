"""Add operator workspace fields for inbox conversations.

Revision ID: 20260329_07
Revises: 20260329_06
Create Date: 2026-03-29 23:59:30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_07"
down_revision = "20260329_06"
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

    if _has_table(bind, "inbox_conversations"):
        if not _has_column(bind, "inbox_conversations", "status"):
            op.add_column(
                "inbox_conversations",
                sa.Column("status", sa.String(), nullable=False, server_default="ai_active"),
            )
        if not _has_column(bind, "inbox_conversations", "assigned_to_user_id"):
            op.add_column("inbox_conversations", sa.Column("assigned_to_user_id", uuid_type, nullable=True))
            if bind.dialect.name == "postgresql":
                op.create_foreign_key(
                    "fk_inbox_conversations_assigned_to_user_id",
                    "inbox_conversations",
                    "users",
                    ["assigned_to_user_id"],
                    ["id"],
                )
        if not _has_column(bind, "inbox_conversations", "internal_note"):
            op.add_column("inbox_conversations", sa.Column("internal_note", sa.String(), nullable=True))
        if not _has_column(bind, "inbox_conversations", "last_operator_reply_at"):
            op.add_column("inbox_conversations", sa.Column("last_operator_reply_at", sa.DateTime(), nullable=True))
        if not _has_column(bind, "inbox_conversations", "resolved_at"):
            op.add_column("inbox_conversations", sa.Column("resolved_at", sa.DateTime(), nullable=True))

        if not _has_index(bind, "inbox_conversations", "ix_inbox_conversations_status"):
            op.create_index("ix_inbox_conversations_status", "inbox_conversations", ["status"], unique=False)
        if not _has_index(bind, "inbox_conversations", "ix_inbox_conversations_assigned_to_user_id"):
            op.create_index("ix_inbox_conversations_assigned_to_user_id", "inbox_conversations", ["assigned_to_user_id"], unique=False)

        op.execute(
            sa.text(
                """
                UPDATE inbox_conversations
                SET status = CASE
                    WHEN needs_human_handoff = true THEN 'operator_active'
                    ELSE 'ai_active'
                END
                WHERE status IS NULL OR status = ''
                """
            )
        )

    if _has_table(bind, "inbox_message_logs"):
        if not _has_column(bind, "inbox_message_logs", "reply_source"):
            op.add_column("inbox_message_logs", sa.Column("reply_source", sa.String(), nullable=True))
        if not _has_column(bind, "inbox_message_logs", "reply_author_user_id"):
            op.add_column("inbox_message_logs", sa.Column("reply_author_user_id", uuid_type, nullable=True))
            if bind.dialect.name == "postgresql":
                op.create_foreign_key(
                    "fk_inbox_message_logs_reply_author_user_id",
                    "inbox_message_logs",
                    "users",
                    ["reply_author_user_id"],
                    ["id"],
                )
        if not _has_index(bind, "inbox_message_logs", "ix_inbox_message_logs_reply_author_user_id"):
            op.create_index("ix_inbox_message_logs_reply_author_user_id", "inbox_message_logs", ["reply_author_user_id"], unique=False)

        op.execute(
            sa.text(
                """
                UPDATE inbox_message_logs
                SET reply_source = 'ai'
                WHERE reply_source IS NULL
                  AND ai_reply IS NOT NULL
                  AND status = 'replied'
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "inbox_message_logs"):
        if _has_index(bind, "inbox_message_logs", "ix_inbox_message_logs_reply_author_user_id"):
            op.drop_index("ix_inbox_message_logs_reply_author_user_id", table_name="inbox_message_logs")
        if _has_column(bind, "inbox_message_logs", "reply_author_user_id"):
            if bind.dialect.name == "postgresql":
                op.drop_constraint("fk_inbox_message_logs_reply_author_user_id", "inbox_message_logs", type_="foreignkey")
            op.drop_column("inbox_message_logs", "reply_author_user_id")
        if _has_column(bind, "inbox_message_logs", "reply_source"):
            op.drop_column("inbox_message_logs", "reply_source")

    if _has_table(bind, "inbox_conversations"):
        if _has_index(bind, "inbox_conversations", "ix_inbox_conversations_assigned_to_user_id"):
            op.drop_index("ix_inbox_conversations_assigned_to_user_id", table_name="inbox_conversations")
        if _has_index(bind, "inbox_conversations", "ix_inbox_conversations_status"):
            op.drop_index("ix_inbox_conversations_status", table_name="inbox_conversations")
        if _has_column(bind, "inbox_conversations", "resolved_at"):
            op.drop_column("inbox_conversations", "resolved_at")
        if _has_column(bind, "inbox_conversations", "last_operator_reply_at"):
            op.drop_column("inbox_conversations", "last_operator_reply_at")
        if _has_column(bind, "inbox_conversations", "internal_note"):
            op.drop_column("inbox_conversations", "internal_note")
        if _has_column(bind, "inbox_conversations", "assigned_to_user_id"):
            if bind.dialect.name == "postgresql":
                op.drop_constraint("fk_inbox_conversations_assigned_to_user_id", "inbox_conversations", type_="foreignkey")
            op.drop_column("inbox_conversations", "assigned_to_user_id")
        if _has_column(bind, "inbox_conversations", "status"):
            op.drop_column("inbox_conversations", "status")
