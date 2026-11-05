"""员工站内通知路由"""

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_employee_context
from app.models.common import ApiResponse
from app.models.notification import ReadByBizRequest, ReadExamsRequest
from app.repositories import notification_repository
from app.services import notification_service

router = APIRouter(prefix="/employee", tags=["employee"])

RECIPIENT_EMPLOYEE = "employee"


@router.get("/notifications/summary", response_model=ApiResponse)
async def get_notification_summary(
    context: dict = Depends(get_employee_context),
):
    result = await notification_service.list_summary(
        context["tenant_code"], RECIPIENT_EMPLOYEE, context["employee_id"]
    )
    return ApiResponse.success(data=result.model_dump())


@router.get("/notifications", response_model=ApiResponse)
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: dict = Depends(get_employee_context),
):
    result = await notification_service.list_notifications(
        context["tenant_code"],
        RECIPIENT_EMPLOYEE,
        context["employee_id"],
        unread_only,
        page,
        page_size,
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/notifications/read-all", response_model=ApiResponse)
async def mark_all_notifications_read(
    context: dict = Depends(get_employee_context),
):
    count = await notification_repository.mark_all_read(
        context["tenant_code"], RECIPIENT_EMPLOYEE, context["employee_id"]
    )
    return ApiResponse.success(data={"updated": count})


@router.post("/notifications/read-exams", response_model=ApiResponse)
async def mark_notifications_read_by_exams(
    req: ReadExamsRequest,
    context: dict = Depends(get_employee_context),
):
    count = await notification_repository.mark_read_by_exam_ids(
        context["tenant_code"],
        RECIPIENT_EMPLOYEE,
        context["employee_id"],
        req.exam_ids,
    )
    return ApiResponse.success(data={"updated": count})


@router.post("/notifications/read-by-biz", response_model=ApiResponse)
async def mark_notifications_read_by_biz(
    req: ReadByBizRequest,
    context: dict = Depends(get_employee_context),
):
    count = await notification_repository.mark_read_by_biz(
        context["tenant_code"],
        RECIPIENT_EMPLOYEE,
        context["employee_id"],
        req.biz_type,
        req.biz_id,
    )
    return ApiResponse.success(data={"updated": count})


@router.post("/notifications/{notification_id}/read", response_model=ApiResponse)
async def mark_notification_read(
    notification_id: int,
    context: dict = Depends(get_employee_context),
):
    updated = await notification_repository.mark_read(
        context["tenant_code"],
        RECIPIENT_EMPLOYEE,
        context["employee_id"],
        notification_id,
    )
    return ApiResponse.success(data={"updated": 1 if updated else 0})
