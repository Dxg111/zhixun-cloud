"""站内通知测试"""

import pytest

from app.repositories import notification_repository
from app.services import exam_service, notification_service


@pytest.mark.asyncio
async def test_notify_recipients_writes_deduped_rows(monkeypatch):
    captured: dict = {}

    async def fake_insert_many(rows):
        captured["rows"] = rows
        return len(rows)

    monkeypatch.setattr(notification_repository, "insert_many", fake_insert_many)

    inserted = await notification_service.notify_recipients(
        "demo",
        "employee",
        [3, 1, 3, 0],
        type="exam_assigned",
        title="新考试：消防安全考核",
        content="共 20 题，截止 2026-11-20",
        link_page="pages/employee-exams/index",
        link_params={"examId": 8},
        biz_type="exam",
        biz_id=8,
    )

    assert inserted == 2
    rows = captured["rows"]
    assert [row["recipient_id"] for row in rows] == [1, 3]
    assert all(row["tenant_code"] == "demo" for row in rows)
    assert rows[0]["type"] == "exam_assigned"
    assert rows[0]["link_params"] == '{"examId": 8}'
    assert rows[0]["biz_id"] == 8


@pytest.mark.asyncio
async def test_notify_recipients_swallows_db_failure(monkeypatch):
    async def broken_insert(rows):
        raise RuntimeError("db down")

    monkeypatch.setattr(notification_repository, "insert_many", broken_insert)

    inserted = await notification_service.notify_recipients(
        "demo",
        "employee",
        [1],
        type="exam_assigned",
        title="新考试",
        biz_type="exam",
        biz_id=8,
    )

    assert inserted == 0


@pytest.mark.asyncio
async def test_notify_exam_assigned_builds_content(monkeypatch):
    captured: dict = {}

    async def fake_notify(tenant_code, recipient_type, recipient_ids, **kwargs):
        captured["args"] = (tenant_code, recipient_type, list(recipient_ids))
        captured["kwargs"] = kwargs
        return len(recipient_ids)

    monkeypatch.setattr(notification_service, "notify_recipients", fake_notify)

    await notification_service.notify_exam_assigned(
        "demo",
        8,
        "消防安全考核",
        [1, 2],
        end_at="2026-11-20 23:59:00",
        question_count=20,
    )

    tenant_code, recipient_type, ids = captured["args"]
    assert (tenant_code, recipient_type, ids) == ("demo", "employee", [1, 2])
    kwargs = captured["kwargs"]
    assert kwargs["type"] == "exam_assigned"
    assert kwargs["title"] == "新考试：消防安全考核"
    assert "共 20 题" in kwargs["content"]
    assert "截止 2026-11-20 23:59:00" in kwargs["content"]
    assert kwargs["biz_type"] == "exam"
    assert kwargs["biz_id"] == 8


def _exam(status: str = "draft") -> dict:
    return {
        "id": 8,
        "tenant_code": "demo",
        "title": "消防安全考核",
        "bank_id": 2,
        "bank_name": "安全题库",
        "question_count": 20,
        "pass_score": 60,
        "duration_minutes": 30,
        "max_attempts": 1,
        "start_at": None,
        "end_at": "2026-11-20 23:59:00",
        "status": status,
        "assigned": 0,
        "completed": 0,
        "pass_rate": 0,
        "card_view_rate": 0,
        "created_at": "2026-11-05 09:00:00",
    }


@pytest.mark.asyncio
async def test_publish_exam_notifies_assigned_employees(monkeypatch):
    calls: list[dict] = []

    async def get_exam(tenant_code, exam_id):
        return _exam()

    async def no_cards(tenant_code, exam_id):
        return []

    async def publish(tenant_code, exam_id):
        return 2

    async def assigned_ids(exam_id):
        return [1, 2]

    class FakeSettings:
        notify_assigned = True

    async def get_settings(tenant_code):
        return FakeSettings()

    async def fake_notify(tenant_code, exam_id, title, employee_ids, **kwargs):
        calls.append(
            {
                "tenant_code": tenant_code,
                "exam_id": exam_id,
                "title": title,
                "employee_ids": list(employee_ids),
                **kwargs,
            }
        )
        return len(employee_ids)

    monkeypatch.setattr(exam_service.admin_exam_repository, "get_exam", get_exam)
    monkeypatch.setattr(exam_service.knowledge_card_repository, "list_cards_by_exam", no_cards)
    monkeypatch.setattr(exam_service.admin_exam_repository, "publish_exam", publish)
    monkeypatch.setattr(
        exam_service.admin_exam_repository, "list_assigned_employee_ids", assigned_ids
    )
    monkeypatch.setattr(exam_service.settings_service, "get_settings", get_settings)
    monkeypatch.setattr(exam_service.notification_service, "notify_exam_assigned", fake_notify)

    await exam_service.publish_exam("demo", 8)

    assert len(calls) == 1
    assert calls[0]["exam_id"] == 8
    assert calls[0]["employee_ids"] == [1, 2]
    assert calls[0]["question_count"] == 20


@pytest.mark.asyncio
async def test_publish_exam_respects_notification_switch(monkeypatch):
    calls: list[dict] = []

    async def get_exam(tenant_code, exam_id):
        return _exam()

    async def no_cards(tenant_code, exam_id):
        return []

    async def publish(tenant_code, exam_id):
        return 2

    class FakeSettings:
        notify_assigned = False

    async def get_settings(tenant_code):
        return FakeSettings()

    async def fake_notify(*args, **kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(exam_service.admin_exam_repository, "get_exam", get_exam)
    monkeypatch.setattr(exam_service.knowledge_card_repository, "list_cards_by_exam", no_cards)
    monkeypatch.setattr(exam_service.admin_exam_repository, "publish_exam", publish)
    monkeypatch.setattr(exam_service.settings_service, "get_settings", get_settings)
    monkeypatch.setattr(exam_service.notification_service, "notify_exam_assigned", fake_notify)

    await exam_service.publish_exam("demo", 8)

    assert calls == []
