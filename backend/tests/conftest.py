import os
from pathlib import Path
import tempfile
import uuid

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

TEST_DB_PATH = Path(tempfile.gettempdir()) / f"social_tool_test_suite_{uuid.uuid4().hex}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["JWT_SECRET"] = "test-jwt-secret"
os.environ["TOKEN_ENCRYPTION_SECRET"] = "test-token-secret"
os.environ["ADMIN_PASSWORD"] = "admin12345"
os.environ["DEFAULT_ADMIN_USERNAME"] = "admin"
os.environ["DEFAULT_ADMIN_DISPLAY_NAME"] = "Quản trị viên kiểm thử"
os.environ["FB_VERIFY_TOKEN"] = "test-verify-token"
os.environ["PASSWORD_MIN_LENGTH"] = "8"
os.environ["SCHEDULER_ENABLED"] = "false"
os.environ["BACKGROUND_JOBS_MODE"] = "dedicated-worker"
os.environ["APP_ROLE"] = "api"

from app.api import auth, campaigns, facebook, system, users, webhooks
from app.api.auth import require_authenticated_user
from app.core.database import Base, SessionLocal, engine
from app.services.accounts import ensure_default_admin


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_file():
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
    except OSError:
        pass

    yield

    engine.dispose()
    try:
        if TEST_DB_PATH.exists():
            TEST_DB_PATH.unlink()
    except OSError:
        pass


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_admin(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(campaigns.router, dependencies=[Depends(require_authenticated_user)])
    app.include_router(facebook.router, dependencies=[Depends(require_authenticated_user)])
    app.include_router(system.router, dependencies=[Depends(require_authenticated_user)])
    app.include_router(users.router, dependencies=[Depends(require_authenticated_user)])
    app.include_router(webhooks.router)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": os.environ["ADMIN_PASSWORD"]},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
