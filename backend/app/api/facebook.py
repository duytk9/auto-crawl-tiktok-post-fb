from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.api.auth import require_admin, require_authenticated_user
from app.core.database import get_db
from app.models.models import Campaign, FacebookPage, InboxConversation, InboxMessageLog, InteractionLog, TaskQueue, User
from app.services.campaign_jobs import has_affiliate_comment_options
from app.services.observability import record_event
from app.services.security import decrypt_secret, encrypt_secret, is_secret_encrypted, mask_secret
from app.services.fb_graph import inspect_page_access, inspect_page_messenger_subscription, inspect_user_pages, subscribe_page_to_app

router = APIRouter(prefix="/facebook", tags=["Trang Facebook"])
PAGE_WEBHOOK_REQUIRED_FIELDS = ("messages", "feed")

class FacebookPageCreate(BaseModel):
    page_id: str
    page_name: str
    long_lived_access_token: str


class FacebookPageDiscoveryRequest(BaseModel):
    user_access_token: str


class FacebookPageBulkImportRequest(BaseModel):
    user_access_token: str
    page_ids: list[str] = Field(default_factory=list, min_length=1)


class FacebookPageBulkRefreshRequest(BaseModel):
    user_access_token: str
    page_ids: list[str] = Field(default_factory=list)


class FacebookAutomationUpdate(BaseModel):
    comment_auto_reply_enabled: bool
    comment_ai_prompt: str | None = None
    message_auto_reply_enabled: bool
    message_ai_prompt: str | None = None
    message_reply_schedule_enabled: bool = False
    message_reply_start_time: str = Field(default="08:00", pattern=r"^\d{2}:\d{2}$")
    message_reply_end_time: str = Field(default="22:00", pattern=r"^\d{2}:\d{2}$")
    message_reply_cooldown_minutes: int = Field(default=0, ge=0, le=1440)
    affiliate_comment_enabled: bool = False
    affiliate_comment_text: str | None = None
    affiliate_link_url: str | None = None
    affiliate_comment_delay_seconds: int = Field(default=60, ge=0, le=3600)


def _normalize_time_string(value: str, *, field_name: str) -> str:
    raw = (value or "").strip()
    try:
        hours, minutes = raw.split(":")
        hour_value = int(hours)
        minute_value = int(minutes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} phải theo định dạng HH:MM.") from exc

    if not (0 <= hour_value <= 23 and 0 <= minute_value <= 59):
        raise HTTPException(status_code=400, detail=f"{field_name} không hợp lệ.")

    return f"{hour_value:02d}:{minute_value:02d}"

def get_token_kind(token: str | None) -> str:
    if not token:
        return "missing"
    try:
        plain_token = decrypt_secret(token)
    except ValueError:
        return "invalid_encryption"
    if plain_token.startswith("http://") or plain_token.startswith("https://"):
        return "legacy_webhook"
    return "page_access_token"


def _validate_page_access_token(page_id: str, access_token: str) -> dict:
    inspection = inspect_page_access(page_id, access_token)
    if inspection.get("ok"):
        return inspection

    raise HTTPException(
        status_code=400,
        detail=inspection.get("message", "Không thể xác minh Page Access Token."),
    )


def serialize_page_config(page: FacebookPage) -> dict:
    raw_token = page.long_lived_access_token
    if raw_token and not is_secret_encrypted(raw_token):
        page.long_lived_access_token = encrypt_secret(raw_token)
        raw_token = page.long_lived_access_token

    try:
        decrypted = decrypt_secret(raw_token)
        token_kind = get_token_kind(raw_token)
        token_preview = mask_secret(decrypted)
    except ValueError:
        token_kind = "invalid_encryption"
        token_preview = None

    return {
        "page_id": page.page_id,
        "page_name": page.page_name,
        "has_token": bool(raw_token),
        "token_kind": token_kind,
        "token_preview": token_preview,
        "token_is_encrypted": bool(raw_token and is_secret_encrypted(raw_token)),
        "comment_auto_reply_enabled": page.comment_auto_reply_enabled is not False,
        "comment_ai_prompt": page.comment_ai_prompt or "",
        "message_auto_reply_enabled": bool(page.message_auto_reply_enabled),
        "message_ai_prompt": page.message_ai_prompt or "",
        "message_reply_schedule_enabled": bool(page.message_reply_schedule_enabled),
        "message_reply_start_time": page.message_reply_start_time or "08:00",
        "message_reply_end_time": page.message_reply_end_time or "22:00",
        "message_reply_cooldown_minutes": page.message_reply_cooldown_minutes or 0,
        "affiliate_comment_enabled": bool(page.affiliate_comment_enabled),
        "affiliate_comment_text": page.affiliate_comment_text or "",
        "affiliate_link_url": page.affiliate_link_url or "",
        "affiliate_comment_delay_seconds": page.affiliate_comment_delay_seconds or 60,
    }


