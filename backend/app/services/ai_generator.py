import json
import unicodedata
from typing import Any

from app.core.config import settings
from app.services.http_client import request_with_retries
from app.services.observability import log_structured
from app.services.runtime_settings import resolve_runtime_value

GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_COMMENT_REPLY_PROMPT = (
    "Bạn là chăm sóc khách hàng cho fanpage Facebook. "
    "Hãy trả lời bình luận thật thân thiện, ngắn gọn, tự nhiên và phù hợp ngữ cảnh. "
    "Chỉ trả về nội dung câu trả lời, không giải thích thêm."
)
DEFAULT_MESSAGE_REPLY_PROMPT = (
    "Bạn là trợ lý tư vấn cho fanpage Facebook. "
    "Hãy trả lời tin nhắn inbox theo phong cách lịch sự, rõ ràng, hữu ích và chủ động gợi mở bước tiếp theo khi phù hợp. "
    "Chỉ trả về nội dung tin nhắn gửi cho khách."
)


def _strip_hashtag_tokens(text: str) -> str:
    return " ".join(token for token in (text or "").replace("\n", " ").split() if not token.startswith("#")).strip()


def _slugify_ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return "".join(char for char in ascii_text.lower() if char.isalnum() or char.isspace()).strip()


def _build_caption_hashtags(original_caption: str, caption_body: str) -> list[str]:
    corpus = _slugify_ascii(f"{original_caption} {caption_body}")
    hashtags = []

    if any(keyword in corpus for keyword in ["trung quoc", "china", "chinese"]):
        hashtags.append("#gaixinhtrungquoc")

    if any(keyword in corpus for keyword in ["nhay", "dance", "dancing", "vu dao"]):
        hashtags.append("#gaixinhnhay")

    if "gaixinhtrungquoc" not in [tag.lstrip("#") for tag in hashtags]:
        hashtags.append("#gaixinh")
    if "gaixinhnhay" not in [tag.lstrip("#") for tag in hashtags]:
        hashtags.append("#gaixinhnhay")

    hashtags.extend(["#viral", "#trending", "#xuhuong"])

    deduped = []
    for tag in hashtags:
        if tag not in deduped:
            deduped.append(tag)
        if len(deduped) == 4:
            break
    return deduped


def _normalize_caption_length(caption: str, original_caption: str) -> str:
    normalized = _strip_hashtag_tokens(caption)
    normalized = " ".join(normalized.replace("\n", " ").split()).strip()
    backup = " ".join(_strip_hashtag_tokens(original_caption).split()).strip()

    if not normalized:
        normalized = backup

    words = normalized.split()
    if len(words) > 20:
        return " ".join(words[:20]).strip()

    if len(words) >= 15:
        return normalized

    backup_words = backup.split()
    extended_words = list(words)
    for candidate in backup_words:
        if len(extended_words) >= 15:
            break
        extended_words.append(candidate)

    if not extended_words:
        return ""

    return " ".join(extended_words[:20]).strip()


