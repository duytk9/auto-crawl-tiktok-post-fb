import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, Uuid

from app.core.database import Base
from app.core.time import utc_now
from app.models.common import JSON_TYPE


class InteractionStatus(str, enum.Enum):
    pending = "pending"
    replied = "replied"
    failed = "failed"
    ignored = "ignored"


class ConversationStatus(str, enum.Enum):
    ai_active = "ai_active"
    operator_active = "operator_active"
    resolved = "resolved"


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
