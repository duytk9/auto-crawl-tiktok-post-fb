from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.observability import record_event, update_worker_heartbeat
from app.services.task_queue import (
    claim_next_task,
    complete_task,
    fail_task,
)
from app.worker.task_registry import run_task


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
                result = run_task(task)
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
