from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import tempfile
import uuid
from urllib.parse import urlsplit

import yt_dlp

from app.core.config import settings
from app.services.observability import log_structured

DOWNLOAD_DIR = settings.DOWNLOAD_DIR


@dataclass(frozen=True)
class NormalizedMediaEntry:
    original_id: str
    source_video_url: str
    original_caption: str | None
    title: str | None
    description: str | None
    source_platform: str
    source_kind: str


def extract_metadata(url: str):
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "extract_flat": False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as exc:
        log_structured(
            "crawler",
            "error",
            "Không thể lấy metadata nguồn video.",
            details={"url": url, "error": str(exc)},
        )
        raise


def _iter_info_entries(info) -> list[dict]:
    if not info:
        return []
    if isinstance(info, dict) and "entries" in info:
        return [entry for entry in (info.get("entries") or []) if entry]
    if isinstance(info, dict):
        return [info]
    return []


def _is_youtube_short_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlsplit(url)
    return parsed.netloc.lower() in {"youtube.com", "www.youtube.com", "m.youtube.com"} and parsed.path.lower().startswith("/shorts/")


def _is_tiktok_video_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlsplit(url)
    path = parsed.path.lower()
    return parsed.netloc.lower().endswith("tiktok.com") and ("/video/" in path or "/photo/" in path)


def _build_entry_url(entry: dict, source_platform: str, source_kind_hint: str) -> str | None:
    webpage_url = entry.get("webpage_url")
    if isinstance(webpage_url, str) and webpage_url.startswith("http"):
        return webpage_url

    direct_url = entry.get("url")
    if isinstance(direct_url, str) and direct_url.startswith("http"):
        return direct_url

    entry_id = entry.get("id")
    if not entry_id:
        return None

    if source_platform == "youtube" and source_kind_hint in {"youtube_short", "youtube_shorts_feed"}:
        return f"https://www.youtube.com/shorts/{entry_id}"

    return None


def _normalize_entry(entry: dict, source_platform: str, source_kind_hint: str) -> NormalizedMediaEntry | None:
    entry_url = _build_entry_url(entry, source_platform, source_kind_hint)
    if not entry_url:
        return None

    if source_platform == "youtube":
        if not _is_youtube_short_url(entry_url):
            return None
        source_kind = "youtube_short"
    elif source_platform == "tiktok":
        if _is_tiktok_video_url(entry_url):
            source_kind = "tiktok_video"
        else:
            source_kind = source_kind_hint or "tiktok_video"
    else:
        source_kind = source_kind_hint

    title = (entry.get("title") or "").strip() or None
    description = (entry.get("description") or "").strip() or None
    original_caption = description or title

    return NormalizedMediaEntry(
        original_id=str(entry.get("id") or uuid.uuid4()),
        source_video_url=entry_url,
        original_caption=original_caption,
        title=title,
        description=description,
        source_platform=source_platform,
        source_kind=source_kind,
    )


def extract_source_entries(url: str, source_platform: str, source_kind: str) -> list[NormalizedMediaEntry]:
    raw_info = extract_metadata(url)
    normalized_entries: list[NormalizedMediaEntry] = []
    seen_ids: set[str] = set()

    for entry in _iter_info_entries(raw_info):
        normalized = _normalize_entry(entry, source_platform, source_kind)
        if not normalized:
            continue
        if normalized.original_id in seen_ids:
            continue
        seen_ids.add(normalized.original_id)
        normalized_entries.append(normalized)

    if not normalized_entries and isinstance(raw_info, dict):
        normalized = _normalize_entry(raw_info, source_platform, source_kind)
        if normalized:
            normalized_entries.append(normalized)

    return normalized_entries


def download_video(url: str, filename_prefix: str = "video"):
    Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    video_id = str(uuid.uuid4())
    filename = f"{filename_prefix}_{video_id}.mp4"
    out_path = os.path.join(DOWNLOAD_DIR, filename)

    ydl_opts = {
        "format": "best[vcodec^=h264]/best[vcodec^=avc]/best",
        "outtmpl": out_path,
        "quiet": True,
        "no_warnings": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return out_path, video_id
    except Exception as exc:
        log_structured(
            "crawler",
            "error",
            "Không thể tải video từ nguồn.",
            details={"url": url, "filename_prefix": filename_prefix, "error": str(exc)},
        )
        return None, None


def get_downloader_health() -> dict:
    download_dir = Path(DOWNLOAD_DIR)
    try:
        download_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=download_dir, delete=True):
            pass
        return {
            "ok": True,
            "configured": True,
            "download_dir": str(download_dir),
            "download_dir_exists": download_dir.exists(),
            "download_dir_writable": True,
            "yt_dlp_version": getattr(getattr(yt_dlp, "version", None), "__version__", None),
            "message": "yt-dlp sẵn sàng và thư mục tải xuống có thể ghi.",
        }
    except Exception as exc:
        return {
            "ok": False,
            "configured": True,
            "download_dir": str(download_dir),
            "download_dir_exists": download_dir.exists(),
            "download_dir_writable": False,
            "yt_dlp_version": getattr(getattr(yt_dlp, "version", None), "__version__", None),
            "message": f"yt-dlp hoặc thư mục tải xuống chưa sẵn sàng: {exc}",
        }
