"""P1 通知与身份一致性测试"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core import auth
from app.core.auth import create_employee_token
from app.core.exceptions import AuthenticationError
from app.repositories import admin_org_repository, notification_repository
from app.services import (
    deadline_reminder_service,
    employee_exam_service,
    exam_service,
    notification_service,
)


# ---------- 通知内容 ----------


@pytest.mark.asyncio
async def test_notify_result_ready_content(monkeypatch):
    captured: dict = {}

    async def fake_notify(tenant_code, recipient_type, recipient_ids, **kwargs):
        captured["args"] = (tenant_code, recipient_type, list(recipient_ids))
        captured["kwargs"] = kwargs
        return 1

    monkeypatch.setattr(notification_service, "notify_recipients", fake_notify)

    await notification_service.notify_result_ready(
        "demo", 8, "消防安全考核", 14, 33, 88.5, True
    )

    assert captured["args"] == ("demo", "employee", [14])
    kwargs = captured["kwargs"]
    assert kwargs["type"] == "result_ready"
    assert kwargs["title"] == "成绩已出：消防安全考核"
    assert "88.5" in kwargs["content"]
    assert "已通过" in kwargs["content"]
    assert kwargs["biz_type"] == "attempt"
    assert kwargs["biz_id"] == 33
    assert kwargs["link_params"] == {"attemptId": 33}


@pytest.mark.asyncio
async def test_notify_join_result_approved(monkeypatch):
    captured: dict = {}

    async def fake_notify(tenant_code, recipient_type, recipient_ids, **kwargs):
        captured["args"] = (tenant_code, recipient_type, list(recipient_ids))
        captured["kwargs"] = kwargs
        return 1

    monkeypatch.setattr(notification_service, "notify_recipients", fake_notify)

    await notification_service.notify_join_result(
        "demo", 7, 12, approved=True, tenant_name="演示企业"
    )

    assert captured["args"] == ("demo", "user", [7])
    assert captured["kwargs"]["type"] == "join_approved"
    assert captured["kwargs"]["biz_type"] == "join_request"
    assert "演示企业" in captured["kwargs"]["title"]


@pytest.mark.asyncio
async def test_notify_join_result_rejected_keeps_reason(monkeypatch):
    captured: dict = {}

    async def fake_notify(tenant_code, recipient_type, recipient_ids, **kwargs):
        captured["kwargs"] = kwargs
        return 1

    monkeypatch.setattr(notification_service, "notify_recipients", fake_notify)

    await notification_service.notify_join_result(
        "demo", 7, 12, approved=False, reject_reason="工号与姓名不匹配"
    )

    assert captured["kwargs"]["type"] == "join_rejected"
    assert captured["kwargs"]["content"] == "工号与姓名不匹配"


# ---------- 判分 / 关闭通知触发 ----------


@pytest.mark.asyncio
async def test_result_notification_respects_switch(monkeypatch):
    calls: list[dict] = []

    class FakeSettings:
        notify_result = True

    async def get_settings(tenant_code):
        return FakeSettings()

    async def get_assignment(tenant_code, exam_id, employee_id):
        return {"title": "消防安全考核"}

    async def fake_notify(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return 1

    monkeypatch.setattr(employee_exam_service.settings_service, "get_settings", get_settings)
    monkeypatch.setattr(
        employee_exam_service.employee_exam_repository, "get_assignment", get_assignment
    )
    monkeypatch.setattr(
        employee_exam_service.notification_service, "notify_result_ready", fake_notify
    )

    await employee_exam_service._notify_result_ready(
        "demo",
        14,
        {"id": 33, "exam_id": 8},
        SimpleNamespace(score=88.5, passed=True),
    )

    assert len(calls) == 1
    args = calls[0]["args"]
    assert args[:3] == ("demo", 8, "消防安全考核")
    assert args[3:] == (14, 33, 88.5, True)


@pytest.mark.asyncio
async def test_result_notification_skipped_when_disabled(monkeypatch):
    calls: list = []

    class FakeSettings:
        notify_result = False

    async def get_settings(tenant_code):
        return FakeSettings()

    async def fake_notify(*args, **kwargs):
        calls.append(args)

    monkeypatch.setattr(employee_exam_service.settings_service, "get_settings", get_settings)
    monkeypatch.setattr(
        employee_exam_service.notification_service, "notify_result_ready", fake_notify
    )

    await employee_exam_service._notify_result_ready(
        "demo", 14, {"id": 33, "exam_id": 8}, SimpleNamespace(score=10, passed=False)
    )

    assert calls == []


@pytest.mark.asyncio
async def test_close_exam_notifies_incomplete(monkeypatch):
    captured: dict = {}

    class FakeSettings:
        notify_assigned = True

    async def get_settings(tenant_code):
        return FakeSettings()

    async def incomplete(exam_id):
        return [1, 2]

    async def fake_notify(tenant_code, exam_id, title, employee_ids):
        captured["args"] = (tenant_code, exam_id, title, list(employee_ids))
        return 2

    monkeypatch.setattr(exam_service.settings_service, "get_settings", get_settings)
    monkeypatch.setattr(
        exam_service.admin_exam_repository, "list_incomplete_employee_ids", incomplete
    )
    monkeypatch.setattr(exam_service.notification_service, "notify_exam_closed", fake_notify)

    await exam_service._notify_closed("demo", 8, {"title": "消防安全考核"})

    assert captured["args"] == ("demo", 8, "消防安全考核", [1, 2])


# ---------- 截止提醒 ----------


@pytest.mark.asyncio
async def test_deadline_scan_groups_by_exam(monkeypatch):
    rows = [
        ("demo", 8, "消防安全考核", datetime(2026, 11, 6, 9, 0), 1),
        ("demo", 8, "消防安全考核", datetime(2026, 11, 6, 9, 0), 2),
        ("demo", 9, "SOP 考核", datetime(2026, 11, 6, 10, 0), 3),
    ]
    calls: list[tuple] = []

    async def candidates(hours):
        return rows

    class FakeSettings:
        notify_deadline = True

    async def get_settings(tenant_code):
        return FakeSettings()

    async def fake_notify(tenant_code, exam_id, title, employee_ids, end_at):
        calls.append((tenant_code, exam_id, title, list(employee_ids), end_at))
        return len(employee_ids)

    monkeypatch.setattr(
        notification_repository, "list_deadline_candidates", candidates
    )
    monkeypatch.setattr(deadline_reminder_service.settings_service, "get_settings", get_settings)
    monkeypatch.setattr(
        deadline_reminder_service.notification_service, "notify_exam_deadline", fake_notify
    )

    inserted = await deadline_reminder_service._scan_and_notify()

    assert inserted == 3
    assert calls == [
        ("demo", 8, "消防安全考核", [1, 2], "2026-11-06 09:00"),
        ("demo", 9, "SOP 考核", [3], "2026-11-06 10:00"),
    ]


@pytest.mark.asyncio
async def test_deadline_scan_respects_switch(monkeypatch):
    calls: list = []

    async def candidates(hours):
        return [("demo", 8, "考核", datetime(2026, 11, 6, 9, 0), 1)]

    class FakeSettings:
        notify_deadline = False

    async def get_settings(tenant_code):
        return FakeSettings()

    async def fake_notify(*args, **kwargs):
        calls.append(args)

    monkeypatch.setattr(notification_repository, "list_deadline_candidates", candidates)
    monkeypatch.setattr(deadline_reminder_service.settings_service, "get_settings", get_settings)
    monkeypatch.setattr(
        deadline_reminder_service.notification_service, "notify_exam_deadline", fake_notify
    )

    inserted = await deadline_reminder_service._scan_and_notify()

    assert inserted == 0
    assert calls == []


# ---------- 员工身份校验 ----------


class FakeRequest:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_employee_context_rejects_disabled_employee(monkeypatch):
    token = create_employee_token(14, "demo", "张敏", "0001")

    async def get_employee(tenant_code, employee_id):
        return {"id": employee_id, "status": "disabled", "tenant_code": tenant_code}

    monkeypatch.setattr(admin_org_repository, "get_employee", get_employee)

    with pytest.raises(AuthenticationError):
        await auth.get_employee_context(FakeRequest(token))


@pytest.mark.asyncio
async def test_employee_context_rejects_missing_employee(monkeypatch):
    token = create_employee_token(99, "demo", "无此人", "9999")

    async def get_employee(tenant_code, employee_id):
        return None

    monkeypatch.setattr(admin_org_repository, "get_employee", get_employee)

    with pytest.raises(AuthenticationError):
        await auth.get_employee_context(FakeRequest(token))


@pytest.mark.asyncio
async def test_employee_context_accepts_active_employee(monkeypatch):
    token = create_employee_token(14, "demo", "张敏", "0001")

    async def get_employee(tenant_code, employee_id):
        return {"id": employee_id, "status": "active", "tenant_code": tenant_code}

    monkeypatch.setattr(admin_org_repository, "get_employee", get_employee)

    context = await auth.get_employee_context(FakeRequest(token))

    assert context["employee_id"] == 14
    assert context["tenant_code"] == "demo"
