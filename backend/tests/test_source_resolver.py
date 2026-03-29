import pytest
from datetime import timedelta

from app.core.time import utc_now
from app.models.models import Campaign, CampaignStatus, TaskQueue, Video, VideoStatus
from app.services.campaign_jobs import sync_campaign_content
from app.services.source_resolver import SourceResolutionError, resolve_content_source
from app.services.ytdlp_crawler import extract_source_entries


@pytest.mark.parametrize(
    ("url", "platform", "source_kind", "is_collection", "normalized_url"),
    [
        (
            "https://www.tiktok.com/@demo/video/1234567890?is_copy_url=1",
            "tiktok",
            "tiktok_video",
            False,
            "https://www.tiktok.com/@demo/video/1234567890",
        ),
        (
            "https://www.tiktok.com/@demo/",
            "tiktok",
            "tiktok_profile",
            True,
            "https://www.tiktok.com/@demo",
        ),
        (
            "https://vt.tiktok.com/ZSh123abc/",
            "tiktok",
            "tiktok_shortlink",
            False,
            "https://vt.tiktok.com/ZSh123abc",
        ),
        (
            "https://www.youtube.com/shorts/abc123?feature=share",
            "youtube",
            "youtube_short",
            False,
            "https://www.youtube.com/shorts/abc123",
        ),
        (
            "https://www.youtube.com/@creator/shorts",
            "youtube",
            "youtube_shorts_feed",
            True,
            "https://www.youtube.com/@creator/shorts",
        ),
    ],
)
def test_resolve_content_source_supported_urls(url, platform, source_kind, is_collection, normalized_url):
    resolved = resolve_content_source(url)
    assert resolved.platform.value == platform
    assert resolved.source_kind.value == source_kind
    assert resolved.is_collection is is_collection
    assert resolved.normalized_url == normalized_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=abc123",
        "https://youtu.be/abc123",
        "https://example.com/video/123",
    ],
)
def test_resolve_content_source_rejects_unsupported_urls(url):
    with pytest.raises(SourceResolutionError):
        resolve_content_source(url)


def test_create_campaign_detects_youtube_shorts_metadata(client, auth_headers, db_session):
    response = client.post(
        "/campaigns/",
        headers=auth_headers,
        json={
            "name": "YouTube Shorts test",
            "source_url": "https://www.youtube.com/shorts/abc123?feature=share",
            "auto_post": False,
            "schedule_interval": 30,
        },
    )

    assert response.status_code == 200
    campaign = db_session.query(Campaign).one()
    assert campaign.source_url == "https://www.youtube.com/shorts/abc123"
    assert campaign.source_platform == "youtube"
    assert campaign.source_kind == "youtube_short"

    task = db_session.query(TaskQueue).one()
    assert task.payload["source_platform"] == "youtube"
    assert task.payload["source_kind"] == "youtube_short"


