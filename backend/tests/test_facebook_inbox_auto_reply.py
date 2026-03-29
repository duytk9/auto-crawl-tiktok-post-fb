from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.models import ConversationStatus, FacebookPage, InboxConversation, InboxMessageLog, InteractionStatus, TaskQueue, User
from app.services.security import encrypt_secret
from app.services.task_queue import TASK_TYPE_MESSAGE_REPLY, enqueue_task
from app.worker.tasks import process_task_queue


def mock_page_access(page_id: str, access_token: str):
    return {
        "ok": True,
        "message": "Mã truy cập hợp lệ.",
        "token_kind": "page_access_token",
        "token_subject_id": page_id,
        "token_subject_name": "Trang demo",
        "page_id": page_id,
        "page_name": "Trang demo",
        "page_link": "https://facebook.com/demo-page",
        "fan_count": 123,
    }


def test_can_save_page_automation_settings(client, auth_headers, monkeypatch):
    from app.api import facebook as facebook_api

    monkeypatch.setattr(facebook_api, "inspect_page_access", mock_page_access)

    create_response = client.post(
        "/facebook/config",
        headers=auth_headers,
        json={
            "page_id": "page-1",
            "page_name": "Trang demo",
            "long_lived_access_token": "page-token-123456",
        },
    )
    assert create_response.status_code == 200

    update_response = client.patch(
        "/facebook/config/page-1/automation",
        headers=auth_headers,
        json={
            "comment_auto_reply_enabled": True,
            "comment_ai_prompt": "Trả lời bình luận thật vui vẻ.",
            "message_auto_reply_enabled": True,
            "message_ai_prompt": "Trả lời inbox như tư vấn viên bán hàng.",
            "message_reply_schedule_enabled": True,
            "message_reply_start_time": "08:30",
            "message_reply_end_time": "21:45",
            "message_reply_cooldown_minutes": 15,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["page"]["comment_ai_prompt"] == "Trả lời bình luận thật vui vẻ."
    assert payload["page"]["message_auto_reply_enabled"] is True
    assert payload["page"]["message_ai_prompt"] == "Trả lời inbox như tư vấn viên bán hàng."
    assert payload["page"]["message_reply_schedule_enabled"] is True
    assert payload["page"]["message_reply_start_time"] == "08:30"
    assert payload["page"]["message_reply_end_time"] == "21:45"
    assert payload["page"]["message_reply_cooldown_minutes"] == 15

    config_response = client.get("/facebook/config", headers=auth_headers)
    assert config_response.status_code == 200
    page_payload = config_response.json()[0]
    assert page_payload["comment_auto_reply_enabled"] is True
    assert page_payload["message_auto_reply_enabled"] is True
    assert page_payload["message_reply_schedule_enabled"] is True
    assert page_payload["message_reply_cooldown_minutes"] == 15


def test_rejects_user_access_token_when_saving_page(client, auth_headers, monkeypatch):
    from app.api import facebook as facebook_api

    monkeypatch.setattr(
        facebook_api,
        "inspect_page_access",
        lambda page_id, access_token: {
            "ok": False,
            "message": "Mã truy cập hiện tại là User Access Token. Hãy dùng đúng Page Access Token của fanpage.",
            "token_kind": "user_access_token",
            "token_subject_id": "user-1",
            "token_subject_name": "Người dùng thử nghiệm",
            "page_id": page_id,
            "page_name": "Trang demo",
        },
    )

    create_response = client.post(
        "/facebook/config",
        headers=auth_headers,
        json={
            "page_id": "page-user-token",
            "page_name": "Trang sai token",
            "long_lived_access_token": "user-token-123456",
        },
    )
    assert create_response.status_code == 400
    assert "User Access Token" in create_response.json()["detail"]


def test_validate_page_returns_messenger_connection(client, auth_headers, db_session, monkeypatch):
    from app.api import facebook as facebook_api

    page = FacebookPage(
        page_id="page-validate",
        page_name="Trang kiểm tra",
        long_lived_access_token=encrypt_secret("page-token-validate"),
    )
    db_session.add(page)
    db_session.commit()

    monkeypatch.setattr(facebook_api, "inspect_page_access", mock_page_access)
    monkeypatch.setattr(
        facebook_api,
        "inspect_page_messenger_subscription",
        lambda page_id, access_token, required_fields=("messages",): {
            "ok": True,
            "connected": True,
            "message": "Inbox đã kết nối với app kiểm thử.",
            "required_fields": list(required_fields),
            "connected_app": {
                "id": "app-1",
                "name": "Ứng dụng kiểm thử",
                "subscribed_fields": ["messages"],
            },
            "apps": [
                {
                    "id": "app-1",
                    "name": "Ứng dụng kiểm thử",
                    "subscribed_fields": ["messages"],
                }
            ],
        },
    )

    response = client.get("/facebook/config/page-validate/validate", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["token_kind"] == "page_access_token"
    assert payload["messenger_connection"]["connected"] is True
    assert payload["messenger_connection"]["connected_app"]["id"] == "app-1"


def test_can_subscribe_page_messages_from_dashboard(client, auth_headers, db_session, monkeypatch):
    from app.api import facebook as facebook_api

    page = FacebookPage(
        page_id="page-subscribe",
        page_name="Trang subscribe",
        long_lived_access_token=encrypt_secret("page-token-subscribe"),
    )
    db_session.add(page)
    db_session.commit()

    monkeypatch.setattr(facebook_api, "inspect_page_access", mock_page_access)
    monkeypatch.setattr(
        facebook_api,
        "subscribe_page_to_app",
        lambda page_id, access_token, subscribed_fields=("messages",): {
            "ok": True,
            "message": "Đã đăng ký messages.",
            "data": {"success": True},
        },
    )
    monkeypatch.setattr(
        facebook_api,
        "inspect_page_messenger_subscription",
        lambda page_id, access_token, required_fields=("messages",): {
            "ok": True,
            "connected": True,
            "message": "Inbox đã kết nối với app kiểm thử.",
            "required_fields": list(required_fields),
            "connected_app": {
                "id": "app-2",
                "name": "Ứng dụng kiểm thử",
                "subscribed_fields": ["messages"],
            },
            "apps": [
                {
                    "id": "app-2",
                    "name": "Ứng dụng kiểm thử",
                    "subscribed_fields": ["messages"],
                }
            ],
        },
    )

    response = client.post("/facebook/config/page-subscribe/subscribe-messages", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert "messages" in payload["message"]
    assert payload["validation"]["token_kind"] == "page_access_token"
    assert payload["messenger_connection"]["connected"] is True
    assert payload["messenger_connection"]["connected_app"]["id"] == "app-2"


def test_webhook_message_event_creates_message_log_and_task_when_enabled(client, auth_headers, db_session):
    page = FacebookPage(
        page_id="page-enabled",
        page_name="Trang bật inbox",
        long_lived_access_token=encrypt_secret("page-token-enabled"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-enabled",
                    "messaging": [
                        {
                            "sender": {"id": "user-100"},
                            "recipient": {"id": "page-enabled"},
                            "message": {"mid": "mid.100", "text": "Xin chào shop"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    logs = db_session.query(InboxMessageLog).all()
    assert len(logs) == 1
    assert logs[0].status == InteractionStatus.pending
    assert logs[0].user_message == "Xin chào shop"
    assert logs[0].conversation_id is not None

    conversations = db_session.query(InboxConversation).all()
    assert len(conversations) == 1
    assert conversations[0].page_id == "page-enabled"
    assert conversations[0].sender_id == "user-100"
    assert conversations[0].latest_customer_message_id == "mid.100"

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert len(tasks) == 1
    assert tasks[0].entity_type == "inbox_message_log"


def test_webhook_message_event_is_recorded_without_task_when_disabled(client, db_session):
    page = FacebookPage(
        page_id="page-disabled",
        page_name="Trang tắt inbox",
        long_lived_access_token=encrypt_secret("page-token-disabled"),
        message_auto_reply_enabled=False,
    )
    db_session.add(page)
    db_session.commit()

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-disabled",
                    "messaging": [
                        {
                            "sender": {"id": "user-200"},
                            "recipient": {"id": "page-disabled"},
                            "message": {"mid": "mid.200", "text": "Có ai hỗ trợ không?"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    logs = db_session.query(InboxMessageLog).all()
    assert len(logs) == 1
    assert logs[0].status == InteractionStatus.ignored
    assert "đang tắt" in (logs[0].ai_reply or "")

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert tasks == []


def test_webhook_message_event_is_ignored_outside_schedule(client, db_session, monkeypatch):
    page = FacebookPage(
        page_id="page-schedule",
        page_name="Trang theo giờ",
        long_lived_access_token=encrypt_secret("page-token-schedule"),
        message_auto_reply_enabled=True,
        message_reply_schedule_enabled=True,
        message_reply_start_time="08:00",
        message_reply_end_time="17:00",
    )
    db_session.add(page)
    db_session.commit()

    monkeypatch.setattr(
        "app.api.webhooks.get_local_now",
        lambda: datetime(2026, 3, 29, 22, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh")),
    )

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-schedule",
                    "messaging": [
                        {
                            "sender": {"id": "user-300"},
                            "recipient": {"id": "page-schedule"},
                            "message": {"mid": "mid.300", "text": "Nhắn ngoài giờ"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    log = db_session.query(InboxMessageLog).filter(InboxMessageLog.facebook_message_id == "mid.300").first()
    assert log is not None
    assert log.status == InteractionStatus.ignored
    assert "Ngoài khung giờ" in (log.ai_reply or "")

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert tasks == []


def test_webhook_message_event_is_ignored_during_cooldown(client, db_session):
    page = FacebookPage(
        page_id="page-cooldown",
        page_name="Trang cooldown",
        long_lived_access_token=encrypt_secret("page-token-cooldown"),
        message_auto_reply_enabled=True,
        message_reply_cooldown_minutes=30,
    )
    db_session.add(page)
    db_session.commit()

    previous_log = InboxMessageLog(
        page_id="page-cooldown",
        facebook_message_id="mid.old",
        sender_id="user-400",
        recipient_id="page-cooldown",
        user_message="Tin cũ",
        ai_reply="Đã phản hồi trước đó",
        status=InteractionStatus.replied,
    )
    db_session.add(previous_log)
    db_session.commit()

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-cooldown",
                    "messaging": [
                        {
                            "sender": {"id": "user-400"},
                            "recipient": {"id": "page-cooldown"},
                            "message": {"mid": "mid.400", "text": "Nhắn liên tiếp"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    log = db_session.query(InboxMessageLog).filter(InboxMessageLog.facebook_message_id == "mid.400").first()
    assert log is not None
    assert log.status == InteractionStatus.ignored
    assert "thời gian chờ 30 phút" in (log.ai_reply or "")

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert tasks == []


def test_webhook_message_event_is_ignored_when_conversation_waits_for_human(client, db_session):
    page = FacebookPage(
        page_id="page-human",
        page_name="Trang operator",
        long_lived_access_token=encrypt_secret("page-token-human"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    conversation = InboxConversation(
        page_id="page-human",
        sender_id="user-human",
        recipient_id="page-human",
        needs_human_handoff=True,
        handoff_reason="Khách đang cần nhân viên xử lý trực tiếp.",
    )
    db_session.add(conversation)
    db_session.commit()

    webhook_response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-human",
                    "messaging": [
                        {
                            "sender": {"id": "user-human"},
                            "recipient": {"id": "page-human"},
                            "message": {"mid": "mid.human.1", "text": "Cho mình gặp nhân viên nhé"},
                        }
                    ],
                }
            ],
        },
    )
    assert webhook_response.status_code == 200

    log = db_session.query(InboxMessageLog).filter(InboxMessageLog.facebook_message_id == "mid.human.1").first()
    assert log is not None
    assert log.status == InteractionStatus.ignored
    assert "chuyển cho nhân viên" in (log.ai_reply or "")

    tasks = db_session.query(TaskQueue).filter(TaskQueue.task_type == TASK_TYPE_MESSAGE_REPLY).all()
    assert tasks == []


def test_worker_processes_message_reply_task(db_session, monkeypatch):
    page = FacebookPage(
        page_id="page-worker",
        page_name="Trang worker",
        long_lived_access_token=encrypt_secret("page-token-worker"),
        message_auto_reply_enabled=True,
        message_ai_prompt="Tư vấn nhanh gọn.",
    )
    db_session.add(page)
    db_session.commit()

    log = InboxMessageLog(
        page_id="page-worker",
        facebook_message_id="mid.worker.1",
        sender_id="user-worker",
        recipient_id="page-worker",
        user_message="Cho mình xin giá",
        status=InteractionStatus.pending,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    enqueue_task(
        db_session,
        task_type=TASK_TYPE_MESSAGE_REPLY,
        entity_type="inbox_message_log",
        entity_id=str(log.id),
        payload={"message_log_id": str(log.id)},
        priority=20,
    )

    monkeypatch.setattr(
        "app.services.campaign_jobs.generate_message_reply_with_context",
        lambda user_message, **kwargs: {
            "reply": f"Phản hồi AI cho: {user_message}",
            "summary": f"Khách vừa hỏi: {user_message}",
            "intent": "hoi_gia",
            "customer_facts": {},
            "handoff": False,
            "handoff_reason": None,
        },
    )
    monkeypatch.setattr(
        "app.services.campaign_jobs.send_page_message",
        lambda recipient_id, message, access_token: {"recipient_id": recipient_id, "message_id": "m_out_1"},
    )

    processed = process_task_queue("worker-test@local")
    assert processed == 1

    db_session.expire_all()
    saved_log = db_session.query(InboxMessageLog).filter(InboxMessageLog.id == log.id).first()
    assert saved_log.status == InteractionStatus.replied
    assert saved_log.ai_reply == "Phản hồi AI cho: Cho mình xin giá"
    assert saved_log.facebook_reply_message_id == "m_out_1"


def test_worker_skips_reply_when_conversation_already_handoff(db_session, monkeypatch):
    page = FacebookPage(
        page_id="page-skip-handoff",
        page_name="Trang skip handoff",
        long_lived_access_token=encrypt_secret("page-token-skip-handoff"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    conversation = InboxConversation(
        page_id="page-skip-handoff",
        sender_id="user-skip-handoff",
        recipient_id="page-skip-handoff",
        needs_human_handoff=True,
        handoff_reason="Đang chờ nhân viên tiếp nhận.",
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    log = InboxMessageLog(
        page_id="page-skip-handoff",
        conversation_id=conversation.id,
        facebook_message_id="mid.skip.handoff",
        sender_id="user-skip-handoff",
        recipient_id="page-skip-handoff",
        user_message="Mình cần hỗ trợ gấp",
        status=InteractionStatus.pending,
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    enqueue_task(
        db_session,
        task_type=TASK_TYPE_MESSAGE_REPLY,
        entity_type="inbox_message_log",
        entity_id=str(log.id),
        payload={"message_log_id": str(log.id)},
        priority=20,
    )

    called = {"ai": False, "send": False}

    def fake_ai(*args, **kwargs):
        called["ai"] = True
        return {}

    def fake_send(*args, **kwargs):
        called["send"] = True
        return {}

    monkeypatch.setattr("app.services.campaign_jobs.generate_message_reply_with_context", fake_ai)
    monkeypatch.setattr("app.services.campaign_jobs.send_page_message", fake_send)

    processed = process_task_queue("worker-skip-handoff@local")
    assert processed == 1

    db_session.expire_all()
    saved_log = db_session.query(InboxMessageLog).filter(InboxMessageLog.id == log.id).first()
    assert saved_log.status == InteractionStatus.ignored
    assert "chuyển cho nhân viên" in (saved_log.ai_reply or "")
    assert called["ai"] is False
    assert called["send"] is False


def test_worker_uses_recent_conversation_history_and_updates_memory(db_session, monkeypatch):
    page = FacebookPage(
        page_id="page-memory",
        page_name="Trang memory",
        long_lived_access_token=encrypt_secret("page-token-memory"),
        message_auto_reply_enabled=True,
        message_ai_prompt="Tư vấn theo đúng ngữ cảnh đã trao đổi.",
    )
    db_session.add(page)
    db_session.commit()

    conversation = InboxConversation(
        page_id="page-memory",
        sender_id="user-memory",
        recipient_id="page-memory",
        conversation_summary="Khách đã hỏi giá gói cơ bản.",
        current_intent="hoi_gia",
        customer_facts={"san_pham": "goi co ban"},
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    old_log = InboxMessageLog(
        page_id="page-memory",
        conversation_id=conversation.id,
        facebook_message_id="mid.memory.old",
        sender_id="user-memory",
        recipient_id="page-memory",
        user_message="Cho mình xin giá gói cơ bản",
        ai_reply="Gói cơ bản hiện là 299k.",
        status=InteractionStatus.replied,
    )
    current_log = InboxMessageLog(
        page_id="page-memory",
        conversation_id=conversation.id,
        facebook_message_id="mid.memory.new",
        sender_id="user-memory",
        recipient_id="page-memory",
        user_message="Vậy gồm những gì vậy shop?",
        status=InteractionStatus.pending,
    )
    db_session.add(old_log)
    db_session.add(current_log)
    db_session.commit()
    db_session.refresh(current_log)

    enqueue_task(
        db_session,
        task_type=TASK_TYPE_MESSAGE_REPLY,
        entity_type="inbox_message_log",
        entity_id=str(current_log.id),
        payload={"message_log_id": str(current_log.id)},
        priority=20,
    )

    captured = {}

    def fake_generate(user_message, **kwargs):
        captured["user_message"] = user_message
        captured["kwargs"] = kwargs
        return {
            "reply": "Gói cơ bản gồm 3 bài đăng mỗi tuần và 1 báo cáo tổng hợp.",
            "summary": "Khách đã hỏi giá và đang hỏi thêm thành phần của gói cơ bản.",
            "intent": "hoi_thanh_phan_goi",
            "customer_facts": {"san_pham": "goi co ban", "moi_quan_tam": "thanh_phan"},
            "handoff": False,
            "handoff_reason": None,
        }

    monkeypatch.setattr("app.services.campaign_jobs.generate_message_reply_with_context", fake_generate)
    monkeypatch.setattr(
        "app.services.campaign_jobs.send_page_message",
        lambda recipient_id, message, access_token: {"recipient_id": recipient_id, "message_id": "m_out_memory"},
    )

    processed = process_task_queue("worker-memory@local")
    assert processed == 1

    assert captured["user_message"] == "Vậy gồm những gì vậy shop?"
    assert captured["kwargs"]["conversation_summary"] == "Khách đã hỏi giá gói cơ bản."
    assert captured["kwargs"]["customer_facts"] == {"san_pham": "goi co ban"}
    assert captured["kwargs"]["recent_turns"] == [
        {"role": "customer", "content": "Cho mình xin giá gói cơ bản"},
        {"role": "assistant", "content": "Gói cơ bản hiện là 299k."},
    ]

    db_session.expire_all()
    saved_log = db_session.query(InboxMessageLog).filter(InboxMessageLog.id == current_log.id).first()
    saved_conversation = db_session.query(InboxConversation).filter(InboxConversation.id == conversation.id).first()

    assert saved_log.status == InteractionStatus.replied
    assert saved_log.ai_reply.startswith("Gói cơ bản gồm 3 bài đăng")
    assert saved_log.facebook_reply_message_id == "m_out_memory"
    assert saved_conversation.current_intent == "hoi_thanh_phan_goi"
    assert saved_conversation.customer_facts == {"san_pham": "goi co ban", "moi_quan_tam": "thanh_phan"}
    assert saved_conversation.needs_human_handoff is False
    assert saved_conversation.latest_customer_message_id == "mid.memory.new"
    assert saved_conversation.latest_reply_message_id == "m_out_memory"
    assert saved_conversation.last_ai_reply_at is not None


def test_worker_marks_conversation_handoff_when_ai_requests_it(db_session, monkeypatch):
    page = FacebookPage(
        page_id="page-handoff",
        page_name="Trang handoff",
        long_lived_access_token=encrypt_secret("page-token-handoff"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    conversation = InboxConversation(
        page_id="page-handoff",
        sender_id="user-handoff",
        recipient_id="page-handoff",
        customer_facts={},
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    current_log = InboxMessageLog(
        page_id="page-handoff",
        conversation_id=conversation.id,
        facebook_message_id="mid.handoff.1",
        sender_id="user-handoff",
        recipient_id="page-handoff",
        user_message="Mình cần xử lý khiếu nại gấp",
        status=InteractionStatus.pending,
    )
    db_session.add(current_log)
    db_session.commit()
    db_session.refresh(current_log)

    enqueue_task(
        db_session,
        task_type=TASK_TYPE_MESSAGE_REPLY,
        entity_type="inbox_message_log",
        entity_id=str(current_log.id),
        payload={"message_log_id": str(current_log.id)},
        priority=20,
    )

    monkeypatch.setattr(
        "app.services.campaign_jobs.generate_message_reply_with_context",
        lambda user_message, **kwargs: {
            "reply": "Bên mình đã ghi nhận khiếu nại và sẽ chuyển nhân viên hỗ trợ ngay cho bạn.",
            "summary": "Khách cần xử lý khiếu nại gấp, đã chuyển cho người thật hỗ trợ.",
            "intent": "khieu_nai_gap",
            "customer_facts": {"muc_dich": "khieu_nai"},
            "handoff": True,
            "handoff_reason": "Khách cần nhân viên xử lý khiếu nại trực tiếp.",
        },
    )
    monkeypatch.setattr(
        "app.services.campaign_jobs.send_page_message",
        lambda recipient_id, message, access_token: {"recipient_id": recipient_id, "message_id": "m_out_handoff"},
    )

    processed = process_task_queue("worker-handoff@local")
    assert processed == 1

    db_session.expire_all()
    saved_conversation = db_session.query(InboxConversation).filter(InboxConversation.id == conversation.id).first()
    assert saved_conversation.needs_human_handoff is True
    assert saved_conversation.handoff_reason == "Khách cần nhân viên xử lý khiếu nại trực tiếp."
    assert saved_conversation.current_intent == "khieu_nai_gap"


def test_operator_can_clear_handoff_status_from_dashboard(client, auth_headers, db_session):
    page = FacebookPage(
        page_id="page-clear-handoff",
        page_name="Trang clear handoff",
        long_lived_access_token=encrypt_secret("page-token-clear-handoff"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    conversation = InboxConversation(
        page_id="page-clear-handoff",
        sender_id="user-clear-handoff",
        recipient_id="page-clear-handoff",
        needs_human_handoff=True,
        handoff_reason="Đang chờ nhân viên xử lý.",
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    response = client.patch(
        f"/webhooks/messages/{conversation.id}/handoff",
        headers=auth_headers,
        json={"needs_human_handoff": False, "handoff_reason": ""},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation"]["needs_human_handoff"] is False
    assert payload["conversation"]["handoff_reason"] == ""
    assert "facebook_thread_url" in payload["conversation"]

    db_session.expire_all()
    saved_conversation = db_session.query(InboxConversation).filter(InboxConversation.id == conversation.id).first()
    assert saved_conversation.needs_human_handoff is False
    assert saved_conversation.handoff_reason is None
    assert saved_conversation.status == ConversationStatus.resolved


def test_can_list_conversations_grouped_with_latest_preview(client, auth_headers, db_session):
    page = FacebookPage(
        page_id="page-conversations",
        page_name="Trang conversation",
        long_lived_access_token=encrypt_secret("page-token-conversations"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    conversation = InboxConversation(
        page_id="page-conversations",
        sender_id="user-conversations",
        recipient_id="page-conversations",
        status=ConversationStatus.operator_active,
        needs_human_handoff=True,
        handoff_reason="Khách đang chờ nhân viên tư vấn.",
        current_intent="hoi_gia",
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    db_session.add_all(
        [
            InboxMessageLog(
                page_id="page-conversations",
                conversation_id=conversation.id,
                facebook_message_id="mid.conv.1",
                sender_id="user-conversations",
                recipient_id="page-conversations",
                user_message="Shop còn bàn phím này không?",
                status=InteractionStatus.ignored,
            ),
            InboxMessageLog(
                page_id="page-conversations",
                conversation_id=conversation.id,
                facebook_message_id="outbound:mid.conv.2",
                sender_id="user-conversations",
                recipient_id="page-conversations",
                user_message=None,
                ai_reply="Bên mình đang kiểm tra giúp bạn nhé.",
                facebook_reply_message_id="mid.conv.2",
                reply_source="operator",
                status=InteractionStatus.replied,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/webhooks/conversations", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["conversations"]) == 1
    item = payload["conversations"][0]
    assert item["id"] == str(conversation.id)
    assert item["status"] == ConversationStatus.operator_active.value
    assert item["message_count"] == 2
    assert item["latest_preview"] == "Bên mình đang kiểm tra giúp bạn nhé."
    assert item["latest_preview_direction"] == "page"
    assert item["latest_log"]["reply_source"] == "operator"


def test_operator_can_send_manual_reply_and_keep_conversation_active(client, auth_headers, db_session, monkeypatch):
    from app.api import webhooks as webhooks_api

    page = FacebookPage(
        page_id="page-manual-reply",
        page_name="Trang manual",
        long_lived_access_token=encrypt_secret("page-token-manual"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    admin_user = db_session.query(User).filter(User.username == "admin").first()
    conversation = InboxConversation(
        page_id="page-manual-reply",
        sender_id="user-manual",
        recipient_id="page-manual-reply",
        status=ConversationStatus.operator_active,
        needs_human_handoff=True,
        handoff_reason="Đang chờ nhân viên xử lý trực tiếp.",
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    monkeypatch.setattr(
        webhooks_api,
        "send_page_message",
        lambda recipient_id, message, access_token: {"recipient_id": recipient_id, "message_id": "m_manual_1"},
    )

    response = client.post(
        f"/webhooks/conversations/{conversation.id}/reply",
        headers=auth_headers,
        json={"message": "Mình đã kiểm tra rồi, mẫu này còn hàng bạn nhé.", "mark_resolved": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation"]["status"] == ConversationStatus.operator_active.value
    assert payload["log"]["reply_source"] == "operator"
    assert payload["log"]["reply_author_user_id"] == str(admin_user.id)

    db_session.expire_all()
    saved_conversation = db_session.query(InboxConversation).filter(InboxConversation.id == conversation.id).first()
    saved_logs = db_session.query(InboxMessageLog).filter(InboxMessageLog.conversation_id == conversation.id).all()
    assert saved_conversation.assigned_to_user_id == admin_user.id
    assert saved_conversation.last_operator_reply_at is not None
    assert saved_conversation.status == ConversationStatus.operator_active
    assert len(saved_logs) == 1
    assert saved_logs[0].reply_source == "operator"
    assert saved_logs[0].facebook_reply_message_id == "m_manual_1"


def test_can_update_conversation_status_assignment_and_note(client, auth_headers, db_session):
    admin_user = db_session.query(User).filter(User.username == "admin").first()
    page = FacebookPage(
        page_id="page-update-conversation",
        page_name="Trang update",
        long_lived_access_token=encrypt_secret("page-token-update"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    conversation = InboxConversation(
        page_id="page-update-conversation",
        sender_id="user-update",
        recipient_id="page-update-conversation",
        status=ConversationStatus.ai_active,
        needs_human_handoff=False,
    )
    db_session.add(conversation)
    db_session.commit()
    db_session.refresh(conversation)

    response = client.patch(
        f"/webhooks/conversations/{conversation.id}",
        headers=auth_headers,
        json={
            "status": "operator_active",
            "assigned_to_user_id": str(admin_user.id),
            "internal_note": "Khách hỏi combo gear cho FPS.",
            "handoff_reason": "Cần nhân viên tư vấn chốt cấu hình.",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["conversation"]["status"] == ConversationStatus.operator_active.value
    assert payload["conversation"]["assigned_to_user_id"] == str(admin_user.id)
    assert payload["conversation"]["internal_note"] == "Khách hỏi combo gear cho FPS."
    assert payload["conversation"]["assigned_user"]["username"] == "admin"

    db_session.expire_all()
    saved_conversation = db_session.query(InboxConversation).filter(InboxConversation.id == conversation.id).first()
    assert saved_conversation.status == ConversationStatus.operator_active
    assert saved_conversation.needs_human_handoff is True
    assert saved_conversation.handoff_reason == "Cần nhân viên tư vấn chốt cấu hình."
    assert saved_conversation.internal_note == "Khách hỏi combo gear cho FPS."


def test_resolved_conversation_reopens_ai_on_new_customer_message(client, db_session):
    page = FacebookPage(
        page_id="page-reopen-ai",
        page_name="Trang reopen",
        long_lived_access_token=encrypt_secret("page-token-reopen"),
        message_auto_reply_enabled=True,
    )
    db_session.add(page)
    db_session.commit()

    conversation = InboxConversation(
        page_id="page-reopen-ai",
        sender_id="user-reopen",
        recipient_id="page-reopen-ai",
        status=ConversationStatus.resolved,
        needs_human_handoff=False,
        resolved_at=datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")),
    )
    db_session.add(conversation)
    db_session.commit()

    response = client.post(
        "/webhooks/fb",
        json={
            "object": "page",
            "entry": [
                {
                    "id": "page-reopen-ai",
                    "messaging": [
                        {
                            "sender": {"id": "user-reopen"},
                            "recipient": {"id": "page-reopen-ai"},
                            "message": {"mid": "mid.reopen.1", "text": "Mình hỏi thêm một chút nhé"},
                        }
                    ],
                }
            ],
        },
    )
    assert response.status_code == 200

    db_session.expire_all()
    saved_conversation = db_session.query(InboxConversation).filter(InboxConversation.page_id == "page-reopen-ai").first()
    saved_log = db_session.query(InboxMessageLog).filter(InboxMessageLog.facebook_message_id == "mid.reopen.1").first()
    assert saved_conversation.status == ConversationStatus.ai_active
    assert saved_conversation.needs_human_handoff is False
    assert saved_conversation.resolved_at is None
    assert saved_log.status == InteractionStatus.pending
