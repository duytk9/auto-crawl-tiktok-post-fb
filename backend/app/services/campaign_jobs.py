from __future__ import annotations

from datetime import datetime, timedelta
import os
import random
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.time import utc_now
from app.models.models import (
    AffiliateCommentStatus,
    Campaign,
    CampaignStatus,
    ConversationStatus,
    FacebookPage,
    InboxConversation,
    InboxMessageLog,
    InteractionLog,
    InteractionStatus,
    Video,
    VideoStatus,
)
from app.services.ai_generator import generate_message_reply_with_context, generate_reply
from app.services.fb_graph import publish_affiliate_comment, reply_to_comment, send_page_message
from app.services.inbox_memory import (
    apply_conversation_ai_state,
    get_or_create_inbox_conversation,
    normalize_customer_facts,
    serialize_recent_turns,
    touch_conversation_with_customer_message,
)
from app.services.observability import record_event
from app.services.security import decrypt_secret
from app.services.source_resolver import SourceResolutionError, resolve_content_source
from app.services.task_queue import TASK_TYPE_AFFILIATE_COMMENT, enqueue_task
from app.services.ytdlp_crawler import download_video, extract_source_entries


def parse_uuid_or_none(raw_id: str):
    try:
        return uuid.UUID(raw_id)
    except ValueError:
        return None


def safe_remove_file(path: str | None):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def mark_video_failed(video: Video, message: str):
    video.status = VideoStatus.failed
    video.last_error = message[:1000]
    video.retry_count = (video.retry_count or 0) + 1


def parse_affiliate_lines(raw_value: str | None) -> list[str]:
    return [line.strip() for line in (raw_value or "").splitlines() if line.strip()]


def has_affiliate_comment_options(page: FacebookPage) -> bool:
    return bool(parse_affiliate_lines(page.affiliate_comment_text) or parse_affiliate_lines(page.affiliate_link_url))


def build_affiliate_comment_text(page: FacebookPage, *, chooser=random.choice) -> str | None:
    contents = parse_affiliate_lines(page.affiliate_comment_text)
    links = parse_affiliate_lines(page.affiliate_link_url)
    content = chooser(contents) if contents else None
    link = chooser(links) if links else None
    parts = [part for part in [content, link] if part]
    if not parts:
        return None
    return "\n".join(parts)


def queue_affiliate_comment_for_video(db: Session, video: Video, page: FacebookPage) -> dict | None:
    affiliate_text = build_affiliate_comment_text(page)
    if not page.affiliate_comment_enabled or not affiliate_text:
        video.affiliate_comment_status = AffiliateCommentStatus.disabled
        video.affiliate_comment_text = affiliate_text
        video.affiliate_comment_error = None
        video.affiliate_comment_fb_id = None
        video.affiliate_comment_requested_at = None
        video.affiliate_commented_at = None
        return None

    available_at = utc_now() + timedelta(seconds=max(0, page.affiliate_comment_delay_seconds or 60))
    video.affiliate_comment_status = AffiliateCommentStatus.queued
    video.affiliate_comment_text = affiliate_text
    video.affiliate_comment_error = None
    video.affiliate_comment_fb_id = None
    video.affiliate_comment_requested_at = available_at
    task = enqueue_task(
        db,
        task_type=TASK_TYPE_AFFILIATE_COMMENT,
        entity_type="video",
        entity_id=str(video.id),
        payload={"video_id": str(video.id)},
        priority=10,
        max_attempts=3,
        available_at=available_at,
        dedupe_open_task=True,
    )
    return {"task_id": str(task.id), "available_at": available_at.isoformat()}


def set_campaign_sync_state(campaign: Campaign, status: str, error: str | None = None, finished_at: datetime | None = None):
    campaign.last_sync_status = status
    campaign.last_sync_error = error[:1000] if error else None
    if finished_at:
        campaign.last_synced_at = finished_at


def ensure_campaign_source_details(campaign: Campaign):
    resolved = resolve_content_source(campaign.source_url)
    changed = False
    if campaign.source_url != resolved.normalized_url:
        campaign.source_url = resolved.normalized_url
        changed = True
    if campaign.source_platform != resolved.platform.value:
        campaign.source_platform = resolved.platform.value
        changed = True
    if campaign.source_kind != resolved.source_kind.value:
        campaign.source_kind = resolved.source_kind.value
        changed = True
    return resolved, changed


def build_download_prefix(source_platform: str | None) -> str:
    if source_platform == "youtube":
        return "youtube_short"
    if source_platform == "tiktok":
        return "tiktok"
    return "video"


