"""管理后台账号管理路由"""

from fastapi import APIRouter, Depends

from app.core.auth import get_admin_context
from app.models.auth import (
    AdminCreateRequest,
    AdminResetPasswordRequest,
    AdminStatusUpdateRequest,
)
from app.models.common import ApiResponse
from app.services import admin_user_service

router = APIRouter(prefix="/admin/admins", tags=["admin"])


@router.get("", response_model=ApiResponse)
async def list_admin_accounts(context: dict = Depends(get_admin_context)):
    result = await admin_user_service.list_admins(context["tenant_code"])
    return ApiResponse.success(data=result.model_dump())


@router.post("", response_model=ApiResponse)
async def create_admin_account(
    req: AdminCreateRequest,
    context: dict = Depends(get_admin_context),
):
    result = await admin_user_service.create_admin(context["tenant_code"], req)
    return ApiResponse.success(data=result.model_dump())


@router.post("/{admin_id}/reset-password", response_model=ApiResponse)
async def reset_admin_password(
    admin_id: int,
    req: AdminResetPasswordRequest,
    context: dict = Depends(get_admin_context),
):
    result = await admin_user_service.reset_admin_password(
        tenant_code=context["tenant_code"],
        admin_id=admin_id,
        new_password=req.new_password,
    )
    return ApiResponse.success(data=result.model_dump())


@router.put("/{admin_id}/status", response_model=ApiResponse)
async def update_admin_account_status(
    admin_id: int,
    req: AdminStatusUpdateRequest,
    context: dict = Depends(get_admin_context),
):
    result = await admin_user_service.update_admin_status(
        tenant_code=context["tenant_code"],
        admin_id=admin_id,
        status=req.status,
        actor_login_name=context.get("login_name", ""),
    )
    return ApiResponse.success(data=result.model_dump())
