"""题库审核服务"""

from __future__ import annotations

import structlog

from app.core.exceptions import QuestionError
from app.models.question_bank import (
    AdminQuestionItem,
    QuestionBankItem,
    QuestionBankListResponse,
    QuestionBulkReviewResponse,
    QuestionCounts,
    QuestionListResponse,
    QuestionUpdateRequest,
)
from app.repositories import question_repository

logger = structlog.get_logger()


def _to_item(question: dict) -> AdminQuestionItem:
    return AdminQuestionItem(**question)


async def list_questions(
    tenant_code: str,
    status: str,
    keyword: str,
    page: int,
    page_size: int,
    bank_id: int | None = None,
) -> QuestionListResponse:
    items, total, counts = await question_repository.list_questions(
        tenant_code=tenant_code,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
        bank_id=bank_id,
    )
    return QuestionListResponse(
        items=[_to_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        counts=QuestionCounts(**counts),
    )


async def review_question(
    tenant_code: str,
    question_id: int,
    action: str,
    note: str | None,
    reviewer: str,
) -> AdminQuestionItem:
    target = await question_repository.get_question(tenant_code, question_id)
    if target is None:
        raise QuestionError("题目不存在")

    status = "approved" if action == "approve" else "rejected"
    review_note = note or ("人工审核驳回" if status == "rejected" else None)

    updated_count = await question_repository.review_question(
        tenant_code=tenant_code,
        question_id=question_id,
        status=status,
        note=review_note,
        reviewer=reviewer,
    )
    if updated_count == 0:
        raise QuestionError("题目审核失败")

    updated = await question_repository.get_question(tenant_code, question_id)
    if updated is None:
        raise QuestionError("题目不存在")

    logger.info(
        "question_reviewed",
        tenant_code=tenant_code,
        question_id=question_id,
        status=status,
        reviewer=reviewer,
    )
    return _to_item(updated)


async def bulk_review(
    tenant_code: str,
    question_ids: list[int],
    action: str,
    note: str | None,
    reviewer: str,
) -> QuestionBulkReviewResponse:
    status = "approved" if action == "approve" else "rejected"
    review_note = note or ("人工审核驳回" if status == "rejected" else None)

    updated = await question_repository.bulk_review(
        tenant_code=tenant_code,
        question_ids=question_ids,
        status=status,
        note=review_note,
        reviewer=reviewer,
    )
    if updated == 0:
        raise QuestionError("没有可审核的题目")

    logger.info(
        "questions_bulk_reviewed",
        tenant_code=tenant_code,
        count=updated,
        status=status,
        reviewer=reviewer,
    )
    return QuestionBulkReviewResponse(updated=updated)


def _validate_question_options(
    question_type: str, options: list, answer: list[str]
) -> list[str]:
    keys = [option.key for option in options]
    if len(set(keys)) != len(keys):
        raise QuestionError("选项 key 不能重复")
    if any(not key.strip() for key in keys):
        raise QuestionError("选项 key 不能为空")

    normalized_answer = sorted({item for item in answer if item})
    if not normalized_answer:
        raise QuestionError("请设置正确答案")
    if not set(normalized_answer).issubset(set(keys)):
        raise QuestionError("答案必须是选项 key 的子集")

    if question_type == "single" and len(normalized_answer) != 1:
        raise QuestionError("单选题只能有 1 个正确答案")
    if question_type == "multiple" and len(normalized_answer) < 2:
        raise QuestionError("多选题至少需要 2 个正确答案")
    if question_type == "judge" and set(keys) != {"A", "B"}:
        raise QuestionError("判断题只能有 A、B 两个选项")
    return normalized_answer


async def update_question(
    tenant_code: str,
    question_id: int,
    req: QuestionUpdateRequest,
) -> AdminQuestionItem:
    question = await question_repository.get_question(tenant_code, question_id)
    if question is None:
        raise QuestionError("题目不存在")

    answer = _validate_question_options(
        question["type"], req.options, req.answer
    )
    updated = await question_repository.update_question(
        tenant_code=tenant_code,
        question_id=question_id,
        stem=req.stem.strip(),
        options=[option.model_dump() for option in req.options],
        answer=answer,
        explanation=req.explanation.strip(),
        knowledge_point=req.knowledge_point.strip(),
        difficulty=req.difficulty,
    )
    if updated == 0:
        raise QuestionError("题目不存在或已删除")

    refreshed = await question_repository.get_question(tenant_code, question_id)
    if refreshed is None:
        raise QuestionError("题目更新失败")
    logger.info(
        "question_updated", tenant_code=tenant_code, question_id=question_id
    )
    return _to_item(refreshed)


async def delete_question(tenant_code: str, question_id: int) -> None:
    question = await question_repository.get_question(tenant_code, question_id)
    if question is None:
        raise QuestionError("题目不存在")
    deleted = await question_repository.soft_delete_question(
        tenant_code, question_id
    )
    if deleted == 0:
        raise QuestionError("题目不存在或已删除")
    logger.info(
        "question_deleted", tenant_code=tenant_code, question_id=question_id
    )


async def list_banks(tenant_code: str) -> QuestionBankListResponse:
    rows = await question_repository.list_banks(tenant_code)
    items = [QuestionBankItem(**row) for row in rows]
    return QuestionBankListResponse(items=items, total=len(items))
