from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel

from app.services.campaign_jobs import reply_to_comment_job, reply_to_message_job, retry_video_download, sync_campaign_content
from app.services.task_types import (
    TASK_TYPE_CAMPAIGN_SYNC,
    TASK_TYPE_COMMENT_REPLY,
    TASK_TYPE_MESSAGE_REPLY,
    TASK_TYPE_VIDEO_RETRY,
)


class CampaignSyncPayload(BaseModel):
    campaign_id: str
    source_url: str = ""
    allow_paused: bool = False
    source_platform: str | None = None
    source_kind: str | None = None


class VideoRetryPayload(BaseModel):
    video_id: str


class CommentReplyPayload(BaseModel):
    interaction_log_id: str


class MessageReplyPayload(BaseModel):
    message_log_id: str


@dataclass(frozen=True)
class TaskDefinition:
    payload_model: type[BaseModel]
    handler: Callable[[BaseModel], dict]


def _run_campaign_sync(payload: CampaignSyncPayload) -> dict:
    return sync_campaign_content(
        payload.campaign_id,
        payload.source_url,
        payload.allow_paused,
        payload.source_platform,
        payload.source_kind,
    )


def _run_video_retry(payload: VideoRetryPayload) -> dict:
    return retry_video_download(payload.video_id)


def _run_comment_reply(payload: CommentReplyPayload) -> dict:
    return reply_to_comment_job(payload.interaction_log_id)


def _run_message_reply(payload: MessageReplyPayload) -> dict:
    return reply_to_message_job(payload.message_log_id)


TASK_REGISTRY: dict[str, TaskDefinition] = {
    TASK_TYPE_CAMPAIGN_SYNC: TaskDefinition(CampaignSyncPayload, _run_campaign_sync),
    TASK_TYPE_VIDEO_RETRY: TaskDefinition(VideoRetryPayload, _run_video_retry),
    TASK_TYPE_COMMENT_REPLY: TaskDefinition(CommentReplyPayload, _run_comment_reply),
    TASK_TYPE_MESSAGE_REPLY: TaskDefinition(MessageReplyPayload, _run_message_reply),
}


def run_task(task) -> dict:
    definition = TASK_REGISTRY.get(task.task_type)
    if not definition:
        raise ValueError(f"Loại tác vụ không được hỗ trợ: {task.task_type}")

    payload = definition.payload_model.model_validate(task.payload or {})
    return definition.handler(payload)
