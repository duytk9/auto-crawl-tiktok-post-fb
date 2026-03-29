from __future__ import annotations

import socket
import sys

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.time import utc_now
from app.models.models import WorkerHeartbeat

WORKER_NAME = f"{settings.APP_ROLE}@{socket.gethostname()}"


def main() -> int:
    db = SessionLocal()
    try:
        heartbeat = db.query(WorkerHeartbeat).filter(WorkerHeartbeat.worker_name == WORKER_NAME).first()
        if not heartbeat or not heartbeat.last_seen_at:
            return 1

        age_seconds = (utc_now() - heartbeat.last_seen_at).total_seconds()
        max_age_seconds = max(settings.WORKER_STALE_SECONDS * 2, 30)
        return 0 if age_seconds <= max_age_seconds else 1
    except Exception:
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
