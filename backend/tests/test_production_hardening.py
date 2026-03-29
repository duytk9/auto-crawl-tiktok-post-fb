from datetime import timedelta

from app.models.models import (
    Campaign,
    CampaignStatus,
    FacebookPage,
    InteractionLog,
    InteractionStatus,
    TaskQueue,
    TaskStatus,
    Video,
    VideoStatus,
    WorkerHeartbeat,
)
from app.core.time import utc_now
from app.services.security import encrypt_secret
from app.services.task_queue import TASK_TYPE_CAMPAIGN_SYNC, TASK_TYPE_COMMENT_REPLY, claim_next_task, enqueue_task
from app.services.ytdlp_crawler import NormalizedMediaEntry
from app.worker import healthcheck as worker_healthcheck
from app.worker.tasks import process_task_queue


def test_claim_next_task_recovers_stale_processing_task(db_session):
    stale_task = TaskQueue(
        task_type=TASK_TYPE_CAMPAIGN_SYNC,
        entity_type="campaign",
        entity_id="campaign-stale",
        payload={"campaign_id": "campaign-stale", "source_url": "https://example.com"},
        status=TaskStatus.processing,
        attempts=1,
        max_attempts=3,
        locked_at=utc_now() - timedelta(minutes=10),
        locked_by="worker-old@test",
        started_at=utc_now() - timedelta(minutes=10),
        available_at=utc_now() - timedelta(minutes=10),
    )
    db_session.add(stale_task)
    db_session.commit()
    db_session.refresh(stale_task)

    claimed = claim_next_task(db_session, "worker-new@test")
    assert claimed is not None
    assert str(claimed.id) == str(stale_task.id)
    assert claimed.status == TaskStatus.processing
    assert claimed.locked_by == "worker-new@test"
    assert claimed.attempts == 2

    db_session.expire_all()
    refreshed = db_session.query(TaskQueue).filter(TaskQueue.id == stale_task.id).first()
    assert refreshed.last_error is None


def test_worker_healthcheck_reflects_fresh_and_stale_heartbeat(db_session, monkeypatch):
    worker = WorkerHeartbeat(
        worker_name="worker-health@test",
        app_role="worker",
        hostname="localhost",
        status="idle",
        last_seen_at=utc_now(),
    )
    db_session.add(worker)
    db_session.commit()

    monkeypatch.setattr(worker_healthcheck, "WORKER_NAME", "worker-health@test")
    assert worker_healthcheck.main() == 0

    worker.last_seen_at = utc_now() - timedelta(minutes=10)
    db_session.commit()
    assert worker_healthcheck.main() == 1


def test_system_health_reports_dependency_breakdown(client, auth_headers, monkeypatch):
    from app.api import system as system_api

    monkeypatch.setattr(
        system_api,
        "get_downloader_health",
        lambda: {
            "ok": True,
            "configured": True,
            "download_dir": "C:/tmp/downloads",
            "download_dir_exists": True,
            "download_dir_writable": True,
            "yt_dlp_version": "2026.01.01",
            "message": "yt-dlp sẵn sàng.",
        },
    )
    monkeypatch.setattr(
        system_api,
        "check_runtime_env_health",
        lambda: {
            "ok": True,
            "file_exists": True,
            "path": "C:/tmp/runtime.env",
            "parent_exists": True,
            "message": "runtime.env sẵn sàng.",
        },
    )
    monkeypatch.setattr(
        system_api,
        "check_facebook_dependency",
        lambda db: {
            "configured": True,
            "ok": True,
            "status": "healthy",
            "message": "Facebook Graph sẵn sàng.",
            "page_id": "page-health",
        },
    )
    monkeypatch.setattr(
        system_api,
        "check_gemini_dependency",
        lambda db: {
            "configured": True,
            "ok": True,
            "status": "healthy",
            "model": "gemini-2.5-flash",
            "message": "Gemini sẵn sàng.",
        },
    )

    response = client.get("/system/health", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["dependencies"]["facebook_graph"]["status"] == "healthy"
    assert payload["dependencies"]["gemini"]["status"] == "healthy"
    assert payload["dependencies"]["yt_dlp"]["ok"] is True
    assert payload["config"]["task_lock_stale_seconds"] > 0


def test_comment_webhook_worker_smoke_flow(client, db_session, monkeypatch):
    page = FacebookPage(
        page_id="page-comment-smoke",
        page_name="Trang comment smoke",
        long_lived_access_token=encrypt_secret("page-token-comment-smoke"),
        comment_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-comment-smoke",
                    "changes": [
                        {
                            "field": "feed",
                            "value": {
                                "item": "comment",
                                "verb": "add",
                                "comment_id": "comment-smoke-1",
                                "post_id": "post-smoke-1",
                                "message": "Video này hay quá",
                                "from": {"id": "user-comment-1"},
                            },
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    saved_log = db_session.query(InteractionLog).filter(InteractionLog.comment_id == "comment-smoke-1").first()
    assert saved_log is not None
    assert saved_log.status == InteractionStatus.pending

    pending_task = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_COMMENT_REPLY).first()
    assert pending_task is not None

    monkeypatch.setattr(
        "app.services.campaign_jobs.generate_reply",
        lambda user_message, **kwargs: "Cảm ơn bạn đã ủng hộ nhé!",
    )
    monkeypatch.setattr(
        "app.services.campaign_jobs.reply_to_comment",
        lambda comment_id, message, access_token: {"id": "reply-comment-1"},
    )

    processed = process_task_queue("worker-comment@test")
    assert processed == 1

    db_session.expire_all()
    saved_log = db_session.query(InteractionLog).filter(InteractionLog.comment_id == "comment-smoke-1").first()
    assert saved_log.status == InteractionStatus.replied
    assert saved_log.ai_reply == "Cảm ơn bạn đã ủng hộ nhé!"


def test_campaign_sync_worker_smoke_flow(db_session, monkeypatch):
    campaign = Campaign(
        name="YouTube Shorts smoke",
        source_url="https://www.youtube.com/shorts/abc123",
        source_platform="youtube",
        source_kind="youtube_short",
        status=CampaignStatus.active,
        schedule_interval=15,
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    enqueue_task(
        db_session,
        task_type=TASK_TYPE_CAMPAIGN_SYNC,
        entity_type="campaign",
        entity_id=str(campaign.id),
        payload={
            "campaign_id": str(campaign.id),
            "source_url": campaign.source_url,
            "source_platform": campaign.source_platform,
            "source_kind": campaign.source_kind,
        },
        priority=10,
    )

    monkeypatch.setattr(
        "app.services.campaign_jobs.extract_source_entries",
        lambda url, source_platform, source_kind: [
            NormalizedMediaEntry(
                original_id="short-1",
                source_video_url="https://www.youtube.com/shorts/short-1",
                original_caption="Caption YouTube Shorts",
                title="Short title",
                description="Caption YouTube Shorts",
                source_platform="youtube",
                source_kind="youtube_short",
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.campaign_jobs.download_video",
        lambda url, filename_prefix="video": ("C:/tmp/youtube_short_smoke.mp4", "download-short-1"),
    )

    processed = process_task_queue("worker-sync@test")
    assert processed == 1

    db_session.expire_all()
    saved_video = db_session.query(Video).filter(Video.campaign_id == campaign.id).first()
    assert saved_video is not None
    assert saved_video.status == VideoStatus.ready
    assert saved_video.source_platform == "youtube"
    assert saved_video.source_kind == "youtube_short"
