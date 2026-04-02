import enum
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.time import utc_now

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class CampaignStatus(str, enum.Enum):
    active = "active"
    paused = "paused"


class VideoStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    ready = "ready"
    posted = "posted"
    failed = "failed"


class AffiliateCommentStatus(str, enum.Enum):
    disabled = "disabled"
    queued = "queued"
    posted = "posted"
    operator_required = "operator_required"


class InteractionStatus(str, enum.Enum):
    pending = "pending"
    replied = "replied"
    failed = "failed"
    ignored = "ignored"


class ConversationStatus(str, enum.Enum):
    ai_active = "ai_active"
    operator_active = "operator_active"
    resolved = "resolved"


class TaskStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    source_url = Column(String)
    source_platform = Column(String, nullable=True, index=True)
    source_kind = Column(String, nullable=True)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.active)
    auto_post = Column(Boolean, default=False)
    target_page_id = Column(String, nullable=True)
    schedule_interval = Column(Integer, default=0)
    last_synced_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String, default="idle")
    last_sync_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    videos = relationship("Video", back_populates="campaign")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("campaign_id", "original_id", name="uq_videos_campaign_original"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(Uuid(as_uuid=True), ForeignKey("campaigns.id"))
    original_id = Column(String, index=True)
    source_platform = Column(String, nullable=True, index=True)
    source_kind = Column(String, nullable=True)
    source_video_url = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    original_caption = Column(String, nullable=True)
    ai_caption = Column(String, nullable=True)
    status = Column(Enum(VideoStatus), default=VideoStatus.pending)
    publish_time = Column(DateTime, nullable=True)
    fb_video_id = Column(String, nullable=True)
    fb_post_id = Column(String, nullable=True)
    fb_permalink_url = Column(String, nullable=True)
    affiliate_comment_status = Column(Enum(AffiliateCommentStatus), default=AffiliateCommentStatus.disabled, nullable=False)
    affiliate_comment_text = Column(String, nullable=True)
    affiliate_comment_fb_id = Column(String, nullable=True)
    affiliate_comment_error = Column(String, nullable=True)
    affiliate_comment_attempts = Column(Integer, default=0, nullable=False)
    affiliate_comment_requested_at = Column(DateTime, nullable=True)
    affiliate_commented_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    campaign = relationship("Campaign", back_populates="videos")


class FacebookPage(Base):
    __tablename__ = "facebook_pages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String, unique=True, index=True)
    page_name = Column(String)
    long_lived_access_token = Column(String)
    comment_auto_reply_enabled = Column(Boolean, default=True, nullable=False)
    comment_ai_prompt = Column(String, nullable=True)
    message_auto_reply_enabled = Column(Boolean, default=False, nullable=False)
    message_ai_prompt = Column(String, nullable=True)
    message_reply_schedule_enabled = Column(Boolean, default=False, nullable=False)
    message_reply_start_time = Column(String, default="08:00", nullable=False)
    message_reply_end_time = Column(String, default="22:00", nullable=False)
    message_reply_cooldown_minutes = Column(Integer, default=0, nullable=False)
    affiliate_comment_enabled = Column(Boolean, default=False, nullable=False)
    affiliate_comment_text = Column(String, nullable=True)
    affiliate_link_url = Column(String, nullable=True)
    affiliate_comment_delay_seconds = Column(Integer, default=60, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class InboxConversation(Base):
    __tablename__ = "inbox_conversations"
    __table_args__ = (
        UniqueConstraint("page_id", "sender_id", name="uq_inbox_conversations_page_sender"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String, ForeignKey("facebook_pages.page_id"), index=True)
    sender_id = Column(String, index=True, nullable=False)
    recipient_id = Column(String, nullable=True)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ai_active, nullable=False, index=True)
    conversation_summary = Column(String, nullable=True)
    current_intent = Column(String, nullable=True)
    customer_facts = Column(JSON_TYPE, nullable=True)
    needs_human_handoff = Column(Boolean, default=False, nullable=False)
    handoff_reason = Column(String, nullable=True)
    assigned_to_user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    internal_note = Column(String, nullable=True)
    latest_customer_message_id = Column(String, nullable=True)
    latest_reply_message_id = Column(String, nullable=True)
    last_customer_message_at = Column(DateTime, nullable=True)
    last_ai_reply_at = Column(DateTime, nullable=True)
    last_operator_reply_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class InteractionLog(Base):
    __tablename__ = "interactions_log"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String, ForeignKey("facebook_pages.page_id"))
    post_id = Column(String)
    comment_id = Column(String, unique=True)
    user_id = Column(String)
    user_message = Column(String)
    ai_reply = Column(String, nullable=True)
    status = Column(Enum(InteractionStatus), default=InteractionStatus.pending)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class InboxMessageLog(Base):
    __tablename__ = "inbox_message_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    page_id = Column(String, ForeignKey("facebook_pages.page_id"), index=True)
    conversation_id = Column(Uuid(as_uuid=True), ForeignKey("inbox_conversations.id"), nullable=True, index=True)
    facebook_message_id = Column(String, unique=True, index=True)
    sender_id = Column(String, index=True)
    recipient_id = Column(String, nullable=True)
    user_message = Column(String)
    ai_reply = Column(String, nullable=True)
    facebook_reply_message_id = Column(String, nullable=True)
    reply_source = Column(String, nullable=True)
    reply_author_user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    status = Column(Enum(InteractionStatus), default=InteractionStatus.pending)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class TaskQueue(Base):
    __tablename__ = "task_queue"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String, index=True)
    entity_type = Column(String, index=True, nullable=True)
    entity_id = Column(String, index=True, nullable=True)
    payload = Column(JSON_TYPE)
    status = Column(Enum(TaskStatus), default=TaskStatus.queued)
    priority = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(String, nullable=True)
    available_at = Column(DateTime, default=utc_now)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    display_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.admin, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_name = Column(String, unique=True, index=True)
    app_role = Column(String, nullable=False)
    hostname = Column(String, nullable=True)
    status = Column(String, default="idle", nullable=False)
    current_task_id = Column(String, nullable=True)
    current_task_type = Column(String, nullable=True)
    details = Column(JSON_TYPE, nullable=True)
    last_seen_at = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(String, index=True, nullable=False)
    level = Column(String, index=True, nullable=False)
    message = Column(String, nullable=False)
    details = Column(JSON_TYPE, nullable=True)
    actor_user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)


class RuntimeSetting(Base):
    __tablename__ = "runtime_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    is_secret = Column(Boolean, default=False, nullable=False)
    updated_by_user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
