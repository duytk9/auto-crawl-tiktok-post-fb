from __future__ import annotations

import os
import time

import requests

from app.services.http_client import request_with_retries
from app.services.observability import log_structured

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


def _build_graph_error_message(data, status_code: int) -> str:
    error = data.get("error", {}) if isinstance(data, dict) else {}
    if error.get("message"):
        return error["message"]
    return f"Facebook Graph API trả về lỗi {status_code}."


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {}


def _parse_graph_response(response):
    data = _safe_json(response)
    if response.ok and "error" not in data:
        return {
            "ok": True,
            "status_code": response.status_code,
            "data": data,
        }

    return {
        "ok": False,
        "status_code": response.status_code,
        "data": data,
        "message": _build_graph_error_message(data, response.status_code),
    }


def _graph_get(path: str, *, params: dict | None = None, timeout: int = 30):
    response = request_with_retries(
        "GET",
        f"{GRAPH_API_BASE}/{path.lstrip('/')}",
        params=params,
        timeout=timeout,
        scope="facebook_graph",
        operation=f"GET {path}",
    )
    return _parse_graph_response(response)


def _graph_post(
    path: str,
    *,
    data: dict | None = None,
    json_payload: dict | None = None,
    params: dict | None = None,
    timeout: int = 30,
):
    response = request_with_retries(
        "POST",
        f"{GRAPH_API_BASE}/{path.lstrip('/')}",
        data=data,
        json=json_payload,
        params=params,
        timeout=timeout,
        scope="facebook_graph",
        operation=f"POST {path}",
    )
    return _parse_graph_response(response)


