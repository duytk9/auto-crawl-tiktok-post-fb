from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.time import utc_now
from app.models.models import User, UserRole
from app.services.accounts import serialize_user
from app.services.observability import record_event
from app.services.security import (
    check_login_rate_limit,
    clear_login_rate_limit,
    create_access_token,
    decode_access_token,
    get_client_identity,
    register_failed_login,
    validate_password_strength,
    verify_password,
    hash_password,
)

router = APIRouter(prefix="/auth", tags=["Xác thực"])
security = HTTPBearer()


class LoginRequest(BaseModel):
    username: str = Field(default=settings.DEFAULT_ADMIN_USERNAME, min_length=1)
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập đã hết hạn",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=401,
            detail="Mã truy cập không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        user_id = UUID(payload.get("sub", ""))
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Mã truy cập không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="Tài khoản không còn hoạt động",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(current_user: User = Depends(require_authenticated_user)) -> User:
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Bạn không có quyền quản trị thao tác này.")
    return current_user


@router.post("/login")
def login(creds: LoginRequest, request: Request, db: Session = Depends(get_db)):
    username = creds.username.strip().lower()
    client_id = get_client_identity(request)
    retry_after = check_login_rate_limit(client_id, username)
    if retry_after > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {retry_after} giây.",
        )

    user = db.query(User).filter(User.username == username).first()
    if user and user.is_active and verify_password(creds.password, user.password_hash):
        clear_login_rate_limit(client_id, username)
        user.last_login_at = utc_now()
        db.commit()
        access_token, expires_in = create_access_token(user.id, user.username, user.role.value)
        record_event(
            "auth",
            "info",
            "Đăng nhập thành công.",
            db=db,
            actor_user_id=str(user.id),
            details={"username": user.username, "ip": client_id},
        )
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user": serialize_user(user),
        }

    retry_after = register_failed_login(client_id, username)
    record_event(
        "auth",
        "warning",
        "Đăng nhập thất bại.",
        db=db,
        details={"username": username, "ip": client_id},
    )
    if retry_after > 0:
        raise HTTPException(
            status_code=429,
            detail=f"Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau {retry_after} giây.",
        )
    raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")


@router.get("/me")
def get_me(current_user: User = Depends(require_authenticated_user)):
    return serialize_user(current_user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không chính xác.")

    password_error = validate_password_strength(payload.new_password)
    if password_error:
        raise HTTPException(status_code=400, detail=password_error)

    current_user.password_hash = hash_password(payload.new_password)
    current_user.must_change_password = False
    db.commit()
    record_event(
        "auth",
        "info",
        "Người dùng đã đổi mật khẩu.",
        db=db,
        actor_user_id=str(current_user.id),
        details={"username": current_user.username},
    )
    return {"message": "Đã cập nhật mật khẩu thành công."}
