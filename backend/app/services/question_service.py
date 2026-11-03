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


async def list_banks(tenant_code: str) -> QuestionBankListResponse:
    rows = await question_repository.list_banks(tenant_code)
    items = [QuestionBankItem(**row) for row in rows]
    return QuestionBankListResponse(items=items, total=len(items))
