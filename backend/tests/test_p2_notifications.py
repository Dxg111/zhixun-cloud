"""P2：微信订阅消息、通知偏好与送达统计测试"""

import pytest

from app.repositories import wechat_subscription_repository
from app.services import (
    exam_service,
    notification_service,
    wechat_subscribe_service,
)


class FakeSettings:
    enable_wechat_subscribe = True
    wechat_app_id = "wx-app"
    wechat_app_secret = "wx-secret"
    wechat_subscribe_exam_assigned = "tmpl-exam"
    wechat_subscribe_result_ready = "tmpl-result"
    wechat_subscribe_deadline = "tmpl-deadline"


def _patch_settings(monkeypatch):
    monkeypatch.setattr(
        wechat_subscribe_service, "get_settings", lambda: FakeSettings()
    )


# ---------- 模板构造 ----------


def test_build_payload_without_template(monkeypatch):
    class Empty(FakeSettings):
        wechat_subscribe_exam_assigned = ""

    monkeypatch.setattr(wechat_subscribe_service, "get_settings", lambda: Empty())

    assert wechat_subscribe_service.build_template_payload("exam_assigned", {}) is None


def test_build_exam_assigned_payload(monkeypatch):
    _patch_settings(monkeypatch)

    template_id, data = wechat_subscribe_service.build_template_payload(
        "exam_assigned", {"title": "消防安全考核", "end_at": "2026-11-20 23:59:00"}
    )

    assert template_id == "tmpl-exam"
    assert data["thing1"]["value"] == "消防安全考核"
    assert data["date2"]["value"] == "2026-11-20"


def test_build_result_payload(monkeypatch):
    _patch_settings(monkeypatch)

    template_id, data = wechat_subscribe_service.build_template_payload(
        "result_ready", {"title": "月度考核", "score": 88.5, "passed": True}
    )

    assert template_id == "tmpl-result"
    assert data["number2"]["value"] == "88.5"
    assert data["thing3"]["value"] == "已通过"


def test_clip_long_title(monkeypatch):
    _patch_settings(monkeypatch)

    _, data = wechat_subscribe_service.build_template_payload(
        "exam_assigned", {"title": "这是一个非常非常长的考试名称用于测试截断行为"}
    )

    assert len(data["thing1"]["value"]) <= 20


# ---------- 授权与发送 ----------


@pytest.mark.asyncio
async def test_record_subscriptions_filters_unknown_templates(monkeypatch):
    _patch_settings(monkeypatch)
    recorded: list[tuple] = []

    async def add_quota(user_id, template_id, times=1):
        recorded.append((user_id, template_id, times))
        return 1

    monkeypatch.setattr(wechat_subscription_repository, "add_quota", add_quota)

    count = await wechat_subscribe_service.record_subscriptions(
        7, ["tmpl-exam", "unknown", "tmpl-exam"]
    )

    assert count == 1
    assert recorded == [(7, "tmpl-exam", 1)]


@pytest.mark.asyncio
async def test_send_for_employee_without_quota(monkeypatch):
    _patch_settings(monkeypatch)
    sent: list = []

    async def contact(employee_id):
        return {"user_id": 7, "openid": "o-7"}

    async def quota(user_id):
        return {"tmpl-exam": 0}

    async def fake_send(*args, **kwargs):
        sent.append(args)
        return True

    monkeypatch.setattr(wechat_subscription_repository, "find_employee_contact", contact)
    monkeypatch.setattr(wechat_subscription_repository, "get_quota", quota)
    monkeypatch.setattr(wechat_subscribe_service, "send_message", fake_send)

    result = await wechat_subscribe_service.send_for_employee(
        14, "exam_assigned", {"title": "考核", "end_at": "2026-11-20"}
    )

    assert result is False
    assert sent == []