def build_source_page_publish_time(db: Session, page_id: str | None, schedule_interval: int):
    now = utc_now()
    start_time = now

    if page_id and schedule_interval > 0:
        last_publish = (
            db.query(func.max(Video.publish_time))
            .join(Campaign)
            .filter(
                Campaign.target_page_id == page_id,
                Campaign.status == CampaignStatus.active,
                Video.status == VideoStatus.ready,
            )
            .scalar()
        )
        if last_publish and last_publish > now:
            start_time = last_publish + timedelta(minutes=schedule_interval)
    return start_time


def retry_video_download(video_id: str) -> dict:
    db: Session = SessionLocal()
    video = None
    try:
        video_uuid = parse_uuid_or_none(video_id)
        if not video_uuid:
            raise ValueError("Mã video không hợp lệ.")

        video = db.query(Video).filter(Video.id == video_uuid).first()
        if not video:
            raise ValueError("Không tìm thấy video cần thử lại.")

        out_path, _ = download_video(video.source_video_url, build_download_prefix(video.source_platform))
        if out_path:
            safe_remove_file(video.file_path)
            video.file_path = out_path
            video.status = VideoStatus.ready
            video.publish_time = utc_now()
            video.fb_video_id = None
            video.fb_post_id = None
            video.fb_permalink_url = None
            video.affiliate_comment_status = AffiliateCommentStatus.disabled
            video.affiliate_comment_text = None
            video.affiliate_comment_fb_id = None
            video.affiliate_comment_error = None
            video.affiliate_comment_attempts = 0
            video.affiliate_comment_requested_at = None
            video.affiliate_commented_at = None
            video.last_error = None
            db.commit()
            record_event(
                "video",
                "info",
                "Đã tải lại video thành công.",
                db=db,
                details={"video_id": str(video.id), "original_id": video.original_id},
            )
            return {"ok": True, "video_id": str(video.id)}

        mark_video_failed(video, "Tải lại video thất bại.")
        db.commit()
        record_event(
            "video",
            "warning",
            "Tải lại video không thành công.",
            db=db,
            details={"video_id": str(video.id), "original_id": video.original_id},
        )
        return {"ok": False, "video_id": str(video.id)}
    except Exception as exc:
        if video:
            mark_video_failed(video, str(exc))
            db.commit()
        record_event(
            "video",
            "error",
            "Tiến trình thử tải lại video gặp lỗi.",
            db=db,
            details={"video_id": video_id, "error": str(exc)},
        )
        raise
    finally:
        db.close()