def serialize_discovered_page(page_data: dict, *, existing_page_ids: set[str] | None = None) -> dict:
    existing_page_ids = existing_page_ids or set()
    page_access_token = (page_data.get("page_access_token") or "").strip()
    return {
        "page_id": page_data.get("page_id"),
        "page_name": page_data.get("page_name"),
        "page_link": page_data.get("page_link"),
        "category": page_data.get("category"),
        "tasks": page_data.get("tasks") or [],
        "has_page_access_token": bool(page_access_token),
        "token_preview": mask_secret(page_access_token) if page_access_token else None,
        "already_configured": page_data.get("page_id") in existing_page_ids,
    }


def _upsert_facebook_page(db: Session, *, page_id: str, page_name: str, access_token: str) -> FacebookPage:
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if page:
        page.page_name = page_name
        page.long_lived_access_token = encrypt_secret(access_token)
        return page

    page = FacebookPage(
        page_id=page_id,
        page_name=page_name,
        long_lived_access_token=encrypt_secret(access_token),
    )
    db.add(page)
    return page


def _load_discovered_pages_by_id(normalized_token: str) -> tuple[dict, dict[str, dict]]:
    discovery = inspect_user_pages(normalized_token)
    if not discovery.get("ok"):
        raise HTTPException(status_code=400, detail=discovery.get("message", "Không thể tải danh sách fanpage."))

    discovered_pages = {
        (page.get("page_id") or "").strip(): page
        for page in discovery.get("pages", [])
        if page.get("page_id")
    }
    return discovery, discovered_pages


def _delete_page_related_data(db: Session, page_id: str) -> dict:
    message_log_ids = [
        str(log_id)
        for (log_id,) in db.query(InboxMessageLog.id).filter(InboxMessageLog.page_id == page_id).all()
    ]
    interaction_log_ids = [
        str(log_id)
        for (log_id,) in db.query(InteractionLog.id).filter(InteractionLog.page_id == page_id).all()
    ]

    deleted_task_count = 0
    if message_log_ids:
        deleted_task_count += (
            db.query(TaskQueue)
            .filter(
                TaskQueue.entity_type == "inbox_message_log",
                TaskQueue.entity_id.in_(message_log_ids),
            )
            .delete(synchronize_session=False)
        )
    if interaction_log_ids:
        deleted_task_count += (
            db.query(TaskQueue)
            .filter(
                TaskQueue.entity_type == "interaction_log",
                TaskQueue.entity_id.in_(interaction_log_ids),
            )
            .delete(synchronize_session=False)
        )

    deleted_message_logs = (
        db.query(InboxMessageLog)
        .filter(InboxMessageLog.page_id == page_id)
        .delete(synchronize_session=False)
    )
    deleted_conversations = (
        db.query(InboxConversation)
        .filter(InboxConversation.page_id == page_id)
        .delete(synchronize_session=False)
    )
    deleted_interactions = (
        db.query(InteractionLog)
        .filter(InteractionLog.page_id == page_id)
        .delete(synchronize_session=False)
    )

    return {
        "deleted_message_logs": deleted_message_logs,
        "deleted_conversations": deleted_conversations,
        "deleted_interactions": deleted_interactions,
        "deleted_tasks": deleted_task_count,
    }

@router.post("/config")
def set_facebook_config(
    page_in: FacebookPageCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
):
    normalized_token = page_in.long_lived_access_token.strip()

    if get_token_kind(normalized_token) == "legacy_webhook":
        raise HTTPException(
            status_code=400,
            detail="Hãy nhập mã truy cập trang Facebook thật. Liên kết webhook cũ không còn dùng để đăng bài hoặc trả lời bình luận."
        )

    inspection = _validate_page_access_token(page_in.page_id, normalized_token)

    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_in.page_id).first()
    if page:
        page.page_name = page_in.page_name
        page.long_lived_access_token = encrypt_secret(normalized_token)
    else:
        page = FacebookPage(
            page_id=page_in.page_id,
            page_name=page_in.page_name,
            long_lived_access_token=encrypt_secret(normalized_token)
        )
        db.add(page)
    db.commit()
    record_event(
        "facebook",
        "info",
        "Đã lưu cấu hình trang Facebook.",
        db=db,
        details={
            "page_id": page_in.page_id,
            "page_name": page_in.page_name,
            "token_kind": inspection.get("token_kind"),
        },
    )
    return {
        "message": "Đã lưu Page Access Token thành công!",
        "page": serialize_page_config(page),
        "validation": inspection,
    }


