"""题库审核服务测试"""

import pytest

from app.core.exceptions import QuestionError
from app.repositories import question_repository
from app.services import question_service


def _question(status: str = "draft") -> dict:
    return {
        "id": 1,
        "tenant_code": "demo",
        "bank_id": 1,
        "bank_name": "食品安全题库",
        "type": "single",
        "stem": "冷藏食品的中心温度应控制在哪个范围？",
        "options": [
            {"key": "A", "text": "0–4℃"},
            {"key": "B", "text": "5–10℃"},
        ],
        "answer": ["A"],
        "explanation": "冷藏食品应保持在 0–4℃。",
        "knowledge_point": "冷藏管理",
        "difficulty": "easy",
        "source": "《食品安全操作规范》P12",
        "status": status,
        "ai_meta": "deepseek-chat · 2026-11-02 09:14",
        "review_note": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "created_at": "2026-11-02 09:14:00",
        "updated_at": "2026-11-02 09:14:00",
    }


@pytest.mark.asyncio
async def test_list_questions(monkeypatch):
    async def fake_list(
        tenant_code: str,
        status: str,
        keyword: str,
        page: int,
        page_size: int,
        bank_id: int | None = None,
    ):
        return [_question()], 1, {"all": 1, "draft": 1, "approved": 0, "rejected": 0}

    monkeypatch.setattr(question_repository, "list_questions", fake_list)

    result = await question_service.list_questions("demo", "all", "", 1, 20)

    assert result.total == 1
    assert result.items[0].id == 1
    assert result.counts.draft == 1


@pytest.mark.asyncio
async def test_review_question_approve(monkeypatch):
    state = {"status": "draft"}

    async def fake_get(tenant_code: str, question_id: int):
        return _question(state["status"])

    async def fake_review(tenant_code: str, question_id: int, status: str, note, reviewer: str):
        state["status"] = status
        return 1

    monkeypatch.setattr(question_repository, "get_question", fake_get)
    monkeypatch.setattr(question_repository, "review_question", fake_review)

    result = await question_service.review_question(
        "demo", 1, "approve", "测试通过", "admin"
    )

    assert result.status == "approved"
    assert result.id == 1


@pytest.mark.asyncio
async def test_review_question_not_found(monkeypatch):
    async def fake_get(tenant_code: str, question_id: int):
        return None

    monkeypatch.setattr(question_repository, "get_question", fake_get)

    with pytest.raises(QuestionError, match="不存在"):
        await question_service.review_question("demo", 999, "approve", None, "admin")


@pytest.mark.asyncio
async def test_bulk_review(monkeypatch):
    async def fake_bulk(tenant_code: str, question_ids: list[int], status: str, note, reviewer: str):
        return len(question_ids)

    monkeypatch.setattr(question_repository, "bulk_review", fake_bulk)

    result = await question_service.bulk_review("demo", [1, 2], "approve", None, "admin")

    assert result.updated == 2


@pytest.mark.asyncio
async def test_bulk_review_requires_existing_questions(monkeypatch):
    async def fake_bulk(tenant_code: str, question_ids: list[int], status: str, note, reviewer: str):
        return 0

    monkeypatch.setattr(question_repository, "bulk_review", fake_bulk)

    with pytest.raises(QuestionError, match="没有可审核"):
        await question_service.bulk_review("demo", [999], "approve", None, "admin")


@pytest.mark.asyncio
async def test_list_questions_filters_by_bank(monkeypatch):
    captured = {}

    async def fake_list(
        tenant_code: str,
        status: str,
        keyword: str,
        page: int,
        page_size: int,
        bank_id: int | None = None,
    ):
        captured["bank_id"] = bank_id
        return [_question()], 1, {"all": 1, "draft": 1, "approved": 0, "rejected": 0}

    monkeypatch.setattr(question_repository, "list_questions", fake_list)

    await question_service.list_questions("demo", "all", "", 1, 20, bank_id=3)

    assert captured["bank_id"] == 3
