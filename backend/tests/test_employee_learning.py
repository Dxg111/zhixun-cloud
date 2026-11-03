"""员工知识卡与错题重练测试"""

import pytest

from app.repositories import (
    employee_exam_repository,
    knowledge_card_repository,
    wrong_question_repository,
)
from app.services import employee_learning_service


def _wrong_row(streak: int = 0, mastered_at: str | None = None) -> dict:
    return {
        "id": 5,
        "tenant_code": "demo",
        "employee_id": 1,
        "question_id": 1,
        "snapshot": {
            "id": 1,
            "type": "single",
            "stem": "冷藏食品应保持在多少度？",
            "options": [
                {"key": "A", "text": "0–4℃"},
                {"key": "B", "text": "5–10℃"},
            ],
            "answer": ["A"],
            "explanation": "冷藏食品应保持在 0–4℃。",
            "knowledge_point": "冷藏管理",
        },
        "source_type": "exam",
        "source_id": "9",
        "wrong_count": 1,
        "correct_streak": streak,
        "last_wrong_at": "2026-11-02 10:00:00",
        "mastered_at": mastered_at,
        "created_at": "2026-11-02 10:00:00",
    }


@pytest.mark.asyncio
async def test_retry_twice_marks_mastered(monkeypatch):
    state = {"streak": 0, "mastered_at": None}

    async def fake_get(tenant_code, employee_id, wrong_id):
        return _wrong_row(state["streak"], state["mastered_at"])

    async def fake_correct(tenant_code, employee_id, wrong_id, correct_streak, mastered):
        state["streak"] = correct_streak
        state["mastered_at"] = "2026-11-02 10:10:00" if mastered else None

    async def fake_wrong(tenant_code, employee_id, wrong_id):
        state["streak"] = 0
        state["mastered_at"] = None

    monkeypatch.setattr(wrong_question_repository, "get_wrong_question", fake_get)
    monkeypatch.setattr(wrong_question_repository, "mark_correct", fake_correct)
    monkeypatch.setattr(wrong_question_repository, "mark_wrong", fake_wrong)

    first = await employee_learning_service.retry_wrong_question(
        "demo", 1, 5, ["A"]
    )
    assert first.is_correct is True
    assert first.correct_streak == 1
    assert first.mastered is False

    second = await employee_learning_service.retry_wrong_question(
        "demo", 1, 5, ["A"]
    )
    assert second.correct_streak == 2
    assert second.mastered is True


@pytest.mark.asyncio
async def test_retry_wrong_resets_streak(monkeypatch):
    state = {"streak": 1, "mastered_at": None}

    async def fake_get(tenant_code, employee_id, wrong_id):
        return _wrong_row(state["streak"], state["mastered_at"])

    async def fake_correct(tenant_code, employee_id, wrong_id, correct_streak, mastered):
        state["streak"] = correct_streak
        state["mastered_at"] = "2026-11-02 10:10:00" if mastered else None

    async def fake_wrong(tenant_code, employee_id, wrong_id):
        state["streak"] = 0
        state["mastered_at"] = None

    monkeypatch.setattr(wrong_question_repository, "get_wrong_question", fake_get)
    monkeypatch.setattr(wrong_question_repository, "mark_correct", fake_correct)
    monkeypatch.setattr(wrong_question_repository, "mark_wrong", fake_wrong)

    result = await employee_learning_service.retry_wrong_question(
        "demo", 1, 5, ["B"]
    )

    assert result.is_correct is False
    assert result.correct_streak == 0
    assert result.mastered is False
    assert result.answer == ["A"]


@pytest.mark.asyncio
async def test_list_wrong_questions_maps_snapshot(monkeypatch):
    async def fake_list(tenant_code, employee_id, mastered):
        return [_wrong_row(1, None)]

    monkeypatch.setattr(wrong_question_repository, "list_wrong_questions", fake_list)

    result = await employee_learning_service.list_wrong_questions("demo", 1, False)

    assert result.total == 1
    assert result.items[0].stem == "冷藏食品应保持在多少度？"
    assert result.items[0].options[0].key == "A"
    assert result.items[0].mastered is False


@pytest.mark.asyncio
async def test_list_exam_cards_marks_viewed(monkeypatch):
    async def fake_assignment(tenant_code, exam_id, employee_id):
        return {"exam_id": exam_id, "status": "published"}

    async def fake_cards(tenant_code, exam_id, published_only=False):
        return [
            {
                "id": 7,
                "tenant_code": "demo",
                "doc_id": 1,
                "doc_name": "食品安全.txt",
                "title": "冷藏温度三原则",
                "excerpt": "0–4℃ 冷藏。",
                "source": "食品安全 · 第 1 段",
                "status": "published",
                "view_rate": 0,
                "created_by": "admin",
                "published_at": "2026-11-02 10:00:00",
                "created_at": "2026-11-02 10:00:00",
                "updated_at": "2026-11-02 10:00:00",
                "content_json": {
                    "points": [{"heading": "温度", "body": "0–4℃"}],
                },
            }
        ]

    async def fake_views(tenant_code, employee_id, card_ids):
        return {7: 2}

    monkeypatch.setattr(employee_exam_repository, "get_assignment", fake_assignment)
    monkeypatch.setattr(knowledge_card_repository, "list_cards_by_exam", fake_cards)
    monkeypatch.setattr(knowledge_card_repository, "list_views_for_employee", fake_views)

    result = await employee_learning_service.list_exam_cards("demo", 1, 9)

    assert result.total == 1
    assert result.items[0].viewed is True
    assert result.items[0].view_count == 2
    assert result.items[0].points[0].heading == "温度"