@router.post("/config/discover-pages")
def discover_facebook_pages(
    payload: FacebookPageDiscoveryRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
):
    normalized_token = payload.user_access_token.strip()
    if not normalized_token:
        raise HTTPException(status_code=400, detail="Bạn cần nhập User Access Token để tải danh sách fanpage.")

    if normalized_token.startswith("http://") or normalized_token.startswith("https://"):
        raise HTTPException(status_code=400, detail="Liên kết webhook cũ không thể dùng để tải danh sách fanpage.")

    discovery, _ = _load_discovered_pages_by_id(normalized_token)

    existing_page_ids = {
        page_id
        for (page_id,) in db.query(FacebookPage.page_id).all()
    }
    pages = [
        serialize_discovered_page(page_data, existing_page_ids=existing_page_ids)
        for page_data in discovery.get("pages", [])
    ]

    return {
        "message": discovery.get("message") or f"Đã tải {len(pages)} fanpage.",
        "token_kind": discovery.get("token_kind"),
        "token_subject_id": discovery.get("token_subject_id"),
        "token_subject_name": discovery.get("token_subject_name"),
        "pages": pages,
    }


@router.post("/config/import-pages")
def import_facebook_pages(
    payload: FacebookPageBulkImportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
):
    normalized_token = payload.user_access_token.strip()
    if not normalized_token:
        raise HTTPException(status_code=400, detail="Bạn cần nhập User Access Token để import fanpage.")

    selected_page_ids = [page_id.strip() for page_id in payload.page_ids if page_id and page_id.strip()]
    if not selected_page_ids:
        raise HTTPException(status_code=400, detail="Bạn cần chọn ít nhất một fanpage để import.")

    discovery, discovered_pages = _load_discovered_pages_by_id(normalized_token)

    missing_page_ids = [page_id for page_id in selected_page_ids if page_id not in discovered_pages]
    if missing_page_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Một số fanpage không còn xuất hiện trong danh sách token hiện tại: {', '.join(missing_page_ids)}.",
        )

    imported_pages = []
    for page_id in selected_page_ids:
        page_data = discovered_pages[page_id]
        page_access_token = (page_data.get("page_access_token") or "").strip()
        if not page_access_token:
            raise HTTPException(
                status_code=400,
                detail=f"Fanpage {page_data.get('page_name') or page_id} chưa có Page Access Token trong phản hồi từ Facebook.",
            )

        inspection = _validate_page_access_token(page_id, page_access_token)
        page = _upsert_facebook_page(
            db,
            page_id=page_id,
            page_name=(page_data.get("page_name") or page_id).strip(),
            access_token=page_access_token,
        )
        imported_pages.append(
            {
                "page": serialize_page_config(page),
                "validation": inspection,
            }
        )

    db.commit()

    record_event(
        "facebook",
        "info",
        "Đã import hàng loạt fanpage từ User Access Token.",
        db=db,
        details={
            "count": len(imported_pages),
            "page_ids": selected_page_ids,
            "token_subject_id": discovery.get("token_subject_id"),
            "token_subject_name": discovery.get("token_subject_name"),
        },
    )

    return {
        "message": f"Đã import {len(imported_pages)} fanpage vào hệ thống.",
        "imported_pages": imported_pages,
        "token_subject_id": discovery.get("token_subject_id"),
        "token_subject_name": discovery.get("token_subject_name"),
    }


