from __future__ import annotations

import time

import requests
from requests import Response
from requests.exceptions import RequestException

from app.core.config import settings
from app.services.observability import log_structured

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def compute_retry_delay(
    attempt: int,
    *,
    base_seconds: int,
    max_seconds: int,
) -> int:
    safe_attempt = max(1, attempt)
    return min(max_seconds, base_seconds * (2 ** (safe_attempt - 1)))


def request_with_retries(
    method: str,
    url: str,
    *,
    timeout: int | None = None,
    max_attempts: int | None = None,
    retryable_status_codes: set[int] | None = None,
    scope: str = "http",
    operation: str | None = None,
    **kwargs,
) -> Response:
    attempts = max_attempts or settings.HTTP_RETRY_ATTEMPTS
    request_timeout = timeout or settings.EXTERNAL_HTTP_TIMEOUT
    statuses = retryable_status_codes or RETRYABLE_STATUS_CODES
    operation_name = operation or f"{method.upper()} {url}"

    last_response: Response | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.request(method, url, timeout=request_timeout, **kwargs)
            last_response = response
            if response.status_code not in statuses or attempt == attempts:
                return response

            delay_seconds = compute_retry_delay(
                attempt,
                base_seconds=settings.HTTP_RETRY_BASE_SECONDS,
                max_seconds=settings.HTTP_RETRY_MAX_SECONDS,
            )
            log_structured(
                scope,
                "warning",
                "Yêu cầu HTTP trả về mã lỗi có thể thử lại.",
                details={
                    "operation": operation_name,
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "status_code": response.status_code,
                    "retry_in_seconds": delay_seconds,
                },
            )
            time.sleep(delay_seconds)
        except RequestException as exc:
            if attempt == attempts:
                raise

            delay_seconds = compute_retry_delay(
                attempt,
                base_seconds=settings.HTTP_RETRY_BASE_SECONDS,
                max_seconds=settings.HTTP_RETRY_MAX_SECONDS,
            )
            log_structured(
                scope,
                "warning",
                "Yêu cầu HTTP lỗi mạng, đang chuẩn bị thử lại.",
                details={
                    "operation": operation_name,
                    "attempt": attempt,
                    "max_attempts": attempts,
                    "error": str(exc),
                    "retry_in_seconds": delay_seconds,
                },
            )
            time.sleep(delay_seconds)

    if last_response is not None:
        return last_response
    raise RuntimeError(f"Yêu cầu HTTP thất bại mà không có phản hồi: {operation_name}")
