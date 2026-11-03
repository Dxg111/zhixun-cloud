"""员工学习服务：考前知识卡与错题重练"""

from __future__ import annotations

import structlog

from app.core.exceptions import AdminExamError, KnowledgeCardError
from app.models.employee_learning import (
    EmployeeCardItem,
    EmployeeCardListResponse,
    EmployeeCardPoint,
    EmployeeWrongQuestionItem,
    EmployeeWrongQuestionListResponse,
    EmployeeWrongRetryResponse,
)
from app.repositories import (
    employee_exam_repository,
    knowledge_card_repository,
    wrong_question_repository,
)

logger = structlog.get_logger()


def _card_points(content: dict | None) -> list[EmployeeCardPoint]:
    if not isinstance(content, dict):
        return []
    raw_points = content.get("points") or content.get("sections") or []
    points: list[EmployeeCardPoint] = []
    for item in raw_points:
        if not isinstance(item, dict):
            continue
        heading = str(item.get("heading") or "").strip()
        body = str(item.get("body") or "").strip()
        if heading and body:
            points.append(EmployeeCardPoint(heading=heading, body=body))
    return points


async def list_exam_cards(
    tenant_code: str,
    employee_id: int,
    exam_id: int,
) -> EmployeeCardListResponse:
    assignment = await employee_exam_repository.get_assignment(
        tenant_code, exam_id, employee_id
    )
    if assignment is None:
        raise AdminExamError("没有分配该考试")
    if assignment.get("status") not in ("published", "closed"):
        raise AdminExamError("考试尚未发布")

    cards = await knowledge_card_repository.list_cards_by_exam(
        tenant_code, exam_id, published_only=True
    )
    view_map = await knowledge_card_repository.list_views_for_employee(
        tenant_code, employee_id, [card["id"] for card in cards]
    )

    items = [
        EmployeeCardItem(
            id=card["id"],
            title=card["title"],
            excerpt=card["excerpt"],
            source=card["source"],
            points=_card_points(card.get("content_json")),
            viewed=card["id"] in view_map,
            view_count=view_map.get(card["id"], 0),
        )
        for card in cards
    ]
    return EmployeeCardListResponse(items=items, total=len(items))


async def record_card_view(
    tenant_code: str,
    employee_id: int,
    card_id: int,
) -> None:
    visible = await knowledge_card_repository.is_card_visible_to_employee(
        tenant_code, employee_id, card_id
    )
    if not visible:
        raise KnowledgeCardError("知识卡不存在、未发布或未关联考试")

    await knowledge_card_repository.upsert_view(tenant_code, employee_id, card_id)


def _wrong_item(row: dict) -> EmployeeWrongQuestionItem:
    snapshot = row.get("snapshot") or {}
    question_id = row.get("question_id") or snapshot.get("id") or 0
    return EmployeeWrongQuestionItem(
        id=row["id"],
        question_id=int(question_id),
        type=snapshot.get("type", "single"),
        stem=snapshot.get("stem", ""),
        options=snapshot.get("options", []),
        knowledge_point=snapshot.get("knowledge_point", ""),
        wrong_count=int(row["wrong_count"]),
        correct_streak=int(row["correct_streak"]),
        mastered=bool(row.get("mastered_at")),
        last_wrong_at=row["last_wrong_at"],
    )


async def list_wrong_questions(
    tenant_code: str,
    employee_id: int,
    mastered: bool | None = None,
) -> EmployeeWrongQuestionListResponse:
    rows = await wrong_question_repository.list_wrong_questions(
        tenant_code, employee_id, mastered
    )
    items = [_wrong_item(row) for row in rows]
    return EmployeeWrongQuestionListResponse(items=items, total=len(items))


async def retry_wrong_question(
    tenant_code: str,
    employee_id: int,
    wrong_id: int,
    selected: list[str],
) -> EmployeeWrongRetryResponse:
    row = await wrong_question_repository.get_wrong_question(
        tenant_code, employee_id, wrong_id
    )
    if row is None:
        raise AdminExamError("错题不存在")

    snapshot = row.get("snapshot") or {}
    correct_answer = list(snapshot.get("answer") or [])
    is_correct = set(selected) == set(correct_answer)

    if is_correct:
        next_streak = int(row["correct_streak"]) + 1
        mastered = next_streak >= 2
        await wrong_question_repository.mark_correct(
            tenant_code, employee_id, wrong_id, next_streak, mastered
        )
    else:
        next_streak = 0
        mastered = False
        await wrong_question_repository.mark_wrong(
            tenant_code, employee_id, wrong_id
        )

    return EmployeeWrongRetryResponse(
        is_correct=is_correct,
        answer=correct_answer,
        explanation=str(snapshot.get("explanation") or ""),
        correct_streak=next_streak,
        mastered=mastered,
    )


async def set_wrong_question_mastered(
    tenant_code: str,
    employee_id: int,
    wrong_id: int,
    mastered: bool,
) -> bool:
    row = await wrong_question_repository.get_wrong_question(
        tenant_code, employee_id, wrong_id
    )
    if row is None:
        raise AdminExamError("错题不存在")

    await wrong_question_repository.set_mastered(
        tenant_code, employee_id, wrong_id, mastered
    )
    return mastered
