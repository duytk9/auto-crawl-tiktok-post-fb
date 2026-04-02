from app.models.models import (
    AffiliateCommentStatus,
    Campaign,
    CampaignStatus,
    FacebookPage,
    TaskQueue,
    TaskStatus,
    Video,
    VideoStatus,
)
from app.services.campaign_jobs import build_affiliate_comment_text, has_affiliate_comment_options
from app.services.campaign_jobs import post_affiliate_comment_job
from app.services.security import encrypt_secret
from app.services.task_queue import TASK_TYPE_AFFILIATE_COMMENT


def _seed_page_campaign_video(db_session, *, affiliate_enabled=True):
    page = FacebookPage(
        page_id="page-aff-1",
        page_name="Trang Affiliate",
        long_lived_access_token=encrypt_secret("page-token-affiliate"),
        affiliate_comment_enabled=affiliate_enabled,
        affiliate_comment_text="Link sản phẩm mình để ở đây nhé.",
        affiliate_link_url="https://example.com/aff",
        affiliate_comment_delay_seconds=60,
    )
    campaign = Campaign(
        name="Campaign Affiliate",
        source_url="https://www.tiktok.com/@demo/video/123",
        source_platform="tiktok",
        source_kind="tiktok_video",
        status=CampaignStatus.active,
        auto_post=True,
        target_page_id=page.page_id,
        schedule_interval=30,
    )
    video = Video(
        campaign=campaign,
        original_id="video-aff-1",
        source_platform="tiktok",
        source_kind="tiktok_video",
        source_video_url="https://www.tiktok.com/@demo/video/123",
        status=VideoStatus.posted,
        fb_video_id="fb-video-1",
        fb_post_id="fb-post-1",
        affiliate_comment_status=AffiliateCommentStatus.operator_required,
        affiliate_comment_text="Link sản phẩm mình để ở đây nhé.\nhttps://example.com/aff",
        affiliate_comment_error="Comment trước đó thất bại.",
    )
    db_session.add_all([page, campaign, video])
    db_session.commit()
    db_session.refresh(page)
    db_session.refresh(campaign)
    db_session.refresh(video)
    return page, campaign, video