def _extract_json_payload(raw_text: str) -> dict[str, Any] | None:
    text = (raw_text or "").strip()
    if not text:
        return None

    candidates = [text]
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            cleaned = part.replace("json", "", 1).strip()
            if cleaned:
                candidates.append(cleaned)

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _normalize_reply_payload(
    payload: dict[str, Any] | None,
    *,
    fallback_reply: str,
    fallback_summary: str | None,
    fallback_intent: str = "general_support",
    fallback_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = payload or {}
    reply = str(data.get("reply") or "").strip() or fallback_reply
    summary = str(data.get("summary") or "").strip() or (fallback_summary or "")
    intent = str(data.get("intent") or "").strip() or fallback_intent
    customer_facts = data.get("customer_facts")
    if not isinstance(customer_facts, dict):
        customer_facts = fallback_facts or {}
    handoff = bool(data.get("handoff"))
    handoff_reason = str(data.get("handoff_reason") or "").strip() or None
    return {
        "reply": reply,
        "summary": summary[: settings.INBOX_SUMMARY_MAX_CHARS],
        "intent": intent[:80],
        "customer_facts": customer_facts,
        "handoff": handoff,
        "handoff_reason": handoff_reason[:300] if handoff_reason else None,
    }


def _generate_with_gemini(
    prompt: str,
    fallback: str,
    *,
    timeout: int = 20,
    max_retries: int = 3,
    generation_config: dict[str, Any] | None = None,
) -> str:
    gemini_api_key = resolve_runtime_value("GEMINI_API_KEY")
    if not gemini_api_key:
        log_structured("gemini", "warning", "Chưa cấu hình GEMINI_API_KEY, dùng nội dung fallback.")
        return fallback

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={gemini_api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    if generation_config:
        payload["generationConfig"] = generation_config

    try:
        response = request_with_retries(
            "POST",
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout,
            max_attempts=max_retries,
            scope="gemini",
            operation="generate_content",
        )
    except Exception as exc:
        log_structured(
            "gemini",
            "error",
            "Không thể gọi Gemini sau nhiều lần thử.",
            details={"model": GEMINI_MODEL, "error": str(exc)},
        )
        return fallback

    if response.status_code == 200:
        data = response.json()
        if data.get("candidates") and data["candidates"][0].get("content"):
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    log_structured(
        "gemini",
        "warning",
        "Gemini không trả về nội dung hợp lệ, dùng fallback.",
        details={"model": GEMINI_MODEL, "status_code": response.status_code},
    )
    return fallback


def generate_caption(original_caption: str) -> str:
    prompt = f"""Bạn là Trùm Copywriter chuyên viral content Facebook. Mệnh lệnh bắt buộc:
1. Viết lại caption sao cho kịch tính, thú vị, tự nhiên, đúng ngữ cảnh video.
2. Caption bắt buộc chỉ dài từ 15 đến 20 từ, không ít hơn và không nhiều hơn.
3. Sau caption chính, thêm đúng 4 hashtag viết liền không dấu, ưu tiên kiểu: #gaixinhtrungquoc #gaixinhnhay #viral #trending.
4. Không thêm giải thích, không thêm tiêu đề, không xuống dòng.

Caption gốc: {original_caption}"""
    fallback_body = _normalize_caption_length(_strip_hashtag_tokens(original_caption), original_caption)
    fallback_hashtags = _build_caption_hashtags(original_caption, fallback_body)
    fallback = f"{fallback_body} {' '.join(fallback_hashtags)}".strip()
    generated = _generate_with_gemini(prompt, fallback, timeout=30)
    normalized_body = _normalize_caption_length(generated, original_caption)
    hashtags = _build_caption_hashtags(original_caption, normalized_body)
    return f"{normalized_body} {' '.join(hashtags)}".strip()


def generate_message_reply_with_context(
    user_message: str,
    *,
    prompt_override: str | None = None,
    conversation_summary: str | None = None,
    recent_turns: list[dict[str, str]] | None = None,
    customer_facts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_prompt = (prompt_override or "").strip() or DEFAULT_MESSAGE_REPLY_PROMPT
    fallback_reply = "Cảm ơn bạn đã nhắn cho trang. Bên mình sẽ hỗ trợ bạn sớm nhé!"
    fallback_summary = conversation_summary or f"Khách vừa nhắn: {user_message}"

    facts = customer_facts if isinstance(customer_facts, dict) else {}
    facts_block = json.dumps(facts, ensure_ascii=False) if facts else "{}"
    history_lines = []
    for turn in recent_turns or []:
        role = "Khách" if turn.get("role") == "customer" else "Trang"
        content = (turn.get("content") or "").strip()
        if content:
            history_lines.append(f"- {role}: {content}")
    history_block = "\n".join(history_lines) if history_lines else "- Chưa có lịch sử trước đó."

    prompt = (
        f"{base_prompt}\n\n"
        "Bạn đang xử lý một cuộc trò chuyện nhiều lượt với khách hàng Facebook.\n"
        "Yêu cầu bắt buộc:\n"
        "1. Phải dựa vào toàn bộ ngữ cảnh đã biết để trả lời, không được coi đây là cuộc trò chuyện mới.\n"
        "2. Không hỏi lại thông tin mà khách đã nói trong lịch sử hoặc facts.\n"
        "3. Nếu còn thiếu dữ kiện, chỉ hỏi đúng một câu ngắn gọn để lấy phần còn thiếu.\n"
        "4. Nếu vấn đề nên chuyển người thật xử lý, đặt handoff=true và handoff_reason ngắn gọn.\n"
        f"5. summary phải là bản tóm tắt cập nhật của cuộc trò chuyện, tối đa {settings.INBOX_SUMMARY_MAX_CHARS} ký tự.\n"
        "6. customer_facts là object JSON ngắn gọn, chỉ giữ các dữ kiện hữu ích để nhớ ở lượt sau.\n"
        "7. Chỉ trả về đúng JSON, không thêm markdown hay giải thích.\n\n"
        "Schema JSON bắt buộc:\n"
        '{"reply":"...","summary":"...","intent":"...","customer_facts":{"key":"value"},"handoff":false,"handoff_reason":null}\n\n'
        f"Tóm tắt hiện tại:\n{(conversation_summary or 'Chưa có tóm tắt.').strip()}\n\n"
        f"Thông tin đã biết về khách:\n{facts_block}\n\n"
        f"Lịch sử gần nhất:\n{history_block}\n\n"
        f"Tin nhắn mới nhất của khách:\n{user_message}"
    )

    fallback_payload = _normalize_reply_payload(
        None,
        fallback_reply=fallback_reply,
        fallback_summary=fallback_summary,
        fallback_facts=facts,
    )
    raw_result = _generate_with_gemini(
        prompt,
        json.dumps(fallback_payload, ensure_ascii=False),
        timeout=30,
        generation_config={
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    )
    payload = _extract_json_payload(raw_result)
    if payload is None:
        log_structured(
            "gemini",
            "warning",
            "Gemini trả về structured reply không hợp lệ, dùng fallback chuẩn hóa.",
            details={"model": GEMINI_MODEL},
        )
    return _normalize_reply_payload(
        payload,
        fallback_reply=fallback_reply,
        fallback_summary=fallback_summary,
        fallback_facts=facts,
    )


def generate_reply(user_message: str, *, channel: str = "comment", prompt_override: str | None = None) -> str:
    is_message_channel = channel == "message"
    base_prompt = (prompt_override or "").strip() or (
        DEFAULT_MESSAGE_REPLY_PROMPT if is_message_channel else DEFAULT_COMMENT_REPLY_PROMPT
    )
    customer_label = "Tin nhắn inbox" if is_message_channel else "Bình luận"
    fallback = "Cảm ơn bạn đã nhắn cho trang. Bên mình sẽ hỗ trợ bạn sớm nhé!"
    if not is_message_channel:
        fallback = "Cảm ơn bạn đã quan tâm nhé! 💖"

    prompt = (
        f"{base_prompt}\n\n"
        f"Ngữ cảnh hiện tại:\n"
        f"- Kênh: {customer_label}\n"
        f"- Trả lời ngắn gọn, đúng trọng tâm, không lặp ý.\n"
        f"- Không nhắc đến việc bạn là AI.\n\n"
        f"Khách hàng nhắn: {user_message}"
    )
    return _generate_with_gemini(prompt, fallback)


def check_gemini_health(api_key: str | None = None) -> dict:
    resolved_key = (api_key or resolve_runtime_value("GEMINI_API_KEY") or "").strip()
    if not resolved_key:
        return {
            "configured": False,
            "ok": True,
            "status": "skipped",
            "model": GEMINI_MODEL,
            "message": "Chưa cấu hình GEMINI_API_KEY nên bỏ qua kiểm tra Gemini.",
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={resolved_key}"
    try:
        response = request_with_retries(
            "GET",
            url,
            timeout=min(settings.EXTERNAL_HTTP_TIMEOUT, 8),
            max_attempts=2,
            scope="gemini",
            operation="health_check",
        )
    except Exception as exc:
        return {
            "configured": True,
            "ok": False,
            "status": "error",
            "model": GEMINI_MODEL,
            "message": f"Không thể kết nối Gemini: {exc}",
        }

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code != 200:
        error_message = data.get("error", {}).get("message") if isinstance(data, dict) else None
        return {
            "configured": True,
            "ok": False,
            "status": "error",
            "model": GEMINI_MODEL,
            "message": error_message or f"Gemini trả về HTTP {response.status_code}.",
        }

    model_names = [item.get("name", "") for item in data.get("models", []) if isinstance(item, dict)]
    return {
        "configured": True,
        "ok": True,
        "status": "healthy",
        "model": GEMINI_MODEL,
        "available_models": model_names,
        "target_model_visible": any(GEMINI_MODEL in name for name in model_names),
        "message": "Gemini API phản hồi bình thường.",
    }
