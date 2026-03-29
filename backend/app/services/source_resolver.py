from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from urllib.parse import urlsplit, urlunsplit


class SourcePlatform(str, Enum):
    tiktok = "tiktok"
    youtube = "youtube"


class SourceKind(str, Enum):
    tiktok_video = "tiktok_video"
    tiktok_profile = "tiktok_profile"
    tiktok_shortlink = "tiktok_shortlink"
    youtube_short = "youtube_short"
    youtube_shorts_feed = "youtube_shorts_feed"


class SourceResolutionError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedContentSource:
    platform: SourcePlatform
    source_kind: SourceKind
    normalized_url: str
    is_collection: bool


TIKTOK_SHORTLINK_HOSTS = {"vm.tiktok.com", "vt.tiktok.com"}
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
YOUTUBE_SHORTS_FEED_PATTERN = re.compile(r"^/(?:@[^/]+|channel/[^/]+|c/[^/]+|user/[^/]+)/shorts/?$", re.IGNORECASE)
TIKTOK_PROFILE_PATTERN = re.compile(r"^/@[^/]+/?$", re.IGNORECASE)
TIKTOK_VIDEO_PATTERN = re.compile(r"^/@[^/]+/(?:video|photo)/[^/]+/?$", re.IGNORECASE)
YOUTUBE_SHORT_PATTERN = re.compile(r"^/shorts/[^/]+/?$", re.IGNORECASE)


def normalize_source_url(raw_url: str) -> str:
    candidate = (raw_url or "").strip()
    if not candidate:
        raise SourceResolutionError("Vui lòng nhập liên kết nguồn nội dung.")
    if "://" not in candidate and not candidate.startswith("//"):
        candidate = f"https://{candidate}"

    parsed = urlsplit(candidate)
    if not parsed.netloc:
        raise SourceResolutionError("Liên kết nguồn không hợp lệ.")

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    normalized = parsed._replace(
        scheme=parsed.scheme or "https",
        netloc=parsed.netloc.lower(),
        path=path,
        query="",
        fragment="",
    )
    return urlunsplit(normalized)


def _resolve_tiktok_source(host: str, path: str, normalized_url: str) -> ResolvedContentSource:
    lower_host = host.lower()
    lower_path = path.lower() or "/"

    if lower_host in TIKTOK_SHORTLINK_HOSTS or lower_path.startswith("/t/"):
        return ResolvedContentSource(
            platform=SourcePlatform.tiktok,
            source_kind=SourceKind.tiktok_shortlink,
            normalized_url=normalized_url,
            is_collection=False,
        )

    if TIKTOK_VIDEO_PATTERN.match(lower_path):
        return ResolvedContentSource(
            platform=SourcePlatform.tiktok,
            source_kind=SourceKind.tiktok_video,
            normalized_url=normalized_url,
            is_collection=False,
        )

    if TIKTOK_PROFILE_PATTERN.match(lower_path):
        return ResolvedContentSource(
            platform=SourcePlatform.tiktok,
            source_kind=SourceKind.tiktok_profile,
            normalized_url=normalized_url,
            is_collection=True,
        )

    raise SourceResolutionError("Liên kết TikTok chưa được hỗ trợ. Hãy dùng link video, hồ sơ hoặc shortlink TikTok hợp lệ.")


def _resolve_youtube_source(host: str, path: str, normalized_url: str) -> ResolvedContentSource:
    lower_path = path.lower() or "/"

    if YOUTUBE_SHORT_PATTERN.match(lower_path):
        return ResolvedContentSource(
            platform=SourcePlatform.youtube,
            source_kind=SourceKind.youtube_short,
            normalized_url=normalized_url,
            is_collection=False,
        )

    if YOUTUBE_SHORTS_FEED_PATTERN.match(lower_path):
        return ResolvedContentSource(
            platform=SourcePlatform.youtube,
            source_kind=SourceKind.youtube_shorts_feed,
            normalized_url=normalized_url,
            is_collection=True,
        )

    raise SourceResolutionError(
        "Liên kết YouTube chưa nằm trong phạm vi hỗ trợ. Hãy dùng URL Shorts dạng /shorts/... hoặc nguồn Shorts dạng /@handle/shorts."
    )


def resolve_content_source(raw_url: str) -> ResolvedContentSource:
    normalized_url = normalize_source_url(raw_url)
    parsed = urlsplit(normalized_url)
    host = parsed.netloc.lower()
    path = parsed.path or "/"

    if host.endswith("tiktok.com"):
        return _resolve_tiktok_source(host, path, normalized_url)

    if host in YOUTUBE_HOSTS:
        return _resolve_youtube_source(host, path, normalized_url)

    if host in {"youtu.be", "www.youtu.be"}:
        raise SourceResolutionError(
            "Liên kết youtu.be chưa đủ rõ để xác định Shorts. Hãy dùng URL đầy đủ dạng https://www.youtube.com/shorts/..."
        )

    raise SourceResolutionError("Nguồn nội dung chưa được hỗ trợ. Hiện hệ thống chỉ nhận TikTok và YouTube Shorts.")
