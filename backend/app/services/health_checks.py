from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.models.models import FacebookPage
from app.services.ai_generator import check_gemini_health
from app.services.fb_graph import check_facebook_graph_health
from app.services.runtime_settings import RUNTIME_ENV_FILE, resolve_runtime_value
from app.services.security import decrypt_secret
from app.services.task_queue import count_stale_processing_tasks, summarize_tasks
from app.services.ytdlp_crawler import get_downloader_health


def check_runtime_env_health() -> dict:
    runtime_path = Path(RUNTIME_ENV_FILE)
    parent_path = runtime_path.parent
    return {
        "ok": parent_path.exists() and parent_path.is_dir(),
        "file_exists": runtime_path.exists(),
        "path": str(runtime_path),
        "parent_exists": parent_path.exists(),
        "message": "runtime.env đã sẵn sàng." if parent_path.exists() else "Không tìm thấy thư mục chứa runtime.env.",
    }


def check_facebook_dependency(db: Session) -> dict:
    page = (
        db.query(FacebookPage)
        .filter(FacebookPage.long_lived_access_token.isnot(None))
        .order_by(FacebookPage.updated_at.desc())
        .first()
    )
    if not page:
        return {
            "configured": False,
            "ok": True,
            "status": "skipped",
            "message": "Chưa có fanpage nào để kiểm tra Facebook Graph.",
        }

    try:
        access_token = decrypt_secret(page.long_lived_access_token)
    except ValueError as exc:
        return {
            "configured": True,
            "ok": False,
            "status": "error",
            "message": str(exc),
            "page_id": page.page_id,
            "page_name": page.page_name,
        }

    result = check_facebook_graph_health(page.page_id, access_token)
    return {
        **result,
        "page_id": page.page_id,
        "page_name": page.page_name,
    }


def check_gemini_dependency(db: Session) -> dict:
    api_key = resolve_runtime_value("GEMINI_API_KEY", db=db)
    return check_gemini_health(api_key)


def build_queue_health(db: Session) -> dict:
    summary = summarize_tasks(db)
    stale_processing_count = count_stale_processing_tasks(db)
    return {
        "summary": summary,
        "stale_processing_count": stale_processing_count,
        "failed_count": summary.get("failed", 0),
        "ok": stale_processing_count == 0,
    }


def build_overall_health_status(
    *,
    database_ok: bool,
    downloader_ok: bool,
    runtime_env_ok: bool,
    queue_health: dict,
    facebook_health: dict,
    gemini_health: dict,
) -> str:
    if not database_ok or not downloader_ok or not runtime_env_ok:
        return "unhealthy"

    if not queue_health.get("ok", True):
        return "degraded"

    if facebook_health.get("configured") and not facebook_health.get("ok", False):
        return "degraded"

    if gemini_health.get("configured") and not gemini_health.get("ok", False):
        return "degraded"

    return "healthy"