def upload_video_to_facebook(file_path: str, caption: str, page_id: str, access_token: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file: {file_path}")

    if access_token.startswith("http://") or access_token.startswith("https://"):
        return {"error": "Vui lòng thay URL webhook bằng mã truy cập trang Facebook thật trong cấu hình."}

    try:
        log_structured(
            "facebook_graph",
            "info",
            "Bắt đầu khởi tạo đăng Facebook Reels.",
            details={"page_id": page_id, "file_path": file_path},
        )
        init_result = _graph_post(
            f"{page_id}/video_reels",
            params={
                "upload_phase": "start",
                "access_token": access_token,
            },
            timeout=30,
        )
        if not init_result["ok"] or "video_id" not in init_result["data"]:
            log_structured(
                "facebook_graph",
                "error",
                "Facebook từ chối giai đoạn khởi tạo Reel.",
                details={"page_id": page_id, "response": init_result},
            )
            return {"error": f"Lỗi khởi tạo Reels: {init_result.get('message', 'Lỗi không xác định')}"}

        video_id = init_result["data"]["video_id"]
        log_structured(
            "facebook_graph",
            "info",
            "Đã khởi tạo Reel và nhận video_id.",
            details={"page_id": page_id, "video_id": video_id},
        )

        upload_url = f"https://rupload.facebook.com/video-upload/v19.0/{video_id}"
        file_size = os.path.getsize(file_path)
        with open(file_path, "rb") as file_handle:
            upload_response = requests.post(
                upload_url,
                data=file_handle,
                headers={
                    "Authorization": f"OAuth {access_token}",
                    "offset": "0",
                    "file_size": str(file_size),
                    "X-Entity-Type": "video/mp4",
                    "X-Entity-Name": "video.mp4",
                },
                timeout=300,
            )

        upload_data = _safe_json(upload_response)
        if "id" not in upload_data and not upload_data.get("success"):
            log_structured(
                "facebook_graph",
                "error",
                "Facebook RUpload không xác nhận video upload thành công.",
                details={"page_id": page_id, "video_id": video_id, "response": upload_data},
            )
            return {"error": f"Lỗi tải video (RUpload): {upload_data.get('error', {}).get('message', 'Tải video thất bại')}"}

        log_structured(
            "facebook_graph",
            "info",
            "Đã tải video lên Facebook RUpload, chờ công bố.",
            details={"page_id": page_id, "video_id": video_id},
        )
        time.sleep(20)

        publish_result = _graph_post(
            f"{page_id}/video_reels",
            params={
                "upload_phase": "finish",
                "video_id": video_id,
                "video_state": "PUBLISHED",
                "description": caption,
                "access_token": access_token,
            },
            timeout=30,
        )

        if publish_result["ok"] and publish_result["data"].get("success"):
            log_structured(
                "facebook_graph",
                "info",
                "Đã công bố Facebook Reel thành công.",
                details={"page_id": page_id, "video_id": video_id},
            )
            return {"id": video_id}

        log_structured(
            "facebook_graph",
            "error",
            "Facebook không công bố được Reel.",
            details={"page_id": page_id, "video_id": video_id, "response": publish_result},
        )
        return {"error": f"Lỗi công bố: {publish_result.get('message', 'Công bố thất bại')}"}
    except Exception as exc:
        log_structured(
            "facebook_graph",
            "error",
            "Lỗi hệ thống khi đăng Facebook Reel.",
            details={"page_id": page_id, "file_path": file_path, "error": str(exc)},
        )
        return {"error": f"Lỗi hệ thống khi đăng FB: {exc}"}


def inspect_page_access(page_id: str, access_token: str):
    try:
        token_subject = _graph_get(
            "me",
            params={"fields": "id,name", "access_token": access_token},
            timeout=30,
        )
        if not token_subject["ok"]:
            return {
                "ok": False,
                "message": token_subject["message"],
                "token_kind": "invalid_token",
            }

        page_result = _graph_get(
            page_id,
            params={
                "fields": "id,name,link,fan_count",
                "access_token": access_token,
            },
            timeout=30,
        )
        if not page_result["ok"]:
            return {
                "ok": False,
                "message": page_result["message"],
                "token_kind": "invalid_token",
                "token_subject_id": token_subject["data"].get("id"),
                "token_subject_name": token_subject["data"].get("name"),
            }
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Không thể kết nối tới Facebook Graph API: {exc}",
            "token_kind": "network_error",
        }

    token_subject_id = token_subject["data"].get("id")
    token_subject_name = token_subject["data"].get("name")
    page_data = page_result["data"]
    is_page_token = token_subject_id == page_id

    if not is_page_token:
        return {
            "ok": False,
            "message": "Mã truy cập hiện tại là User Access Token. Hãy dùng đúng Page Access Token của fanpage.",
            "token_kind": "user_access_token",
            "token_subject_id": token_subject_id,
            "token_subject_name": token_subject_name,
            "page_id": page_data.get("id", page_id),
            "page_name": page_data.get("name"),
        }

    return {
        "ok": True,
        "message": f"Mã truy cập hợp lệ cho trang Facebook {page_data.get('name', page_id)}.",
        "token_kind": "page_access_token",
        "token_subject_id": token_subject_id,
        "token_subject_name": token_subject_name,
        "page_id": page_data.get("id", page_id),
        "page_name": page_data.get("name"),
        "page_link": page_data.get("link"),
        "fan_count": page_data.get("fan_count"),
    }


def check_facebook_graph_health(page_id: str | None, access_token: str | None):
    if not page_id or not access_token:
        return {
            "configured": False,
            "ok": True,
            "status": "skipped",
            "message": "Chưa có fanpage nào được cấu hình để kiểm tra Facebook Graph.",
        }

    inspection = inspect_page_access(page_id, access_token)
    if inspection.get("ok"):
        return {
            "configured": True,
            "ok": True,
            "status": "healthy",
            "message": inspection.get("message"),
            "page_id": inspection.get("page_id"),
            "page_name": inspection.get("page_name"),
            "token_kind": inspection.get("token_kind"),
        }

    return {
        "configured": True,
        "ok": False,
        "status": "error",
        "message": inspection.get("message", "Facebook Graph API chưa sẵn sàng."),
        "page_id": page_id,
        "token_kind": inspection.get("token_kind"),
    }


