from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta

from sqlalchemy import func, literal
from sqlalchemy.orm import Session

from app.core.time import utc_today
from app.models import Campaign, FacebookPage, Video, VideoStatus


def serialize_datetime(value):
    return value.isoformat() if value else None


def normalize_status(value):
    return value.value if hasattr(value, "value") else value


def build_campaign_summary_map(db: Session):
    summary_map = defaultdict(
        lambda: {"total": 0, "pending": 0, "downloading": 0, "ready": 0, "posted": 0, "failed": 0}
    )
    rows = (
        db.query(Video.campaign_id, Video.status, func.count(Video.id))
        .group_by(Video.campaign_id, Video.status)
        .all()
    )
    for campaign_id, status, count in rows:
        key = normalize_status(status)
        summary_map[campaign_id]["total"] += count
        summary_map[campaign_id][key] = count
    return summary_map


def build_page_name_map(db: Session):
    return {page.page_id: page.page_name for page in db.query(FacebookPage).all()}


def serialize_campaign(campaign: Campaign, summary_map, page_name_map):
    video_counts = summary_map.get(
        campaign.id,
        {"total": 0, "pending": 0, "downloading": 0, "ready": 0, "posted": 0, "failed": 0},
    )
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "source_url": campaign.source_url,
        "source_platform": campaign.source_platform,
        "source_kind": campaign.source_kind,
        "status": normalize_status(campaign.status),
        "auto_post": campaign.auto_post,
        "target_page_id": campaign.target_page_id,
        "target_page_name": page_name_map.get(campaign.target_page_id),
        "schedule_interval": campaign.schedule_interval,
        "last_synced_at": serialize_datetime(campaign.last_synced_at),
        "last_sync_status": campaign.last_sync_status or "idle",
        "last_sync_error": campaign.last_sync_error,
        "created_at": serialize_datetime(campaign.created_at),
        "updated_at": serialize_datetime(campaign.updated_at),
        "video_counts": video_counts,
    }


def serialize_video(video: Video, page_name_map=None):
    campaign = video.campaign
    page_name = None
    campaign_name = None
    target_page_id = None
    campaign_status = None
    if campaign:
        campaign_name = campaign.name
        target_page_id = campaign.target_page_id
        campaign_status = normalize_status(campaign.status)
        if page_name_map and target_page_id:
            page_name = page_name_map.get(target_page_id)

    return {
        "id": str(video.id),
        "campaign_id": str(video.campaign_id),
        "campaign_name": campaign_name,
        "campaign_status": campaign_status,
        "source_platform": video.source_platform or (campaign.source_platform if campaign else None),
        "source_kind": video.source_kind or (campaign.source_kind if campaign else None),
        "target_page_id": target_page_id,
        "target_page_name": page_name,
        "original_id": video.original_id,
        "source_video_url": video.source_video_url,
        "file_path": video.file_path,
        "original_caption": video.original_caption,
        "ai_caption": video.ai_caption,
        "status": normalize_status(video.status),
        "publish_time": serialize_datetime(video.publish_time),
        "fb_post_id": video.fb_post_id,
        "last_error": video.last_error,
        "retry_count": video.retry_count or 0,
        "created_at": serialize_datetime(video.created_at),
        "updated_at": serialize_datetime(video.updated_at),
    }


def build_source_stats(db: Session):
    summary = {
        "tiktok": {"campaigns": 0, "videos": 0, "ready": 0},
        "youtube": {"campaigns": 0, "videos": 0, "ready": 0},
        "unknown": {"campaigns": 0, "videos": 0, "ready": 0},
    }

    campaign_platform = func.coalesce(Campaign.source_platform, literal("unknown"))
    campaign_rows = (
        db.query(campaign_platform.label("platform"), func.count(Campaign.id))
        .group_by(campaign_platform)
        .all()
    )
    for platform, count in campaign_rows:
        key = platform if platform in summary else "unknown"
        summary[key]["campaigns"] = count

    video_platform = func.coalesce(Video.source_platform, Campaign.source_platform, literal("unknown"))
    video_rows = (
        db.query(video_platform.label("platform"), func.count(Video.id))
        .outerjoin(Campaign, Video.campaign_id == Campaign.id)
        .group_by(video_platform)
        .all()
    )
    for platform, count in video_rows:
        key = platform if platform in summary else "unknown"
        summary[key]["videos"] = count

    ready_rows = (
        db.query(video_platform.label("platform"), func.count(Video.id))
        .outerjoin(Campaign, Video.campaign_id == Campaign.id)
        .filter(Video.status == VideoStatus.ready)
        .group_by(video_platform)
        .all()
    )
    for platform, count in ready_rows:
        key = platform if platform in summary else "unknown"
        summary[key]["ready"] = count

    return summary


def build_source_trends(db: Session, days: int = 7):
    today = utc_today()
    labels = [
        (today - timedelta(days=offset)).isoformat()
        for offset in reversed(range(days))
    ]
    label_index = {label: idx for idx, label in enumerate(labels)}
    series = {
        "tiktok": {"ready": [0] * days, "posted": [0] * days, "failed": [0] * days},
        "youtube": {"ready": [0] * days, "posted": [0] * days, "failed": [0] * days},
        "unknown": {"ready": [0] * days, "posted": [0] * days, "failed": [0] * days},
    }

    start_date = today - timedelta(days=days - 1)
    start_datetime = datetime.combine(start_date, time.min)
    video_platform = func.coalesce(Video.source_platform, Campaign.source_platform, literal("unknown"))
    status_specs = {
        "ready": (VideoStatus.ready, Video.publish_time),
        "posted": (VideoStatus.posted, Video.updated_at),
        "failed": (VideoStatus.failed, Video.updated_at),
    }

    for status_key, (target_status, timestamp_column) in status_specs.items():
        rows = (
            db.query(
                video_platform.label("platform"),
                func.date(timestamp_column).label("day"),
                func.count(Video.id),
            )
            .outerjoin(Campaign, Video.campaign_id == Campaign.id)
            .filter(
                Video.status == target_status,
                timestamp_column.is_not(None),
                timestamp_column >= start_datetime,
            )
            .group_by(video_platform, func.date(timestamp_column))
            .all()
        )
        for platform, raw_day, count in rows:
            day_key = raw_day.isoformat() if hasattr(raw_day, "isoformat") else str(raw_day)
            if day_key not in label_index:
                continue
            source_key = platform if platform in series else "unknown"
            series[source_key][status_key][label_index[day_key]] = count

    return {"labels": labels, "series": series}
