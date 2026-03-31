from __future__ import annotations

from datetime import datetime
import os
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Campaign, Video
from app.services.source_resolver import resolve_content_source


def parse_uuid_or_400(raw_id: str, label: str):
    try:
        return uuid.UUID(raw_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{label} không hợp lệ.") from exc


def set_campaign_sync_state(
    campaign: Campaign,
    status: str,
    error: str | None = None,
    finished_at: datetime | None = None,
):
    campaign.last_sync_status = status
    campaign.last_sync_error = error[:1000] if error else None
    if finished_at:
        campaign.last_synced_at = finished_at


def safe_remove_file(path: str | None):
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def ensure_campaign_source_details(campaign: Campaign):
    resolved = resolve_content_source(campaign.source_url)
    changed = False
    if campaign.source_url != resolved.normalized_url:
        campaign.source_url = resolved.normalized_url
        changed = True
    if campaign.source_platform != resolved.platform.value:
        campaign.source_platform = resolved.platform.value
        changed = True
    if campaign.source_kind != resolved.source_kind.value:
        campaign.source_kind = resolved.source_kind.value
        changed = True
    return resolved, changed


def get_campaign_or_404(db: Session, campaign_id: str):
    campaign_uuid = parse_uuid_or_400(campaign_id, "Mã chiến dịch")
    campaign = db.query(Campaign).filter(Campaign.id == campaign_uuid).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Không tìm thấy chiến dịch.")
    return campaign


def get_video_or_404(db: Session, video_id: str):
    video_uuid = parse_uuid_or_400(video_id, "Mã video")
    video = db.query(Video).filter(Video.id == video_uuid).first()
    if not video:
        raise HTTPException(status_code=404, detail="Không tìm thấy video.")
    return video
