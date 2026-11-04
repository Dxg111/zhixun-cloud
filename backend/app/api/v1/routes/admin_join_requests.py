"""管理后台企业加入申请路由"""

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_admin_context
from app.models.common import ApiResponse
from app.models.employee_join import (
    JoinRequestApproveRequest,
    JoinRequestRejectRequest,
)
from app.services import employee_join_service

router = APIRouter(prefix="/admin/join-requests", tags=["admin"])


@router.get("", response_model=ApiResponse)
async def list_join_requests(
    status: str = Query("pending", max_length=20),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    context: dict = Depends(get_admin_context),
):
    result = await employee_join_service.list_admin_requests(
        tenant_code=context["tenant_code"],
        status=status,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/{request_id}/approve", response_model=ApiResponse)
async def approve_join_request(
    request_id: int,
    req: JoinRequestApproveRequest,
    context: dict = Depends(get_admin_context),
):
    result = await employee_join_service.approve_request(
        tenant_code=context["tenant_code"],
        request_id=request_id,
        admin_name=context.get("display_name") or context.get("login_name") or "管理员",
        req=req,
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/{request_id}/reject", response_model=ApiResponse)
async def reject_join_request(
    request_id: int,
    req: JoinRequestRejectRequest,
    context: dict = Depends(get_admin_context),
):
    result = await employee_join_service.reject_request(
        tenant_code=context["tenant_code"],
        request_id=request_id,
        admin_name=context.get("display_name") or context.get("login_name") or "管理员",
        req=req,
    )
    return ApiResponse.success(data=result.model_dump())
