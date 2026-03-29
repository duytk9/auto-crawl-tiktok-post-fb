import os
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api import auth, campaigns, facebook, system, users, webhooks
from app.api.auth import require_authenticated_user
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models import models  # noqa: F401
from app.services.accounts import ensure_default_admin
from app.services.observability import configure_logging, record_event
from app.services.runtime_settings import write_runtime_env_file
from app.worker.cron import start_scheduler

configure_logging()

max_retries = 10
retry_count = 0
while retry_count < max_retries:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        if settings.AUTO_CREATE_SCHEMA:
            Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            ensure_default_admin(db)
            write_runtime_env_file(db)
        break
    except OperationalError:
        retry_count += 1
        record_event(
            "system",
            "warning",
            "Kết nối cơ sở dữ liệu thất bại khi khởi động, sẽ thử lại.",
            details={"retry_count": retry_count, "max_retries": max_retries},
        )
        if retry_count == max_retries:
            raise
        time.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    record_event(
        "system",
        "info",
        "Ứng dụng API đã khởi động.",
        details={"app_role": settings.APP_ROLE, "scheduler_enabled": settings.SCHEDULER_ENABLED},
    )
    if settings.SCHEDULER_ENABLED:
        start_scheduler()
    yield
    record_event("system", "warning", "Ứng dụng API đã dừng.", details={"app_role": settings.APP_ROLE})


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.include_router(auth.router)
app.include_router(campaigns.router, dependencies=[Depends(require_authenticated_user)])
app.include_router(facebook.router, dependencies=[Depends(require_authenticated_user)])
app.include_router(system.router, dependencies=[Depends(require_authenticated_user)])
app.include_router(users.router, dependencies=[Depends(require_authenticated_user)])
app.include_router(webhooks.router)

os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=settings.DOWNLOAD_DIR), name="downloads")

allow_origins = settings.CORS_ALLOW_ORIGINS or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials="*" not in allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Chào mừng bạn đến với hệ thống tự động mạng xã hội"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app_role": settings.APP_ROLE,
        "background_jobs_mode": settings.BACKGROUND_JOBS_MODE,
    }
