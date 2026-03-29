from __future__ import annotations

from datetime import datetime
import json
import logging
import socket
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import utc_now
from app.models.models import SystemEvent, WorkerHeartbeat

LOGGER_NAME = "social_tool"
_LOGGING_CONFIGURED = False


def configure_logging() -> None:
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
    if not root_logger.handlers:
        logging.basicConfig(level=root_logger.level, format="%(message)s")
    _LOGGING_CONFIGURED = True


def _get_logger(scope: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(f"{LOGGER_NAME}.{scope}")


def _normalize_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    normalized = {}
    for key, value in details.items():
        if isinstance(value, datetime):
            normalized[key] = value.isoformat()
        else:
            normalized[key] = value
    return normalized


def log_structured(
    scope: str,
    level: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_details = _normalize_details(details)
    payload = {
        "timestamp": utc_now().isoformat(),
        "scope": scope,
        "level": level.upper(),
        "message": message,
        "details": normalized_details,
    }
    _get_logger(scope).log(getattr(logging, level.upper(), logging.INFO), json.dumps(payload, ensure_ascii=False))
    return payload


def record_event(
    scope: str,
    level: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    db: Session | None = None,
    actor_user_id: str | None = None,
) -> None:
    normalized_details = _normalize_details(details)
    log_structured(scope, level, message, details=normalized_details)

    own_session = False
    session = db
    try:
        if session is None:
            session = SessionLocal()
            own_session = True
        session.add(
            SystemEvent(
                scope=scope,
                level=level.upper(),
                message=message,
                details=normalized_details or None,
                actor_user_id=actor_user_id,
            )
        )
        session.commit()
    except Exception:
        if own_session and session is not None:
            session.rollback()
    finally:
        if own_session and session is not None:
            session.close()


def update_worker_heartbeat(
    worker_name: str,
    *,
    app_role: str,
    status: str,
    current_task_id: str | None = None,
    current_task_type: str | None = None,
    details: dict[str, Any] | None = None,
    db: Session | None = None,
) -> None:
    own_session = False
    session = db
    if session is None:
        session = SessionLocal()
        own_session = True

    try:
        heartbeat = session.query(WorkerHeartbeat).filter(WorkerHeartbeat.worker_name == worker_name).first()
        if not heartbeat:
            heartbeat = WorkerHeartbeat(
                worker_name=worker_name,
                app_role=app_role,
                hostname=socket.gethostname(),
            )
            session.add(heartbeat)

        heartbeat.app_role = app_role
        heartbeat.hostname = socket.gethostname()
        heartbeat.status = status
        heartbeat.current_task_id = current_task_id
        heartbeat.current_task_type = current_task_type
        heartbeat.details = _normalize_details(details) or None
        heartbeat.last_seen_at = utc_now()
        session.commit()
    finally:
        if own_session and session is not None:
            session.close()