def test_update_facebook_automation_saves_affiliate_settings(client, auth_headers, db_session):
    page = FacebookPage(
        page_id="page-aff-config",
        page_name="Trang cấu hình aff",
        long_lived_access_token=encrypt_secret("page-token-config"),
    )
    db_session.add(page)
    db_session.commit()

    response = client.patch(
        f"/facebook/config/{page.page_id}/automation",
        headers=auth_headers,
        json={
            "comment_auto_reply_enabled": True,
            "comment_ai_prompt": "",
            "message_auto_reply_enabled": False,
            "message_ai_prompt": "",
            "message_reply_schedule_enabled": False,
            "message_reply_start_time": "08:00",
            "message_reply_end_time": "22:00",
            "message_reply_cooldown_minutes": 0,
            "affiliate_comment_enabled": True,
            "affiliate_comment_text": "Link sản phẩm mình để ở đây nhé.\nMình để link tham khảo ở dưới cho bạn nha.",
            "affiliate_link_url": "https://example.com/aff\nhttps://example.com/aff-2",
            "affiliate_comment_delay_seconds": 60,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["page"]["affiliate_comment_enabled"] is True
    assert payload["page"]["affiliate_link_url"] == "https://example.com/aff\nhttps://example.com/aff-2"
    assert payload["page"]["affiliate_comment_delay_seconds"] == 60

    db_session.refresh(page)
    assert page.affiliate_comment_enabled is True
    assert page.affiliate_comment_text == "Link sản phẩm mình để ở đây nhé.\nMình để link tham khảo ở dưới cho bạn nha."
    assert page.affiliate_link_url == "https://example.com/aff\nhttps://example.com/aff-2"
    assert page.affiliate_comment_delay_seconds == 60


def test_affiliate_comment_ignores_blank_lines_and_randomizes_choices():
    page = FacebookPage(
        affiliate_comment_text="Mẫu 1\n\nMẫu 2\n",
        affiliate_link_url="\nhttps://example.com/1\nhttps://example.com/2\n",
    )

    assert has_affiliate_comment_options(page) is True
    assert build_affiliate_comment_text(page, chooser=lambda items: items[-1]) == "Mẫu 2\nhttps://example.com/2"


def test_update_facebook_automation_rejects_blank_affiliate_lists(client, auth_headers, db_session):
    page = FacebookPage(
        page_id="page-aff-empty",
        page_name="Trang aff rỗng",
        long_lived_access_token=encrypt_secret("page-token-empty"),
    )
    db_session.add(page)
    db_session.commit()

    response = client.patch(
        f"/facebook/config/{page.page_id}/automation",
        headers=auth_headers,
        json={
            "comment_auto_reply_enabled": True,
            "comment_ai_prompt": "",
            "message_auto_reply_enabled": False,
            "message_ai_prompt": "",
            "message_reply_schedule_enabled": False,
            "message_reply_start_time": "08:00",
            "message_reply_end_time": "22:00",
            "message_reply_cooldown_minutes": 0,
            "affiliate_comment_enabled": True,
            "affiliate_comment_text": "\n \n",
            "affiliate_link_url": "\n",
            "affiliate_comment_delay_seconds": 60,
        },
    )

    assert response.status_code == 400
    assert "ít nhất một nội dung hoặc một link affiliate" in response.json()["detail"]


def test_retry_affiliate_comment_requeues_task(client, auth_headers, db_session):
    _, _, video = _seed_page_campaign_video(db_session)

    response = client.post(
        f"/campaigns/videos/{video.id}/affiliate-comment/retry",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["video"]["affiliate_comment_status"] == AffiliateCommentStatus.queued.value

    db_session.expire_all()
    saved_video = db_session.query(Video).filter(Video.id == video.id).first()
    assert saved_video.affiliate_comment_status == AffiliateCommentStatus.queued

    task = (
        db_session.query(TaskQueue)
        .filter(TaskQueue.task_type == TASK_TYPE_AFFILIATE_COMMENT, TaskQueue.entity_id == str(video.id))
        .order_by(TaskQueue.created_at.desc())
        .first()
    )
    assert task is not None
    assert task.status == TaskStatus.queued


def test_manual_affiliate_comment_marks_video_posted(client, auth_headers, db_session, monkeypatch):
    _, _, video = _seed_page_campaign_video(db_session)

    monkeypatch.setattr(
        "app.api.campaigns.publish_affiliate_comment",
        lambda **kwargs: {
            "comment_id": "fb-comment-1",
            "post_id": "fb-post-1",
            "permalink_url": "https://facebook.com/reel/1",
        },
    )

    response = client.post(
        f"/campaigns/videos/{video.id}/affiliate-comment/manual",
        headers=auth_headers,
        json={"message": "Link mình để ở đây nhé.\nhttps://example.com/aff"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["video"]["affiliate_comment_status"] == AffiliateCommentStatus.posted.value
    assert payload["video"]["affiliate_comment_fb_id"] == "fb-comment-1"

    db_session.expire_all()
    saved_video = db_session.query(Video).filter(Video.id == video.id).first()
    assert saved_video.affiliate_comment_status == AffiliateCommentStatus.posted
    assert saved_video.affiliate_comment_fb_id == "fb-comment-1"
    assert saved_video.fb_permalink_url == "https://facebook.com/reel/1"


def test_post_affiliate_comment_job_marks_operator_required_after_final_retry(db_session, monkeypatch):
    _, _, video = _seed_page_campaign_video(db_session)
    video.affiliate_comment_status = AffiliateCommentStatus.queued
    video.affiliate_comment_error = None
    db_session.commit()

    monkeypatch.setattr(
        "app.services.campaign_jobs.publish_affiliate_comment",
        lambda **kwargs: {"error": "Facebook từ chối comment."},
    )

    result = post_affiliate_comment_job(str(video.id), attempt_number=3, max_attempts=3)

    assert result["ok"] is False
    assert result["operator_required"] is True

    db_session.expire_all()
    saved_video = db_session.query(Video).filter(Video.id == video.id).first()
    assert saved_video.affiliate_comment_status == AffiliateCommentStatus.operator_required
    assert saved_video.affiliate_comment_error == "Facebook từ chối comment."
    assert saved_video.affiliate_comment_attempts == 3