@router.post("/config/refresh-pages")
def refresh_facebook_pages(
    payload: FacebookPageBulkRefreshRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
):
    normalized_token = payload.user_access_token.strip()
    if not normalized_token:
        raise HTTPException(status_code=400, detail="Bạn cần nhập User Access Token để làm mới token fanpage.")

    discovery, discovered_pages = _load_discovered_pages_by_id(normalized_token)

    selected_page_ids = [page_id.strip() for page_id in payload.page_ids if page_id and page_id.strip()]
    configured_pages_query = db.query(FacebookPage)
    if selected_page_ids:
        configured_pages_query = configured_pages_query.filter(FacebookPage.page_id.in_(selected_page_ids))
    configured_pages = configured_pages_query.all()
    if not configured_pages:
        raise HTTPException(status_code=404, detail="Không có fanpage nào trong hệ thống để làm mới token.")

    refreshed_pages = []
    missing_page_ids = []
    for page in configured_pages:
        page_data = discovered_pages.get(page.page_id)
        if not page_data:
            missing_page_ids.append(page.page_id)
            continue

        page_access_token = (page_data.get("page_access_token") or "").strip()
        if not page_access_token:
            raise HTTPException(
                status_code=400,
                detail=f"Fanpage {page.page_name or page.page_id} chưa có Page Access Token trong phản hồi từ Facebook.",
            )

        inspection = _validate_page_access_token(page.page_id, page_access_token)
        page.page_name = (page_data.get("page_name") or page.page_name or page.page_id).strip()
        page.long_lived_access_token = encrypt_secret(page_access_token)
        refreshed_pages.append(
            {
                "page": serialize_page_config(page),
                "validation": inspection,
            }
        )

    if not refreshed_pages:
        missing_text = ", ".join(missing_page_ids) if missing_page_ids else "không có fanpage phù hợp"
        raise HTTPException(
            status_code=400,
            detail=f"Không thể làm mới token. Token hiện tại không trả về fanpage nào đã cấu hình trong hệ thống ({missing_text}).",
        )

    db.commit()

    record_event(
        "facebook",
        "info",
        "Đã làm mới Page Access Token cho các fanpage đã cấu hình.",
        db=db,
        details={
            "count": len(refreshed_pages),
            "page_ids": [item["page"]["page_id"] for item in refreshed_pages],
            "missing_page_ids": missing_page_ids,
            "token_subject_id": discovery.get("token_subject_id"),
            "token_subject_name": discovery.get("token_subject_name"),
        },
    )

    return {
        "message": f"Đã làm mới token cho {len(refreshed_pages)} fanpage.",
        "refreshed_pages": refreshed_pages,
        "skipped_page_ids": missing_page_ids,
        "token_subject_id": discovery.get("token_subject_id"),
        "token_subject_name": discovery.get("token_subject_name"),
    }

@router.get("/config")
def get_facebook_config(
    db: Session = Depends(get_db),
    _: User = Depends(require_authenticated_user),
):
    pages = db.query(FacebookPage).all()
    should_commit = False
    normalized_pages = []

    for page in pages:
        before_token = page.long_lived_access_token
        payload = serialize_page_config(page)
        if page.long_lived_access_token != before_token:
            should_commit = True
        normalized_pages.append(payload)

    if should_commit:
        db.commit()

    return normalized_pages


