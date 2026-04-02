from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.campaign_jobs import (
    post_affiliate_comment_job,
    reply_to_comment_job,
    reply_to_message_job,
    retry_video_download,
    sync_campaign_content,
)
from app.services.observability import record_event, update_worker_heartbeat
from app.services.task_queue import (
    TASK_TYPE_AFFILIATE_COMMENT,
    TASK_TYPE_CAMPAIGN_SYNC,
    TASK_TYPE_COMMENT_REPLY,
    TASK_TYPE_MESSAGE_REPLY,
    TASK_TYPE_VIDEO_RETRY,
    claim_next_task,
    complete_task,
    fail_task,
)


def _run_task(task) -> dict:
    payload = task.payload or {}
    if task.task_type == TASK_TYPE_CAMPAIGN_SYNC:
        return sync_campaign_content(
            payload.get("campaign_id", task.entity_id or ""),
            payload.get("source_url", ""),
            bool(payload.get("allow_paused")),
            payload.get("source_platform"),
            payload.get("source_kind"),
        )
    if task.task_type == TASK_TYPE_VIDEO_RETRY:
        return retry_video_download(payload.get("video_id", task.entity_id or ""))
    if task.task_type == TASK_TYPE_AFFILIATE_COMMENT:
        return post_affiliate_comment_job(
            payload.get("video_id", task.entity_id or ""),
            attempt_number=task.attempts or 1,
            max_attempts=task.max_attempts or 1,
        )
    if task.task_type == TASK_TYPE_COMMENT_REPLY:
        return reply_to_comment_job(payload.get("interaction_log_id", task.entity_id or ""))
    if task.task_type == TASK_TYPE_MESSAGE_REPLY:
        return reply_to_message_job(payload.get("message_log_id", task.entity_id or ""))
    raise ValueError(f"Loại tác vụ không được hỗ trợ: {task.task_type}")


def process_task_queue(worker_name: str) -> int:
    processed = 0
    db: Session = SessionLocal()
    try:
        for _ in range(settings.WORKER_BATCH_SIZE):
            task = claim_next_task(db, worker_name)
            if not task:
                break

            update_worker_heartbeat(
                worker_name,
                app_role=settings.APP_ROLE,
                status="processing",
                current_task_id=str(task.id),
                current_task_type=task.task_type,
                details={"attempts": task.attempts, "entity_type": task.entity_type, "entity_id": task.entity_id},
                db=db,
            )
            record_event(
                "queue",
                "info",
                "Bắt đầu xử lý tác vụ nền.",
                db=db,
                details={"task_id": str(task.id), "task_type": task.task_type, "worker_name": worker_name},
            )

            try:
                result = _run_task(task)
                complete_task(db, task)
                record_event(
                    "queue",
                    "info",
                    "Đã hoàn tất tác vụ nền.",
                    db=db,
                    details={"task_id": str(task.id), "task_type": task.task_type, "result": result},
                )
            except Exception as exc:
                fail_task(db, task, str(exc))
                record_event(
                    "queue",
                    "error",
                    "Tác vụ nền thất bại.",
                    db=db,
                    details={"task_id": str(task.id), "task_type": task.task_type, "error": str(exc)},
                )
            processed += 1

        update_worker_heartbeat(
            worker_name,
            app_role=settings.APP_ROLE,
            status="idle",
            db=db,
        )
        return processed
    finally:
        db.close()