def sync_campaign_content(
    campaign_id: str,
    source_url: str,
    allow_paused: bool = False,
    source_platform: str | None = None,
    source_kind: str | None = None,
) -> dict:
    db: Session = SessionLocal()
    try:
        campaign_uuid = parse_uuid_or_none(campaign_id)
        if not campaign_uuid:
            raise ValueError("Mã chiến dịch không hợp lệ.")

        campaign = db.query(Campaign).filter(Campaign.id == campaign_uuid).first()
        if not campaign:
            raise ValueError("Không tìm thấy chiến dịch cần đồng bộ.")
        try:
            resolved_source, changed = ensure_campaign_source_details(campaign)
        except SourceResolutionError as exc:
            raise ValueError(str(exc)) from exc

        if not campaign.source_platform and source_platform:
            campaign.source_platform = source_platform
            changed = True
        if not campaign.source_kind and source_kind:
            campaign.source_kind = source_kind
            changed = True
        if not campaign.source_url and source_url:
            campaign.source_url = source_url
            changed = True
        db.commit()
        db.refresh(campaign)

        set_campaign_sync_state(campaign, "syncing")
        db.commit()
        record_event(
            "campaign",
            "info",
            "Bắt đầu đồng bộ chiến dịch.",
            db=db,
            details={"campaign_id": campaign_id, "campaign_name": campaign.name},
        )

        entries = list(
            reversed(
                extract_source_entries(
                    campaign.source_url,
                    campaign.source_platform or resolved_source.platform.value,
                    campaign.source_kind or resolved_source.source_kind.value,
                )
            )
        )
        if not entries:
            raise ValueError("Nguồn nội dung không trả về video hợp lệ để đưa vào hàng chờ.")

        start_time = build_source_page_publish_time(
            db,
            campaign.target_page_id,
            campaign.schedule_interval or 0,
        )
        added_count = 0
        interrupted_reason = None

        for entry in entries:
            db.expire_all()
            campaign = db.query(Campaign).filter(Campaign.id == campaign_uuid).first()
            if not campaign:
                interrupted_reason = "Chiến dịch đã bị xóa trong lúc đồng bộ."
                break
            if campaign.status != CampaignStatus.active and not allow_paused:
                interrupted_reason = "Chiến dịch đã bị tạm dừng trong lúc đồng bộ."
                break

            video_url = entry.source_video_url
            original_id = entry.original_id
            existing_vid = (
                db.query(Video)
                .filter(Video.campaign_id == campaign_uuid, Video.original_id == original_id)
                .first()
            )
            if existing_vid:
                continue

            publish_time = start_time + timedelta(minutes=added_count * (campaign.schedule_interval or 0))

            db_video = Video(
                campaign_id=campaign_uuid,
                original_id=original_id,
                source_platform=entry.source_platform,
                source_kind=entry.source_kind,
                source_video_url=video_url,
                original_caption=entry.original_caption,
                status=VideoStatus.downloading,
                publish_time=publish_time,
            )
            db.add(db_video)
            db.commit()
            db.refresh(db_video)
            added_count += 1

            out_path, _ = download_video(video_url, build_download_prefix(entry.source_platform))
            if out_path:
                db_video.file_path = out_path
                db_video.status = VideoStatus.ready
                db_video.last_error = None
                db_video.fb_video_id = None
                db_video.fb_post_id = None
                db_video.fb_permalink_url = None
                db_video.affiliate_comment_status = AffiliateCommentStatus.disabled
                db_video.affiliate_comment_text = None
                db_video.affiliate_comment_fb_id = None
                db_video.affiliate_comment_error = None
                db_video.affiliate_comment_attempts = 0
                db_video.affiliate_comment_requested_at = None
                db_video.affiliate_commented_at = None
            else:
                mark_video_failed(db_video, "Tải video thất bại.")
            db.commit()

        campaign = db.query(Campaign).filter(Campaign.id == campaign_uuid).first()
        if campaign:
            if interrupted_reason:
                set_campaign_sync_state(campaign, "failed", interrupted_reason, utc_now())
                record_event(
                    "campaign",
                    "warning",
                    "Đồng bộ chiến dịch bị dừng giữa chừng.",
                    db=db,
                    details={"campaign_id": campaign_id, "reason": interrupted_reason},
                )
            else:
                set_campaign_sync_state(campaign, "completed", None, utc_now())
                record_event(
                    "campaign",
                    "info",
                    "Đồng bộ chiến dịch hoàn tất.",
                    db=db,
                    details={"campaign_id": campaign_id, "videos_added": added_count},
                )
            db.commit()

        return {"ok": interrupted_reason is None, "campaign_id": campaign_id, "videos_added": added_count}
    except Exception as exc:
        campaign_uuid = parse_uuid_or_none(campaign_id)
        if campaign_uuid:
            campaign = db.query(Campaign).filter(Campaign.id == campaign_uuid).first()
            if campaign:
                set_campaign_sync_state(campaign, "failed", str(exc), utc_now())
                db.commit()
        record_event(
            "campaign",
            "error",
            "Tiến trình đồng bộ chiến dịch gặp lỗi.",
            db=db,
            details={"campaign_id": campaign_id, "error": str(exc)},
        )
        raise
    finally:
        db.close()


def reply_to_comment_job(interaction_log_id: str) -> dict:
    db: Session = SessionLocal()
    try:
        log_uuid = parse_uuid_or_none(interaction_log_id)
        if not log_uuid:
            raise ValueError("Mã nhật ký bình luận không hợp lệ.")

        log = db.query(InteractionLog).filter(InteractionLog.id == log_uuid).first()
        if not log:
            raise ValueError("Không tìm thấy bình luận cần phản hồi.")

        page_config = db.query(FacebookPage).filter(FacebookPage.page_id == log.page_id).first()
        if not page_config or not page_config.long_lived_access_token:
            log.status = InteractionStatus.failed
            log.ai_reply = "Trang Facebook chưa có mã truy cập hợp lệ."
            db.commit()
            return {"ok": False, "log_id": interaction_log_id}

        if page_config.comment_auto_reply_enabled is False:
            log.status = InteractionStatus.ignored
            log.ai_reply = "Tự động phản hồi bình luận đang tắt cho fanpage này."
            db.commit()
            return {"ok": False, "log_id": interaction_log_id}

        access_token = decrypt_secret(page_config.long_lived_access_token)
        ai_reply = generate_reply(
            log.user_message,
            channel="comment",
            prompt_override=page_config.comment_ai_prompt,
        )
        log.ai_reply = ai_reply

        res = reply_to_comment(log.comment_id, ai_reply, access_token)
        if res and "id" in res:
            log.status = InteractionStatus.replied
            record_event(
                "webhook",
                "info",
                "Đã phản hồi bình luận thành công.",
                db=db,
                details={"comment_id": log.comment_id, "page_id": log.page_id},
            )
        else:
            log.status = InteractionStatus.failed
            record_event(
                "webhook",
                "warning",
                "Phản hồi bình luận không thành công.",
                db=db,
                details={"comment_id": log.comment_id, "page_id": log.page_id, "response": res},
            )

        db.commit()
        return {"ok": log.status == InteractionStatus.replied, "log_id": interaction_log_id}
    except Exception as exc:
        record_event(
            "webhook",
            "error",
            "Tiến trình phản hồi bình luận gặp lỗi.",
            db=db,
            details={"log_id": interaction_log_id, "error": str(exc)},
        )
        raise
    finally:
        db.close()