@router.delete("/config/{page_id}")
def delete_facebook_page(
    page_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy fanpage cần xóa.")

    linked_campaigns = (
        db.query(Campaign)
        .filter(Campaign.target_page_id == page_id)
        .order_by(Campaign.name.asc())
        .all()
    )
    if linked_campaigns:
        campaign_names = ", ".join(campaign.name or str(campaign.id) for campaign in linked_campaigns[:5])
        extra = "" if len(linked_campaigns) <= 5 else f" và {len(linked_campaigns) - 5} chiến dịch khác"
        raise HTTPException(
            status_code=400,
            detail=f"Fanpage này vẫn đang được dùng trong {len(linked_campaigns)} chiến dịch ({campaign_names}{extra}). Hãy đổi hoặc xóa chiến dịch trước khi xóa fanpage.",
        )

    cleanup_stats = _delete_page_related_data(db, page_id)
    page_name = page.page_name
    db.delete(page)
    db.commit()

    record_event(
        "facebook",
        "warning",
        "Đã xóa fanpage khỏi hệ thống.",
        db=db,
        actor_user_id=str(current_user.id),
        details={
            "page_id": page_id,
            "page_name": page_name,
            **cleanup_stats,
        },
    )

    return {
        "message": f"Đã xóa fanpage {page_name or page_id} khỏi hệ thống.",
        "page_id": page_id,
        "page_name": page_name,
        **cleanup_stats,
    }


@router.patch("/config/{page_id}/automation")
def update_facebook_automation(page_id: str, payload: FacebookAutomationUpdate, db: Session = Depends(get_db)):
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy fanpage cần cập nhật.")

    affiliate_comment_text = (payload.affiliate_comment_text or "").strip()
    affiliate_link_url = (payload.affiliate_link_url or "").strip()
    preview_page = FacebookPage(
        affiliate_comment_text=affiliate_comment_text or None,
        affiliate_link_url=affiliate_link_url or None,
    )
    if payload.affiliate_comment_enabled and not has_affiliate_comment_options(preview_page):
        raise HTTPException(
            status_code=400,
            detail="Khi bật comment affiliate, bạn cần nhập ít nhất một nội dung hoặc một link affiliate.",
        )

    page.comment_auto_reply_enabled = payload.comment_auto_reply_enabled
    page.comment_ai_prompt = (payload.comment_ai_prompt or "").strip() or None
    page.message_auto_reply_enabled = payload.message_auto_reply_enabled
    page.message_ai_prompt = (payload.message_ai_prompt or "").strip() or None
    page.message_reply_schedule_enabled = payload.message_reply_schedule_enabled
    page.message_reply_start_time = _normalize_time_string(payload.message_reply_start_time, field_name="Giờ bắt đầu")
    page.message_reply_end_time = _normalize_time_string(payload.message_reply_end_time, field_name="Giờ kết thúc")
    page.message_reply_cooldown_minutes = payload.message_reply_cooldown_minutes
    page.affiliate_comment_enabled = payload.affiliate_comment_enabled
    page.affiliate_comment_text = affiliate_comment_text or None
    page.affiliate_link_url = affiliate_link_url or None
    page.affiliate_comment_delay_seconds = payload.affiliate_comment_delay_seconds
    db.commit()
    db.refresh(page)

    record_event(
        "facebook",
        "info",
        "Đã cập nhật cấu hình AI theo fanpage.",
        db=db,
        details={
            "page_id": page.page_id,
            "comment_auto_reply_enabled": page.comment_auto_reply_enabled,
            "message_auto_reply_enabled": page.message_auto_reply_enabled,
            "message_reply_schedule_enabled": page.message_reply_schedule_enabled,
            "message_reply_start_time": page.message_reply_start_time,
            "message_reply_end_time": page.message_reply_end_time,
            "message_reply_cooldown_minutes": page.message_reply_cooldown_minutes,
            "affiliate_comment_enabled": page.affiliate_comment_enabled,
            "affiliate_comment_delay_seconds": page.affiliate_comment_delay_seconds,
        },
    )
    return {
        "message": f"Đã lưu cấu hình AI cho fanpage {page.page_name}.",
        "page": serialize_page_config(page),
    }


@router.get("/config/{page_id}/validate")
def validate_facebook_page(page_id: str, db: Session = Depends(get_db)):
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang Facebook trong hệ thống.")

    if not page.long_lived_access_token:
        raise HTTPException(status_code=400, detail="Trang Facebook này chưa có mã truy cập để kiểm tra.")

    token_kind = get_token_kind(page.long_lived_access_token)
    if token_kind != "page_access_token":
        raise HTTPException(status_code=400, detail="Mã truy cập hiện tại không phải mã truy cập trang Facebook hợp lệ.")

    try:
        access_token = decrypt_secret(page.long_lived_access_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = _validate_page_access_token(page.page_id, access_token)
    messenger_connection = inspect_page_messenger_subscription(
        page.page_id,
        access_token,
        required_fields=PAGE_WEBHOOK_REQUIRED_FIELDS,
    )
    record_event(
        "facebook",
        "info",
        "Đã xác minh mã truy cập trang Facebook.",
        db=db,
        details={
            "page_id": page.page_id,
            "page_name": page.page_name,
            "messenger_connected": messenger_connection.get("connected", False),
        },
    )
    return {
        **result,
        "messenger_connection": messenger_connection,
    }


@router.post("/config/{page_id}/subscribe-messages")
def subscribe_facebook_page_messages(page_id: str, db: Session = Depends(get_db)):
    page = db.query(FacebookPage).filter(FacebookPage.page_id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Không tìm thấy trang Facebook trong hệ thống.")

    if not page.long_lived_access_token:
        raise HTTPException(status_code=400, detail="Trang Facebook này chưa có mã truy cập để đăng ký.")

    try:
        access_token = decrypt_secret(page.long_lived_access_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    validation = _validate_page_access_token(page.page_id, access_token)
    subscription = subscribe_page_to_app(
        page.page_id,
        access_token,
        subscribed_fields=PAGE_WEBHOOK_REQUIRED_FIELDS,
    )
    if not subscription.get("ok"):
        raise HTTPException(status_code=400, detail=subscription.get("message", "Không thể đăng ký fanpage nhận tin nhắn."))

    messenger_connection = inspect_page_messenger_subscription(
        page.page_id,
        access_token,
        required_fields=PAGE_WEBHOOK_REQUIRED_FIELDS,
    )
    record_event(
        "facebook",
        "info",
        "Đã đăng ký fanpage nhận webhook tin nhắn.",
        db=db,
        details={
            "page_id": page.page_id,
            "page_name": page.page_name,
            "messenger_connected": messenger_connection.get("connected", False),
            "required_fields": messenger_connection.get("required_fields", []),
        },
    )
    return {
        "message": "Đã đăng ký fanpage nhận webhook messages và feed cho app hiện tại.",
        "page": serialize_page_config(page),
        "validation": validation,
        "messenger_connection": messenger_connection,
    }
