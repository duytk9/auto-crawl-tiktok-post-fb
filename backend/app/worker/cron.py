import os
import socket
import traceback
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import utc_now
from app.models.models import AffiliateCommentStatus, Campaign, CampaignStatus, FacebookPage, Video, VideoStatus
from app.services.ai_generator import generate_caption
from app.services.fb_graph import upload_video_to_facebook
from app.services.campaign_jobs import queue_affiliate_comment_for_video
from app.services.observability import record_event, update_worker_heartbeat
from app.services.security import decrypt_secret
from app.worker.tasks import process_task_queue

scheduler = BackgroundScheduler()
WORKER_NAME = f"{settings.APP_ROLE}@{socket.gethostname()}"


def auto_post_job():
    db: Session = SessionLocal()
    update_worker_heartbeat(WORKER_NAME, app_role=settings.APP_ROLE, status="quét lịch đăng", db=db)
    try:
        now = utc_now()
        pages = db.query(FacebookPage).all()

        for page in pages:
            vid = (
                db.query(Video)
                .join(Campaign)
                .filter(
                    Campaign.target_page_id == page.page_id,
                    Campaign.status == CampaignStatus.active,
                    Video.status == VideoStatus.ready,
                    Video.publish_time <= now,
                )
                .order_by(Video.publish_time.asc())
                .first()
            )

            if not vid or not vid.campaign.auto_post:
                continue

            update_worker_heartbeat(
                WORKER_NAME,
                app_role=settings.APP_ROLE,
                status="đang đăng video",
                current_task_type="auto_post",
                current_task_id=str(vid.id),
                details={"page_id": page.page_id, "video_id": str(vid.id)},
                db=db,
            )

            try:
                access_token = decrypt_secret(page.long_lived_access_token)
            except ValueError as exc:
                vid.status = VideoStatus.failed
                vid.last_error = str(exc)
                vid.retry_count = (vid.retry_count or 0) + 1
                db.commit()
                continue

            if not access_token:
                vid.status = VideoStatus.failed
                vid.last_error = "Trang Facebook chưa có mã truy cập hợp lệ."
                vid.retry_count = (vid.retry_count or 0) + 1
                db.commit()
                continue

            if not vid.ai_caption:
                try:
                    vid.ai_caption = generate_caption(vid.original_caption)
                    db.commit()
                except Exception as exc:
                    vid.status = VideoStatus.failed
                    vid.last_error = f"Không thể tạo chú thích AI: {exc}"
                    vid.retry_count = (vid.retry_count or 0) + 1
                    db.commit()
                    record_event(
                        "video",
                        "error",
                        "Tạo chú thích AI trước khi đăng thất bại.",
                        db=db,
                        details={"video_id": str(vid.id), "page_id": page.page_id, "error": str(exc)},
                    )
                    continue

            res = upload_video_to_facebook(
                file_path=vid.file_path,
                caption=vid.ai_caption,
                page_id=page.page_id,
                access_token=access_token,
            )

            if "id" in res:
                vid.fb_video_id = res.get("video_id") or res["id"]
                vid.fb_post_id = res.get("post_id") or res["id"]
                vid.fb_permalink_url = res.get("permalink_url")
                vid.status = VideoStatus.posted
                vid.last_error = None
                affiliate_task = queue_affiliate_comment_for_video(db, vid, page)
                record_event(
                    "video",
                    "info",
                    "Đã đăng video thành công.",
                    db=db,
                    details={
                        "video_id": str(vid.id),
                        "page_id": page.page_id,
                        "fb_video_id": vid.fb_video_id,
                        "fb_post_id": vid.fb_post_id,
                        "affiliate_comment_status": vid.affiliate_comment_status.value
                        if isinstance(vid.affiliate_comment_status, AffiliateCommentStatus)
                        else str(vid.affiliate_comment_status),
                        "affiliate_task_id": affiliate_task.get("task_id") if affiliate_task else None,
                    },
                )
                if vid.file_path and os.path.exists(vid.file_path):
                    try:
                        os.remove(vid.file_path)
                    except Exception as exc:
                        record_event(
                            "video",
                            "warning",
                            "Không thể xóa tệp tạm sau khi đăng.",
                            db=db,
                            details={"video_id": str(vid.id), "file_path": vid.file_path, "error": str(exc)},
                        )
            else:
                vid.status = VideoStatus.failed
                vid.last_error = str(res.get("error", res))
                vid.retry_count = (vid.retry_count or 0) + 1
                record_event(
                    "video",
                    "error",
                    "Đăng video lên Facebook thất bại.",
                    db=db,
                    details={"video_id": str(vid.id), "page_id": page.page_id, "response": res},
                )

            db.commit()
    except Exception as exc:
        record_event(
            "worker",
            "error",
            "Tác vụ quét lịch đăng gặp lỗi.",
            db=db,
            details={"error": str(exc), "traceback": traceback.format_exc()},
        )
    finally:
        update_worker_heartbeat(WORKER_NAME, app_role=settings.APP_ROLE, status="idle", db=db)
        db.close()


def process_task_queue_job():
    processed = process_task_queue(WORKER_NAME)
    if processed:
        record_event(
            "queue",
            "info",
            "Đã xử lý xong một đợt tác vụ nền.",
            details={"worker_name": WORKER_NAME, "processed": processed},
        )


def heartbeat_job():
    update_worker_heartbeat(WORKER_NAME, app_role=settings.APP_ROLE, status="idle")


def start_scheduler():
    if not scheduler.get_job("auto_post_job"):
        scheduler.add_job(
            auto_post_job,
            "interval",
            id="auto_post_job",
            minutes=settings.SCHEDULER_INTERVAL_MINUTES,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    if not scheduler.get_job("process_task_queue_job"):
        scheduler.add_job(
            process_task_queue_job,
            "interval",
            id="process_task_queue_job",
            seconds=settings.TASK_QUEUE_POLL_SECONDS,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    if not scheduler.get_job("heartbeat_job"):
        scheduler.add_job(
            heartbeat_job,
            "interval",
            id="heartbeat_job",
            seconds=max(10, settings.TASK_QUEUE_POLL_SECONDS),
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    if not scheduler.running:
        scheduler.start()