def reply_to_message_job(message_log_id: str) -> dict:
    db: Session = SessionLocal()
    try:
        log_uuid = parse_uuid_or_none(message_log_id)
        if not log_uuid:
            raise ValueError("Mã nhật ký inbox không hợp lệ.")

        log = db.query(InboxMessageLog).filter(InboxMessageLog.id == log_uuid).first()
        if not log:
            raise ValueError("Không tìm thấy tin nhắn inbox cần phản hồi.")

        conversation = None
        if log.conversation_id:
            conversation = db.query(InboxConversation).filter(InboxConversation.id == log.conversation_id).first()
        if not conversation:
            conversation = get_or_create_inbox_conversation(
                db,
                page_id=log.page_id,
                sender_id=log.sender_id,
                recipient_id=log.recipient_id,
            )
            log.conversation_id = conversation.id
            db.commit()
            db.refresh(log)

        if conversation.status != ConversationStatus.ai_active or conversation.needs_human_handoff:
            log.status = InteractionStatus.ignored
            log.ai_reply = "Cuộc trò chuyện này đang được chuyển cho nhân viên hỗ trợ."
            log.last_error = None
            db.commit()
            return {"ok": False, "ignored": True, "log_id": message_log_id}

        page_config = db.query(FacebookPage).filter(FacebookPage.page_id == log.page_id).first()
        if not page_config or not page_config.long_lived_access_token:
            log.status = InteractionStatus.failed
            log.ai_reply = "Trang Facebook chưa có mã truy cập hợp lệ."
            log.last_error = "Thiếu Page Access Token."
            db.commit()
            return {"ok": False, "log_id": message_log_id}

        if not page_config.message_auto_reply_enabled:
            log.status = InteractionStatus.ignored
            log.ai_reply = "Tự động phản hồi inbox đang tắt cho fanpage này."
            log.last_error = None
            db.commit()
            return {"ok": False, "ignored": True, "log_id": message_log_id}

        access_token = decrypt_secret(page_config.long_lived_access_token)
        recent_turns = serialize_recent_turns(
            db,
            conversation_id=conversation.id,
            page_id=log.page_id,
            sender_id=log.sender_id,
            exclude_log_id=log.id,
        )
        ai_payload = generate_message_reply_with_context(
            log.user_message,
            prompt_override=page_config.message_ai_prompt,
            conversation_summary=conversation.conversation_summary,
            recent_turns=recent_turns,
            customer_facts=normalize_customer_facts(conversation.customer_facts),
        )
        ai_reply = ai_payload["reply"]
        log.ai_reply = ai_reply
        touch_conversation_with_customer_message(
            conversation,
            message_id=log.facebook_message_id,
            recipient_id=log.recipient_id,
            message_time=log.created_at or utc_now(),
        )
        apply_conversation_ai_state(
            conversation,
            summary=ai_payload.get("summary"),
            intent=ai_payload.get("intent"),
            customer_facts=ai_payload.get("customer_facts"),
            handoff=bool(ai_payload.get("handoff")),
            handoff_reason=ai_payload.get("handoff_reason"),
        )
        db.commit()

        res = send_page_message(log.sender_id, ai_reply, access_token)
        if res and ("message_id" in res or "recipient_id" in res):
            log.status = InteractionStatus.replied
            log.facebook_reply_message_id = res.get("message_id")
            log.reply_source = "ai"
            log.last_error = None
            conversation.latest_reply_message_id = log.facebook_reply_message_id
            conversation.last_ai_reply_at = utc_now()
            record_event(
                "webhook",
                "info",
                "Đã phản hồi tin nhắn inbox thành công.",
                db=db,
                details={"page_id": log.page_id, "sender_id": log.sender_id, "message_id": log.facebook_message_id},
            )
        else:
            log.status = InteractionStatus.failed
            log.last_error = str(res or "Facebook không trả về kết quả hợp lệ.")
            record_event(
                "webhook",
                "warning",
                "Phản hồi tin nhắn inbox không thành công.",
                db=db,
                details={
                    "page_id": log.page_id,
                    "sender_id": log.sender_id,
                    "message_id": log.facebook_message_id,
                    "conversation_id": str(conversation.id),
                    "handoff": conversation.needs_human_handoff,
                    "response": res,
                },
            )

        db.commit()
        return {"ok": log.status == InteractionStatus.replied, "log_id": message_log_id}
    except Exception as exc:
        record_event(
            "webhook",
            "error",
            "Tiến trình phản hồi tin nhắn inbox gặp lỗi.",
            db=db,
            details={"log_id": message_log_id, "error": str(exc)},
        )
        raise
    finally:
        db.close()


