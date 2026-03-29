"""Add source platform metadata to campaigns and videos.

Revision ID: 20260329_05
Revises: 20260329_04
Create Date: 2026-03-29 23:59:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260329_05"
down_revision = "20260329_04"
branch_labels = None
depends_on = None


def _inspector(bind):
    return sa.inspect(bind)


def _has_table(bind, table_name: str) -> bool:
    return _inspector(bind).has_table(table_name)


def _has_column(bind, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in _inspector(bind).get_columns(table_name))


def _has_index(bind, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in _inspector(bind).get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    additions = {
        "campaigns": [
            ("source_platform", sa.String()),
            ("source_kind", sa.String()),
        ],
        "videos": [
            ("source_platform", sa.String()),
            ("source_kind", sa.String()),
        ],
    }

    for table_name, columns in additions.items():
        if not _has_table(bind, table_name):
            continue
        for column_name, column_type in columns:
            if not _has_column(bind, table_name, column_name):
                op.add_column(table_name, sa.Column(column_name, column_type, nullable=True))

    if _has_table(bind, "campaigns"):
        op.execute("UPDATE campaigns SET source_platform = 'tiktok' WHERE source_platform IS NULL")
        op.execute("UPDATE campaigns SET source_kind = 'tiktok_legacy' WHERE source_kind IS NULL")
        if not _has_index(bind, "campaigns", "ix_campaigns_source_platform"):
            op.create_index("ix_campaigns_source_platform", "campaigns", ["source_platform"])

    if _has_table(bind, "videos"):
        op.execute("UPDATE videos SET source_platform = 'tiktok' WHERE source_platform IS NULL")
        op.execute("UPDATE videos SET source_kind = 'tiktok_legacy' WHERE source_kind IS NULL")
        if not _has_index(bind, "videos", "ix_videos_source_platform"):
            op.create_index("ix_videos_source_platform", "videos", ["source_platform"])


def downgrade() -> None:
    bind = op.get_bind()

    for table_name in ["videos", "campaigns"]:
        if not _has_table(bind, table_name):
            continue
        index_name = f"ix_{table_name}_source_platform"
        if _has_index(bind, table_name, index_name):
            op.drop_index(index_name, table_name=table_name)
        for column_name in ["source_kind", "source_platform"]:
            if _has_column(bind, table_name, column_name):
                op.drop_column(table_name, column_name)
