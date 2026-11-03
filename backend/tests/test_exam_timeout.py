"""考试超时懒过期测试"""

from datetime import datetime, timedelta

import pytest

from app.repositories import employee_exam_repository, wrong_question_repository
from app.services import employee_exam_service


def _paper() -> list[dict]:
    return [
        {
            "snapshot": {
                "id": 1,
                "type": "single",
                "stem": "题目一",
                "options": [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
                "answer": ["A"],
                "explanation": "解析一",
            },
            "score": 50,
        },
        {
            "snapshot": {
                "id": 2,
                "type": "judge",
                "stem": "题目二",
                "options": [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
                "answer": ["B"],
                "explanation": "解析二",
            },
            "score": 50,
        },
    ]


def _attempt(expired: bool = True) -> dict:
    expires_at = datetime.now() + (timedelta(minutes=-1) if expired else timedelta(minutes=10))
    return {
        "id": 9,
        "exam_id": 1,
        "employee_id": 1,
        "attempt_no": 1,
        "status": "in_progress",
        "score": None,
        "passed": None,
        "started_at": "2026-11-02 10:00:00",
        "submitted_at": None,
        "duration_seconds": None,
        "expires_at": expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at_dt": expires_at,
        "answers": [
            {"question_id": 1, "selected": ["B"], "duration_ms": 1000},
            {"question_id": 2, "selected": ["B"], "duration_ms": 1000},
        ],
        "title": "超时测试考试",
        "pass_score": 60,
        "tenant_code": "demo",
    }


def test_is_expired():
    assert employee_exam_service._is_expired(_attempt(expired=True)) is True
    assert employee_exam_service._is_expired(_attempt(expired=False)) is False
    no_expiry = _attempt(expired=False)
    no_expiry["expires_at_dt"] = None
    assert employee_exam_service._is_expired(no_expiry) is False


@pytest.mark.asyncio
async def test_expired_submit_uses_saved_answers(monkeypatch):
    state = {"submitted": False}
    captured = {}

    async def fake_get_attempt(tenant_code: str, attempt_id: int, employee_id: int):
        data = _attempt(expired=True)
        if state["submitted"]:
            data.update(
                status="submitted",
                score=50,
                passed=0,
                submitted_at="2026-11-02 10:30:00",
            )
        return data

    async def fake_submit_attempt(attempt_id, score, passed, answers_json, duration_seconds):
        state["submitted"] = True
        captured["score"] = score
        captured["passed"] = passed
        captured["answers_json"] = answers_json
        return True

    async def fake_load_paper(exam_id: int):
        return _paper()

    async def fake_upsert(tenant_code, employee_id, attempt_id, wrong_items):
        captured["wrong_items"] = wrong_items

    monkeypatch.setattr(employee_exam_repository, "get_attempt", fake_get_attempt)
    monkeypatch.setattr(employee_exam_repository, "submit_attempt", fake_submit_attempt)
    monkeypatch.setattr(employee_exam_service, "_load_paper", fake_load_paper)
    monkeypatch.setattr(wrong_question_repository, "upsert_from_exam", fake_upsert)

    # 客户端提交全对答案，但考试已过期，服务端必须只使用已保存的答案
    answers = [
        employee_exam_service.EmployeeAnswerInput(question_id=1, selected=["A"]),
        employee_exam_service.EmployeeAnswerInput(question_id=2, selected=["B"]),
    ]
    result = await employee_exam_service.submit_exam("demo", 1, 9, answers)

    assert result.score == 50
    assert result.passed is False
    assert captured["score"] == 50
    assert captured["passed"] is False
    assert len(captured["wrong_items"]) == 1
    assert captured["wrong_items"][0]["id"] == 1
