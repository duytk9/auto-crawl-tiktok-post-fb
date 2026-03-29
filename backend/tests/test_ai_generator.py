from app.services import ai_generator


def test_generate_message_reply_with_context_requests_json_mode(monkeypatch):
    captured = {}

    def fake_generate(prompt, fallback, **kwargs):
        captured["kwargs"] = kwargs
        return '{"reply":"OK","summary":"Tom tat","intent":"general_support","customer_facts":{},"handoff":false,"handoff_reason":null}'

    monkeypatch.setattr(ai_generator, "_generate_with_gemini", fake_generate)

    payload = ai_generator.generate_message_reply_with_context(
        "Ban oi tu van giup minh",
        conversation_summary="Khach vua mo dau hoi.",
    )

    assert payload["reply"] == "OK"
    assert captured["kwargs"]["generation_config"]["responseMimeType"] == "application/json"
    assert captured["kwargs"]["generation_config"]["temperature"] == 0.2


def test_generate_message_reply_with_context_parses_structured_json(monkeypatch):
    monkeypatch.setattr(
        ai_generator,
        "_generate_with_gemini",
        lambda prompt, fallback, **kwargs: (
            '```json\n'
            '{"reply":"Chào bạn, gói cơ bản hiện gồm 3 bài mỗi tuần.",'
            '"summary":"Khách đang hỏi thành phần gói cơ bản.",'
            '"intent":"hoi_thanh_phan_goi",'
            '"customer_facts":{"san_pham":"goi co ban"},'
            '"handoff":false,'
            '"handoff_reason":null}\n'
            '```'
        ),
    )

    payload = ai_generator.generate_message_reply_with_context(
        "Gói cơ bản gồm những gì?",
        conversation_summary="Khách đã hỏi giá gói cơ bản.",
        recent_turns=[{"role": "customer", "content": "Cho mình xin giá gói cơ bản"}],
        customer_facts={"san_pham": "goi co ban"},
    )

    assert payload["reply"].startswith("Chào bạn")
    assert payload["summary"] == "Khách đang hỏi thành phần gói cơ bản."
    assert payload["intent"] == "hoi_thanh_phan_goi"
    assert payload["customer_facts"] == {"san_pham": "goi co ban"}
    assert payload["handoff"] is False


def test_generate_message_reply_with_context_falls_back_when_json_invalid(monkeypatch):
    monkeypatch.setattr(
        ai_generator,
        "_generate_with_gemini",
        lambda prompt, fallback, **kwargs: "Đây không phải JSON hợp lệ",
    )

    payload = ai_generator.generate_message_reply_with_context(
        "Có ai hỗ trợ mình không?",
        conversation_summary="Khách cần hỗ trợ chung.",
        recent_turns=[],
        customer_facts={"trang_thai": "moi"},
    )

    assert payload["reply"] == "Cảm ơn bạn đã nhắn cho trang. Bên mình sẽ hỗ trợ bạn sớm nhé!"
    assert payload["summary"] == "Khách cần hỗ trợ chung."
    assert payload["intent"] == "general_support"
    assert payload["customer_facts"] == {"trang_thai": "moi"}
    assert payload["handoff"] is False
