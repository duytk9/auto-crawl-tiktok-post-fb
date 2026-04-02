import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Uuid

from app.core.database import Base
from app.core.time import utc_now
from app.models.common import JSON_TYPE


class TaskStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class UserRole(str, enum.Enum):
    admin = "admin"
    operator = "operator"


class TaskQueue(Base):
    __tablename__ = "task_queue"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(String, index=True)
    entity_type = Column(String, index=True, nullable=True)
    entity_id = Column(String, index=True, nullable=True)
    payload = Column(JSON_TYPE)
    status = Column(Enum(TaskStatus), default=TaskStatus.queued)
    priority = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    last_error = Column(String, nullable=True)
    available_at = Column(DateTime, default=utc_now)
    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    display_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.admin, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    must_change_password = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_name = Column(String, unique=True, index=True)
    app_role = Column(String, nullable=False)
    hostname = Column(String, nullable=True)
    status = Column(String, default="idle", nullable=False)
    current_task_id = Column(String, nullable=True)
    current_task_type = Column(String, nullable=True)
    details = Column(JSON_TYPE, nullable=True)
    last_seen_at = Column(DateTime, default=utc_now, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class SystemEvent(Base):
    __tablename__ = "system_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scope = Column(String, index=True, nullable=False)
    level = Column(String, index=True, nullable=False)
    message = Column(String, nullable=False)
    details = Column(JSON_TYPE, nullable=True)
    actor_user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now, index=True)


class RuntimeSetting(Base):
    __tablename__ = "runtime_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    is_secret = Column(Boolean, default=False, nullable=False)
    updated_by_user_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
