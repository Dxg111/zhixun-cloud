"""题库审核路由"""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_admin_context
from app.models.common import ApiResponse
from app.models.question_bank import QuestionBulkReviewRequest, QuestionReviewRequest
from app.services import question_service

router = APIRouter(prefix="/admin/questions", tags=["admin"])


@router.get("", response_model=ApiResponse)
async def list_admin_questions(
    status: Literal["all", "draft", "approved", "rejected"] = Query("all"),
    keyword: str = Query("", max_length=100),
    bank_id: int | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: dict = Depends(get_admin_context),
):
    result = await question_service.list_questions(
        tenant_code=context["tenant_code"],
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
        bank_id=bank_id,
    )
    return ApiResponse.success(data=result.model_dump())


@router.get("/banks", response_model=ApiResponse)
async def list_admin_question_banks(context: dict = Depends(get_admin_context)):
    result = await question_service.list_banks(context["tenant_code"])
    return ApiResponse.success(data=result.model_dump())


@router.post("/{question_id}/review", response_model=ApiResponse)
async def review_admin_question(
    question_id: int,
    req: QuestionReviewRequest,
    context: dict = Depends(get_admin_context),
):
    result = await question_service.review_question(
        tenant_code=context["tenant_code"],
        question_id=question_id,
        action=req.action,
        note=req.note,
        reviewer=context.get("login_name", ""),
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/bulk-review", response_model=ApiResponse)
async def bulk_review_admin_questions(
    req: QuestionBulkReviewRequest,
    context: dict = Depends(get_admin_context),
):
    result = await question_service.bulk_review(
        tenant_code=context["tenant_code"],
        question_ids=req.ids,
        action=req.action,
        note=req.note,
        reviewer=context.get("login_name", ""),
    )
    return ApiResponse.success(data=result.model_dump())
