"""affiliate comment per page and per video

Revision ID: 20260402_01
Revises: 20260329_07_inbox_operator_workspace
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260402_01"
down_revision = "20260329_07_inbox_operator_workspace"
branch_labels = None
depends_on = None


affiliate_comment_status = sa.Enum(
    "disabled",
    "queued",
    "posted",
    "operator_required",
    name="affiliatecommentstatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    affiliate_comment_status.create(bind, checkfirst=True)

    op.add_column("facebook_pages", sa.Column("affiliate_comment_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("facebook_pages", sa.Column("affiliate_comment_text", sa.String(), nullable=True))
    op.add_column("facebook_pages", sa.Column("affiliate_link_url", sa.String(), nullable=True))
    op.add_column("facebook_pages", sa.Column("affiliate_comment_delay_seconds", sa.Integer(), nullable=False, server_default="60"))

    op.add_column("videos", sa.Column("fb_video_id", sa.String(), nullable=True))
    op.add_column("videos", sa.Column("fb_permalink_url", sa.String(), nullable=True))
    op.add_column(
        "videos",
        sa.Column(
            "affiliate_comment_status",
            affiliate_comment_status,
            nullable=False,
            server_default="disabled",
        ),
    )
    op.add_column("videos", sa.Column("affiliate_comment_text", sa.String(), nullable=True))
    op.add_column("videos", sa.Column("affiliate_comment_fb_id", sa.String(), nullable=True))
    op.add_column("videos", sa.Column("affiliate_comment_error", sa.String(), nullable=True))
    op.add_column("videos", sa.Column("affiliate_comment_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("videos", sa.Column("affiliate_comment_requested_at", sa.DateTime(), nullable=True))
    op.add_column("videos", sa.Column("affiliate_commented_at", sa.DateTime(), nullable=True))

    op.alter_column("facebook_pages", "affiliate_comment_enabled", server_default=None)
    op.alter_column("facebook_pages", "affiliate_comment_delay_seconds", server_default=None)
    op.alter_column("videos", "affiliate_comment_status", server_default=None)
    op.alter_column("videos", "affiliate_comment_attempts", server_default=None)


def downgrade() -> None:
    op.drop_column("videos", "affiliate_commented_at")
    op.drop_column("videos", "affiliate_comment_requested_at")
    op.drop_column("videos", "affiliate_comment_attempts")
    op.drop_column("videos", "affiliate_comment_error")
    op.drop_column("videos", "affiliate_comment_fb_id")
    op.drop_column("videos", "affiliate_comment_text")
    op.drop_column("videos", "affiliate_comment_status")
    op.drop_column("videos", "fb_permalink_url")
    op.drop_column("videos", "fb_video_id")

    op.drop_column("facebook_pages", "affiliate_comment_delay_seconds")
    op.drop_column("facebook_pages", "affiliate_link_url")
    op.drop_column("facebook_pages", "affiliate_comment_text")
    op.drop_column("facebook_pages", "affiliate_comment_enabled")

    bind = op.get_bind()
    affiliate_comment_status.drop(bind, checkfirst=True)
