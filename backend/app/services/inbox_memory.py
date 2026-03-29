from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utc_now
from app.models.models import ConversationStatus, InboxConversation, InboxMessageLog, InteractionStatus


def get_or_create_inbox_conversation(
    db: Session,
    *,
    page_id: str,
    sender_id: str,
    recipient_id: str | None = None,
) -> InboxConversation:
    conversation = (
        db.query(InboxConversation)
        .filter(
            InboxConversation.page_id == page_id,
            InboxConversation.sender_id == sender_id,
        )
        .first()
    )
    if conversation:
        if recipient_id and conversation.recipient_id != recipient_id:
            conversation.recipient_id = recipient_id
            db.commit()
            db.refresh(conversation)
        return conversation

    conversation = InboxConversation(
        page_id=page_id,
        sender_id=sender_id,
        recipient_id=recipient_id,
        customer_facts={},
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def normalize_customer_facts(raw_value: Any) -> dict[str, str]:
    if not isinstance(raw_value, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in raw_value.items():
        key_text = str(key or "").strip()
        if not key_text:
            continue
        value_text = str(value or "").strip()
        if not value_text:
            continue
        normalized[key_text[:60]] = value_text[:200]
        if len(normalized) >= settings.INBOX_FACTS_MAX_ITEMS:
            break
    return normalized


def truncate_summary(summary: str | None) -> str | None:
    text = (summary or "").strip()
    if not text:
        return None
    return text[: settings.INBOX_SUMMARY_MAX_CHARS]


def serialize_recent_turns(
    db: Session,
    *,
    conversation_id: uuid.UUID | None = None,
    page_id: str,
    sender_id: str,
    exclude_log_id: uuid.UUID | None = None,
    limit_logs: int | None = None,
) -> list[dict[str, str]]:
    query = db.query(InboxMessageLog)
    if conversation_id:
        query = query.filter(InboxMessageLog.conversation_id == conversation_id)
    else:
        query = query.filter(
            InboxMessageLog.page_id == page_id,
            InboxMessageLog.sender_id == sender_id,
        )

    if exclude_log_id:
        query = query.filter(InboxMessageLog.id != exclude_log_id)

    logs = (
        query.order_by(InboxMessageLog.created_at.desc())
        .limit(limit_logs or settings.INBOX_CONTEXT_LOG_LIMIT)
        .all()
    )

    turns: list[dict[str, str]] = []
    for log in reversed(logs):
        customer_text = (log.user_message or "").strip()
        if customer_text:
            turns.append({"role": "customer", "content": customer_text})

        if log.status == InteractionStatus.replied:
            reply_text = (log.ai_reply or "").strip()
            if reply_text:
                turns.append({"role": "assistant", "content": reply_text})

    return turns


def touch_conversation_with_customer_message(
    conversation: InboxConversation,
    *,
    message_id: str | None,
    recipient_id: str | None,
    message_time=None,
) -> None:
    if conversation.status == ConversationStatus.resolved:
        conversation.status = ConversationStatus.ai_active
        conversation.needs_human_handoff = False
        conversation.handoff_reason = None
        conversation.assigned_to_user_id = None
        conversation.resolved_at = None
    conversation.latest_customer_message_id = message_id or conversation.latest_customer_message_id
    conversation.recipient_id = recipient_id or conversation.recipient_id
    conversation.last_customer_message_at = message_time or utc_now()


def apply_conversation_ai_state(
    conversation: InboxConversation,
    *,
    summary: str | None,
    intent: str | None,
    customer_facts: dict[str, Any] | None,
    handoff: bool,
    handoff_reason: str | None,
) -> None:
    conversation.conversation_summary = truncate_summary(summary) or conversation.conversation_summary
    conversation.current_intent = (intent or "").strip()[:80] or None
    if customer_facts is not None:
        conversation.customer_facts = normalize_customer_facts(customer_facts)
    conversation.needs_human_handoff = bool(handoff)
    conversation.handoff_reason = (handoff_reason or "").strip()[:300] or None
    if handoff:
        conversation.status = ConversationStatus.operator_active
        conversation.resolved_at = None
    elif conversation.status != ConversationStatus.resolved:
        conversation.status = ConversationStatus.ai_active


def _serialize_assigned_user(assigned_user: Any) -> dict[str, Any] | None:
    if not assigned_user:
        return None
    return {
        "id": str(assigned_user.id),
        "username": assigned_user.username,
        "display_name": assigned_user.display_name or assigned_user.username,
        "role": assigned_user.role.value if hasattr(assigned_user.role, "value") else assigned_user.role,
    }


def serialize_conversation(conversation: InboxConversation | None, assigned_user: Any | None = None) -> dict[str, Any] | None:
    if not conversation:
        return None

    facebook_thread_url = None
    if conversation.page_id and conversation.sender_id:
        page_id = quote(conversation.page_id, safe="")
        sender_id = quote(conversation.sender_id, safe="")
        facebook_thread_url = (
            "https://business.facebook.com/latest/inbox/all"
            f"?asset_id={page_id}&selected_item_id={sender_id}&thread_type=FB_MESSAGE&mailbox_id={page_id}"
        )

    return {
        "id": str(conversation.id),
        "page_id": conversation.page_id,
        "sender_id": conversation.sender_id,
        "recipient_id": conversation.recipient_id,
        "status": conversation.status.value if hasattr(conversation.status, "value") else conversation.status,
        "conversation_summary": conversation.conversation_summary or "",
        "current_intent": conversation.current_intent or "",
        "customer_facts": normalize_customer_facts(conversation.customer_facts),
        "needs_human_handoff": bool(conversation.needs_human_handoff),
        "handoff_reason": conversation.handoff_reason or "",
        "assigned_to_user_id": str(conversation.assigned_to_user_id) if conversation.assigned_to_user_id else None,
        "assigned_user": _serialize_assigned_user(assigned_user),
        "internal_note": conversation.internal_note or "",
        "facebook_thread_url": facebook_thread_url,
        "latest_customer_message_id": conversation.latest_customer_message_id,
        "latest_reply_message_id": conversation.latest_reply_message_id,
        "last_customer_message_at": conversation.last_customer_message_at.isoformat()
        if conversation.last_customer_message_at
        else None,
        "last_ai_reply_at": conversation.last_ai_reply_at.isoformat() if conversation.last_ai_reply_at else None,
        "last_operator_reply_at": conversation.last_operator_reply_at.isoformat()
        if conversation.last_operator_reply_at
        else None,
        "resolved_at": conversation.resolved_at.isoformat() if conversation.resolved_at else None,
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
    }