def post_affiliate_comment_job(video_id: str, *, attempt_number: int = 1, max_attempts: int = 3) -> dict:
    db: Session = SessionLocal()
    try:
        video_uuid = parse_uuid_or_none(video_id)
        if not video_uuid:
            raise ValueError("Mã video không hợp lệ.")

        video = db.query(Video).filter(Video.id == video_uuid).first()
        if not video:
            raise ValueError("Không tìm thấy video cần comment affiliate.")

        if video.status != VideoStatus.posted:
            raise ValueError("Video chưa ở trạng thái đã đăng nên chưa thể comment affiliate.")

        if video.affiliate_comment_status == AffiliateCommentStatus.posted and video.affiliate_comment_fb_id:
            return {"ok": True, "skipped": True, "reason": "already_commented", "video_id": video_id}

        if not video.campaign or not video.campaign.target_page_id:
            raise ValueError("Video chưa gắn với fanpage đích.")

        page = db.query(FacebookPage).filter(FacebookPage.page_id == video.campaign.target_page_id).first()
        if not page or not page.long_lived_access_token:
            raise ValueError("Fanpage chưa có token hợp lệ để comment affiliate.")

        access_token = decrypt_secret(page.long_lived_access_token)
        affiliate_text = (video.affiliate_comment_text or "").strip() or build_affiliate_comment_text(page)
        if not affiliate_text:
            video.affiliate_comment_status = AffiliateCommentStatus.disabled
            video.affiliate_comment_error = None
            db.commit()
            return {"ok": True, "skipped": True, "reason": "affiliate_disabled", "video_id": video_id}

        video.affiliate_comment_attempts = max(video.affiliate_comment_attempts or 0, attempt_number)
        result = publish_affiliate_comment(
            video_id=video.fb_video_id or video.fb_post_id,
            post_id=video.fb_post_id,
            message=affiliate_text,
            access_token=access_token,
        )
        if result and result.get("comment_id"):
            video.fb_post_id = result.get("post_id") or video.fb_post_id
            video.fb_permalink_url = result.get("permalink_url") or video.fb_permalink_url
            video.affiliate_comment_status = AffiliateCommentStatus.posted
            video.affiliate_comment_fb_id = result.get("comment_id")
            video.affiliate_comment_error = None
            video.affiliate_commented_at = utc_now()
            db.commit()
            record_event(
                "affiliate_comment",
                "info",
                "Đã comment affiliate thành công sau khi đăng video.",
                db=db,
                details={
                    "video_id": str(video.id),
                    "campaign_id": str(video.campaign_id),
                    "page_id": page.page_id,
                    "comment_id": video.affiliate_comment_fb_id,
                },
            )
            return {"ok": True, "video_id": video_id, "comment_id": video.affiliate_comment_fb_id}

        error_message = str((result or {}).get("error") or "Không thể comment affiliate lên bài đăng.")
        video.affiliate_comment_error = error_message[:1000]
        if attempt_number >= max_attempts:
            video.affiliate_comment_status = AffiliateCommentStatus.operator_required
            db.commit()
            record_event(
                "affiliate_comment",
                "warning",
                "Comment affiliate thất bại nhiều lần, cần operator xử lý.",
                db=db,
                details={
                    "video_id": str(video.id),
                    "campaign_id": str(video.campaign_id),
                    "page_id": page.page_id,
                    "error": error_message,
                },
            )
            return {
                "ok": False,
                "operator_required": True,
                "video_id": video_id,
                "error": error_message,
            }

        video.affiliate_comment_status = AffiliateCommentStatus.queued
        db.commit()
        raise RuntimeError(error_message)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
