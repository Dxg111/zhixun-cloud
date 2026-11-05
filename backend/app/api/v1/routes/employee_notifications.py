"""员工站内通知路由"""

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_employee_context
from app.core.config import get_settings
from app.models.common import ApiResponse
from app.models.notification import (
    NotificationPreferences,
    ReadByBizRequest,
    ReadExamsRequest,
    WechatSubscribeReport,
)
from app.repositories import notification_repository, wechat_subscription_repository
from app.services import notification_service, wechat_subscribe_service

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


@router.get("/wechat-subscribe/config", response_model=ApiResponse)
async def get_wechat_subscribe_config(
    context: dict = Depends(get_employee_context),
):
    settings = get_settings()
    templates = wechat_subscribe_service.get_template_map()
    return ApiResponse.success(
        data={
            "enabled": bool(settings.enable_wechat_subscribe and templates),
            "templates": templates,
        }
    )


@router.post("/wechat-subscribe/subscriptions", response_model=ApiResponse)
async def report_wechat_subscriptions(
    req: WechatSubscribeReport,
    context: dict = Depends(get_employee_context),
):
    contact = await wechat_subscription_repository.find_employee_contact(
        context["employee_id"]
    )
    if contact is None:
        return ApiResponse.success(data={"recorded": 0})

    recorded = await wechat_subscribe_service.record_subscriptions(
        contact["user_id"], req.template_ids
    )
    return ApiResponse.success(data={"recorded": recorded})


@router.get("/notification-preferences", response_model=ApiResponse)
async def get_notification_preferences(
    context: dict = Depends(get_employee_context),
):
    prefs = await wechat_subscription_repository.get_notification_prefs(
        context["employee_id"]
    )
    return ApiResponse.success(data=NotificationPreferences(**prefs).model_dump())


@router.put("/notification-preferences", response_model=ApiResponse)
async def update_notification_preferences(
    req: NotificationPreferences,
    context: dict = Depends(get_employee_context),
):
    await wechat_subscription_repository.update_notification_prefs(
        context["employee_id"], req.notify_deadline
    )
    return ApiResponse.success(data=req.model_dump())


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