def test_sync_campaign_backfills_missing_source_metadata(client, auth_headers, db_session):
    campaign = Campaign(
        name="Legacy TikTok",
        source_url="https://www.tiktok.com/@legacy/video/987654321",
        source_platform=None,
        source_kind=None,
        status=CampaignStatus.active,
        last_sync_status="idle",
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    response = client.post(f"/campaigns/{campaign.id}/sync", headers=auth_headers)

    assert response.status_code == 200
    db_session.refresh(campaign)
    assert campaign.source_platform == "tiktok"
    assert campaign.source_kind == "tiktok_video"

    queued_task = (
        db_session.query(TaskQueue)
        .filter(TaskQueue.entity_id == str(campaign.id))
        .order_by(TaskQueue.created_at.desc())
        .first()
    )
    assert queued_task is not None
    assert queued_task.payload["source_platform"] == "tiktok"
    assert queued_task.payload["source_kind"] == "tiktok_video"


def test_extract_source_entries_filters_to_youtube_shorts(monkeypatch):
    def fake_extract_metadata(_url):
        return {
            "entries": [
                {
                    "id": "short-1",
                    "webpage_url": "https://www.youtube.com/shorts/short-1",
                    "title": "Short 1",
                    "description": "Mo ta short 1",
                },
                {
                    "id": "watch-2",
                    "webpage_url": "https://www.youtube.com/watch?v=watch-2",
                    "title": "Video dai",
                    "description": "Khong phai short",
                },
                {
                    "id": "short-3",
                    "title": "Short 3",
                    "description": "",
                },
            ]
        }

    monkeypatch.setattr("app.services.ytdlp_crawler.extract_metadata", fake_extract_metadata)

    entries = extract_source_entries(
        "https://www.youtube.com/@creator/shorts",
        source_platform="youtube",
        source_kind="youtube_shorts_feed",
    )

    assert [entry.original_id for entry in entries] == ["short-1", "short-3"]
    assert all(entry.source_platform == "youtube" for entry in entries)
    assert all(entry.source_kind == "youtube_short" for entry in entries)
    assert entries[1].source_video_url == "https://www.youtube.com/shorts/short-3"


def test_sync_campaign_content_uses_normalized_youtube_entries(monkeypatch, db_session):
    campaign = Campaign(
        name="YouTube feed campaign",
        source_url="https://www.youtube.com/@creator/shorts",
        source_platform="youtube",
        source_kind="youtube_shorts_feed",
        status=CampaignStatus.active,
        schedule_interval=15,
        last_sync_status="idle",
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    def fake_extract_source_entries(_url, source_platform, source_kind):
        assert source_platform == "youtube"
        assert source_kind == "youtube_shorts_feed"
        from app.services.ytdlp_crawler import NormalizedMediaEntry

        return [
            NormalizedMediaEntry(
                original_id="short-a",
                source_video_url="https://www.youtube.com/shorts/short-a",
                original_caption="Caption A",
                title="Short A",
                description="Caption A",
                source_platform="youtube",
                source_kind="youtube_short",
            ),
            NormalizedMediaEntry(
                original_id="short-b",
                source_video_url="https://www.youtube.com/shorts/short-b",
                original_caption="Caption B",
                title="Short B",
                description="Caption B",
                source_platform="youtube",
                source_kind="youtube_short",
            ),
        ]

    def fake_download_video(url, filename_prefix):
        return (f"/tmp/{filename_prefix}-{url.rsplit('/', 1)[-1]}.mp4", "download-id")

    monkeypatch.setattr("app.services.campaign_jobs.extract_source_entries", fake_extract_source_entries)
    monkeypatch.setattr("app.services.campaign_jobs.download_video", fake_download_video)

    result = sync_campaign_content(
        str(campaign.id),
        campaign.source_url,
        allow_paused=False,
        source_platform=campaign.source_platform,
        source_kind=campaign.source_kind,
    )

    assert result["ok"] is True
    assert result["videos_added"] == 2

    videos = db_session.query(Video).filter(Video.campaign_id == campaign.id).order_by(Video.original_id.asc()).all()
    assert [video.original_id for video in videos] == ["short-a", "short-b"]
    assert all(video.source_platform == "youtube" for video in videos)
    assert all(video.source_kind == "youtube_short" for video in videos)
    assert all(video.status == VideoStatus.ready for video in videos)
    assert videos[0].file_path.endswith("youtube_short-short-a.mp4")


def test_sync_campaign_content_fails_when_youtube_source_has_no_valid_shorts(monkeypatch, db_session):
    campaign = Campaign(
        name="Empty Shorts feed",
        source_url="https://www.youtube.com/@creator/shorts",
        source_platform="youtube",
        source_kind="youtube_shorts_feed",
        status=CampaignStatus.active,
        last_sync_status="idle",
    )
    db_session.add(campaign)
    db_session.commit()
    db_session.refresh(campaign)

    monkeypatch.setattr("app.services.campaign_jobs.extract_source_entries", lambda *_args, **_kwargs: [])

    with pytest.raises(ValueError, match="không trả về video hợp lệ"):
        sync_campaign_content(
            str(campaign.id),
            campaign.source_url,
            allow_paused=False,
            source_platform=campaign.source_platform,
            source_kind=campaign.source_kind,
        )


def test_campaign_stats_include_source_breakdown(client, auth_headers, db_session):
    tiktok_campaign = Campaign(
        name="TikTok campaign",
        source_url="https://www.tiktok.com/@demo",
        source_platform="tiktok",
        source_kind="tiktok_profile",
        status=CampaignStatus.active,
    )
    youtube_campaign = Campaign(
        name="YouTube Shorts campaign",
        source_url="https://www.youtube.com/@creator/shorts",
        source_platform="youtube",
        source_kind="youtube_shorts_feed",
        status=CampaignStatus.active,
    )
    db_session.add_all([tiktok_campaign, youtube_campaign])
    db_session.commit()
    db_session.refresh(tiktok_campaign)
    db_session.refresh(youtube_campaign)

    db_session.add_all(
        [
            Video(
                campaign_id=tiktok_campaign.id,
                original_id="tt-ready",
                source_video_url="https://www.tiktok.com/@demo/video/tt-ready",
                original_caption="TikTok ready",
                status=VideoStatus.ready,
                publish_time=utc_now(),
            ),
            Video(
                campaign_id=youtube_campaign.id,
                original_id="yt-ready",
                source_video_url="https://www.youtube.com/shorts/yt-ready",
                original_caption="Short ready",
                status=VideoStatus.ready,
                source_platform="youtube",
                source_kind="youtube_short",
                publish_time=utc_now(),
            ),
            Video(
                campaign_id=youtube_campaign.id,
                original_id="yt-failed",
                source_video_url="https://www.youtube.com/shorts/yt-failed",
                original_caption="Short failed",
                status=VideoStatus.failed,
                source_platform="youtube",
                source_kind="youtube_short",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/campaigns/stats", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["by_source"]["tiktok"]["campaigns"] == 1
    assert payload["by_source"]["tiktok"]["videos"] == 1
    assert payload["by_source"]["tiktok"]["ready"] == 1
    assert payload["by_source"]["youtube"]["campaigns"] == 1
    assert payload["by_source"]["youtube"]["videos"] == 2
    assert payload["by_source"]["youtube"]["ready"] == 1


def test_get_videos_can_filter_by_source_platform(client, auth_headers, db_session):
    tiktok_campaign = Campaign(
        name="TikTok campaign",
        source_url="https://www.tiktok.com/@demo",
        source_platform="tiktok",
        source_kind="tiktok_profile",
        status=CampaignStatus.active,
    )
    youtube_campaign = Campaign(
        name="YouTube Shorts campaign",
        source_url="https://www.youtube.com/@creator/shorts",
        source_platform="youtube",
        source_kind="youtube_shorts_feed",
        status=CampaignStatus.active,
    )
    db_session.add_all([tiktok_campaign, youtube_campaign])
    db_session.commit()
    db_session.refresh(tiktok_campaign)
    db_session.refresh(youtube_campaign)

    db_session.add_all(
        [
            Video(
                campaign_id=tiktok_campaign.id,
                original_id="tt-ready",
                source_video_url="https://www.tiktok.com/@demo/video/tt-ready",
                original_caption="TikTok ready",
                status=VideoStatus.ready,
                publish_time=utc_now(),
            ),
            Video(
                campaign_id=youtube_campaign.id,
                original_id="yt-ready",
                source_video_url="https://www.youtube.com/shorts/yt-ready",
                original_caption="Short ready",
                status=VideoStatus.ready,
                source_platform="youtube",
                source_kind="youtube_short",
                publish_time=utc_now(),
            ),
            Video(
                campaign_id=youtube_campaign.id,
                original_id="yt-posted",
                source_video_url="https://www.youtube.com/shorts/yt-posted",
                original_caption="Short posted",
                status=VideoStatus.posted,
                source_platform="youtube",
                source_kind="youtube_short",
            ),
        ]
    )
    db_session.commit()

    response = client.get("/campaigns/videos?source_platform=youtube", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert {video["original_id"] for video in payload["videos"]} == {"yt-ready", "yt-posted"}
    assert all(video["source_platform"] == "youtube" for video in payload["videos"])


def test_campaign_stats_include_source_trends(client, auth_headers, db_session):
    now = utc_now()
    tiktok_campaign = Campaign(
        name="TikTok campaign",
        source_url="https://www.tiktok.com/@demo",
        source_platform="tiktok",
        source_kind="tiktok_profile",
        status=CampaignStatus.active,
    )
    youtube_campaign = Campaign(
        name="YouTube Shorts campaign",
        source_url="https://www.youtube.com/@creator/shorts",
        source_platform="youtube",
        source_kind="youtube_shorts_feed",
        status=CampaignStatus.active,
    )
    db_session.add_all([tiktok_campaign, youtube_campaign])
    db_session.commit()
    db_session.refresh(tiktok_campaign)
    db_session.refresh(youtube_campaign)

    db_session.add_all(
        [
            Video(
                campaign_id=tiktok_campaign.id,
                original_id="tt-ready-today",
                source_video_url="https://www.tiktok.com/@demo/video/tt-ready-today",
                original_caption="TikTok ready today",
                status=VideoStatus.ready,
                publish_time=now,
            ),
            Video(
                campaign_id=tiktok_campaign.id,
                original_id="tt-posted-yesterday",
                source_video_url="https://www.tiktok.com/@demo/video/tt-posted-yesterday",
                original_caption="TikTok posted yesterday",
                status=VideoStatus.posted,
                updated_at=now - timedelta(days=1),
            ),
            Video(
                campaign_id=youtube_campaign.id,
                original_id="yt-failed-two-days",
                source_video_url="https://www.youtube.com/shorts/yt-failed-two-days",
                original_caption="YouTube failed",
                status=VideoStatus.failed,
                source_platform="youtube",
                source_kind="youtube_short",
                updated_at=now - timedelta(days=2),
            ),
        ]
    )
    db_session.commit()

    response = client.get("/campaigns/stats", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    labels = payload["source_trends"]["labels"]
    tiktok_ready = payload["source_trends"]["series"]["tiktok"]["ready"]
    tiktok_posted = payload["source_trends"]["series"]["tiktok"]["posted"]
    youtube_failed = payload["source_trends"]["series"]["youtube"]["failed"]

    assert len(labels) == 7
    assert tiktok_ready[-1] == 1
    assert tiktok_posted[-2] == 1
    assert youtube_failed[-3] == 1