def inspect_page_messenger_subscription(page_id: str, access_token: str, *, required_fields: tuple[str, ...] = ("messages",)):
    try:
        result = _graph_get(
            f"{page_id}/subscribed_apps",
            params={
                "fields": "id,name,subscribed_fields",
                "access_token": access_token,
            },
            timeout=30,
        )
    except Exception as exc:
        return {
            "ok": False,
            "connected": False,
            "message": f"Không thể kiểm tra kết nối Messenger: {exc}",
            "required_fields": list(required_fields),
            "apps": [],
        }

    if not result["ok"]:
        return {
            "ok": False,
            "connected": False,
            "message": result["message"],
            "required_fields": list(required_fields),
            "apps": [],
        }

    apps = []
    for app in result["data"].get("data", []):
        fields = app.get("subscribed_fields") or []
        apps.append(
            {
                "id": app.get("id"),
                "name": app.get("name"),
                "subscribed_fields": fields,
            }
        )

    connected_app = next(
        (
            app
            for app in apps
            if all(field in (app.get("subscribed_fields") or []) for field in required_fields)
        ),
        None,
    )

    if connected_app:
        return {
            "ok": True,
            "connected": True,
            "message": f"Inbox đã kết nối với app {connected_app.get('name') or connected_app.get('id')}.",
            "required_fields": list(required_fields),
            "connected_app": connected_app,
            "apps": apps,
        }

    return {
        "ok": True,
        "connected": False,
        "message": "Fanpage chưa đăng ký nhận webhook tin nhắn cho app này.",
        "required_fields": list(required_fields),
        "connected_app": None,
        "apps": apps,
    }


def subscribe_page_to_app(page_id: str, access_token: str, *, subscribed_fields: tuple[str, ...] = ("messages",)):
    try:
        result = _graph_post(
            f"{page_id}/subscribed_apps",
            data={
                "subscribed_fields": ",".join(dict.fromkeys(subscribed_fields)),
                "access_token": access_token,
            },
            timeout=30,
        )
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Không thể đăng ký fanpage với app: {exc}",
        }

    if not result["ok"]:
        return {
            "ok": False,
            "message": result["message"],
            "data": result.get("data"),
        }

    return {
        "ok": bool(result["data"].get("success")),
        "message": "Đã đăng ký fanpage nhận webhook tin nhắn." if result["data"].get("success") else "Facebook không xác nhận đăng ký fanpage.",
        "data": result["data"],
    }


def reply_to_comment(comment_id: str, message: str, access_token: str):
    try:
        result = _graph_post(
            f"{comment_id}/comments",
            data={"message": message, "access_token": access_token},
            timeout=30,
        )
        if not result["ok"]:
            log_structured(
                "facebook_graph",
                "warning",
                "Facebook từ chối phản hồi bình luận.",
                details={"comment_id": comment_id, "message": result["message"]},
            )
            return {"error": result["message"], **(result.get("data") or {})}
        return result["data"]
    except Exception as exc:
        log_structured(
            "facebook_graph",
            "error",
            "Lỗi API phản hồi bình luận Facebook.",
            details={"comment_id": comment_id, "error": str(exc)},
        )
        return {"error": str(exc)}


def send_page_message(recipient_id: str, message: str, access_token: str):
    try:
        result = _graph_post(
            "me/messages",
            params={"access_token": access_token},
            json_payload={
                "recipient": {"id": recipient_id},
                "messaging_type": "RESPONSE",
                "message": {"text": message},
            },
            timeout=30,
        )
        if not result["ok"]:
            log_structured(
                "facebook_graph",
                "warning",
                "Facebook từ chối gửi phản hồi inbox.",
                details={"recipient_id": recipient_id, "message": result["message"]},
            )
            return {"error": result["message"], **(result.get("data") or {})}
        return result["data"]
    except Exception as exc:
        log_structured(
            "facebook_graph",
            "error",
            "Lỗi API gửi tin nhắn inbox Facebook.",
            details={"recipient_id": recipient_id, "error": str(exc)},
        )
        return {"error": str(exc)}
