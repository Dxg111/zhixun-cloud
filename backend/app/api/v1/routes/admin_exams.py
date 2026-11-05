"""考试、导出、工作台路由"""

import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from app.core.auth import get_admin_context
from app.core.exceptions import AdminExamError
from app.models.admin_exam import (
    ExamAssignRequest,
    ExamCreateRequest,
    ExamKnowledgeCardsRequest,
)
from app.models.common import ApiResponse
from app.services import audit_service, dashboard_service, exam_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=ApiResponse)
async def dashboard(context: dict = Depends(get_admin_context)):
    result = await dashboard_service.get_dashboard(context["tenant_code"])
    return ApiResponse.success(data=result.model_dump())


@router.get("/exams", response_model=ApiResponse)
async def list_exams(
    status: Literal["all", "draft", "published", "closed"] = Query("all"),
    keyword: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    context: dict = Depends(get_admin_context),
):
    result = await exam_service.list_exams(
        tenant_code=context["tenant_code"],
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/exams", response_model=ApiResponse)
async def create_exam(
    req: ExamCreateRequest,
    context: dict = Depends(get_admin_context),
):
    result = await exam_service.create_exam(
        tenant_code=context["tenant_code"],
        req=req,
        created_by=context.get("login_name", ""),
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "exam.create",
        target_type="exam",
        target_id=result.id,
        detail={"title": result.title, "question_count": result.question_count},
    )
    return ApiResponse.success(data=result.model_dump())


@router.get("/exams/{exam_id}", response_model=ApiResponse)
async def get_exam(exam_id: int, context: dict = Depends(get_admin_context)):
    result = await exam_service.get_exam_detail(context["tenant_code"], exam_id)
    return ApiResponse.success(data=result.model_dump())


@router.get("/exams/{exam_id}/knowledge-cards", response_model=ApiResponse)
async def get_exam_knowledge_cards(
    exam_id: int,
    context: dict = Depends(get_admin_context),
):
    cards = await exam_service.get_exam_knowledge_cards(
        context["tenant_code"], exam_id
    )
    return ApiResponse.success(data=[card.model_dump() for card in cards])


@router.put("/exams/{exam_id}/knowledge-cards", response_model=ApiResponse)
async def set_exam_knowledge_cards(
    exam_id: int,
    req: ExamKnowledgeCardsRequest,
    context: dict = Depends(get_admin_context),
):
    cards = await exam_service.set_exam_knowledge_cards(
        context["tenant_code"], exam_id, req.card_ids
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "exam.set_cards",
        target_type="exam",
        target_id=exam_id,
        detail={"card_ids": req.card_ids},
    )
    return ApiResponse.success(data=[card.model_dump() for card in cards])


@router.get("/exams/{exam_id}/assignments", response_model=ApiResponse)
async def get_exam_assignments(
    exam_id: int,
    context: dict = Depends(get_admin_context),
):
    result = await exam_service.get_exam_assignments(context["tenant_code"], exam_id)
    return ApiResponse.success(data=result)


@router.put("/exams/{exam_id}/assignments", response_model=ApiResponse)
async def assign_exam(
    exam_id: int,
    req: ExamAssignRequest,
    context: dict = Depends(get_admin_context),
):
    result = await exam_service.assign_exam(
        context["tenant_code"],
        exam_id,
        req.scope,
        req.org_ids,
        req.employee_ids,
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "exam.assign",
        target_type="exam",
        target_id=exam_id,
        detail={
            "scope": req.scope,
            "assigned": result.get("assigned"),
            "added": result.get("added", 0),
        },
    )
    return ApiResponse.success(data=result)


@router.get("/exams/{exam_id}/analytics", response_model=ApiResponse)
async def get_exam_analytics(exam_id: int, context: dict = Depends(get_admin_context)):
    result = await exam_service.get_exam_analytics(context["tenant_code"], exam_id)
    return ApiResponse.success(data=result)


@router.get("/exams/{exam_id}/attempts", response_model=ApiResponse)
async def list_exam_attempts(
    exam_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: dict = Depends(get_admin_context),
):
    result = await exam_service.get_exam_attempts(
        context["tenant_code"], exam_id, page, page_size
    )
    return ApiResponse.success(data=result)


@router.get("/exams/{exam_id}/notification-stats", response_model=ApiResponse)
async def get_notification_stats(exam_id: int, context: dict = Depends(get_admin_context)):
    result = await exam_service.get_notification_stats(context["tenant_code"], exam_id)
    return ApiResponse.success(data=result)


@router.get("/exams/{exam_id}/notify-preview", response_model=ApiResponse)
async def get_notify_preview(exam_id: int, context: dict = Depends(get_admin_context)):
    result = await exam_service.get_notify_preview(context["tenant_code"], exam_id)
    return ApiResponse.success(data=result)


@router.post("/exams/{exam_id}/publish", response_model=ApiResponse)
async def publish_exam(exam_id: int, context: dict = Depends(get_admin_context)):
    result = await exam_service.publish_exam(context["tenant_code"], exam_id)
    await audit_service.record(
        context["tenant_code"],
        context,
        "exam.publish",
        target_type="exam",
        target_id=exam_id,
        detail={"title": result.title, "assigned": result.assigned},
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/exams/{exam_id}/close", response_model=ApiResponse)
async def close_exam(exam_id: int, context: dict = Depends(get_admin_context)):
    result = await exam_service.close_exam(context["tenant_code"], exam_id)
    await audit_service.record(
        context["tenant_code"],
        context,
        "exam.close",
        target_type="exam",
        target_id=exam_id,
        detail={"title": result.title},
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/exams/{exam_id}/export", response_model=ApiResponse)
async def export_exam(exam_id: int, context: dict = Depends(get_admin_context)):
    result = await exam_service.export_exam(
        tenant_code=context["tenant_code"],
        exam_id=exam_id,
        created_by=context.get("login_name", ""),
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "exam.export",
        target_type="exam",
        target_id=exam_id,
        detail={"task_id": result.id, "file_name": result.file_name},
    )
    return ApiResponse.success(data=result.model_dump())


@router.get("/exports", response_model=ApiResponse)
async def list_exports(context: dict = Depends(get_admin_context)):
    result = await exam_service.list_export_tasks(context["tenant_code"])
    return ApiResponse.success(data=result.model_dump())


@router.get("/exports/{task_id}/download")
async def download_export(task_id: int, context: dict = Depends(get_admin_context)):
    task = await exam_service.get_export_task(context["tenant_code"], task_id)
    expires_at = task.get("expires_at")
    if expires_at:
        try:
            expired = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S") < datetime.now()
        except ValueError:
            expired = False
        if expired:
            raise AdminExamError("导出文件已过期，请重新导出")

    file_path = task.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise AdminExamError("导出文件不存在或已过期")
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if str(file_path).lower().endswith(".xlsx")
        else "text/csv; charset=utf-8"
    )
    return FileResponse(
        file_path,
        filename=task["file_name"],
        media_type=media_type,
    )