@pytest.mark.asyncio
async def test_send_for_employee_consumes_on_success(monkeypatch):
    _patch_settings(monkeypatch)
    consumed: list[tuple] = []

    async def contact(employee_id):
        return {"user_id": 7, "openid": "o-7"}

    async def quota(user_id):
        return {"tmpl-exam": 1}

    async def fake_send(openid, template_id, data, page):
        assert openid == "o-7"
        assert template_id == "tmpl-exam"
        assert page == "pages/employee-exams/index"
        return True

    async def consume(user_id, template_id):
        consumed.append((user_id, template_id))
        return True

    monkeypatch.setattr(wechat_subscription_repository, "find_employee_contact", contact)
    monkeypatch.setattr(wechat_subscription_repository, "get_quota", quota)
    monkeypatch.setattr(wechat_subscribe_service, "send_message", fake_send)
    monkeypatch.setattr(wechat_subscription_repository, "consume", consume)

    result = await wechat_subscribe_service.send_for_employee(
        14, "exam_assigned", {"title": "考核", "end_at": "2026-11-20"}
    )

    assert result is True
    assert consumed == [(7, "tmpl-exam")]


@pytest.mark.asyncio
async def test_send_failure_does_not_consume(monkeypatch):
    _patch_settings(monkeypatch)
    consumed: list = []

    async def contact(employee_id):
        return {"user_id": 7, "openid": "o-7"}

    async def quota(user_id):
        return {"tmpl-exam": 1}

    async def fake_send(*args, **kwargs):
        return False

    async def consume(user_id, template_id):
        consumed.append((user_id, template_id))
        return True

    monkeypatch.setattr(wechat_subscription_repository, "find_employee_contact", contact)
    monkeypatch.setattr(wechat_subscription_repository, "get_quota", quota)
    monkeypatch.setattr(wechat_subscribe_service, "send_message", fake_send)
    monkeypatch.setattr(wechat_subscription_repository, "consume", consume)

    result = await wechat_subscribe_service.send_for_employee(
        14, "exam_assigned", {"title": "考核"}
    )

    assert result is False
    assert consumed == []


@pytest.mark.asyncio
async def test_notification_service_sends_wechat_after_insert(monkeypatch):
    calls: list[tuple] = []

    async def fake_insert(rows):
        return len(rows)

    async def fake_send(employee_id, notice_type, data):
        calls.append((employee_id, notice_type))
        return employee_id == 1

    monkeypatch.setattr(notification_service.notification_repository, "insert_many", fake_insert)
    monkeypatch.setattr(
        notification_service.wechat_subscribe_service, "send_for_employee", fake_send
    )

    await notification_service.notify_recipients(
        "demo",
        "employee",
        [1, 2],
        type="exam_assigned",
        title="新考试",
        biz_type="exam",
        biz_id=8,
        wechat_data={"title": "新考试"},
    )

    assert sorted(calls) == [(1, "exam_assigned"), (2, "exam_assigned")]


@pytest.mark.asyncio
async def test_notification_service_skips_wechat_without_data(monkeypatch):
    calls: list = []

    async def fake_insert(rows):
        return len(rows)

    async def fake_send(*args, **kwargs):
        calls.append(args)

    monkeypatch.setattr(notification_service.notification_repository, "insert_many", fake_insert)
    monkeypatch.setattr(
        notification_service.wechat_subscribe_service, "send_for_employee", fake_send
    )

    await notification_service.notify_recipients(
        "demo",
        "employee",
        [1],
        type="exam_closed",
        title="考试已关闭",
        biz_type="exam_closed",
        biz_id=8,
    )

    assert calls == []


# ---------- 送达统计 ----------


@pytest.mark.asyncio
async def test_exam_notification_stats(monkeypatch):
    async def get_exam(tenant_code, exam_id):
        return {"id": exam_id}

    async def stats(tenant_code, exam_id):
        return {
            "assigned": 8,
            "notified": 8,
            "read": 3,
            "bound_wechat": 1,
            "unbound": [{"id": 1, "name": "张敏", "employee_no": "0001"}],
        }

    monkeypatch.setattr(exam_service.admin_exam_repository, "get_exam", get_exam)
    monkeypatch.setattr(
        exam_service.admin_exam_repository, "get_notification_stats", stats
    )

    result = await exam_service.get_notification_stats("demo", 8)

    assert result["assigned"] == 8
    assert result["read"] == 3
    assert result["unbound"][0]["name"] == "张敏"
