"""租户设置路由"""

from fastapi import APIRouter, Depends

from app.core.auth import get_admin_context
from app.models.admin_console import TenantSettingsUpdate
from app.models.common import ApiResponse
from app.services import settings_service

router = APIRouter(prefix="/admin/settings", tags=["admin"])


@router.get("", response_model=ApiResponse)
async def get_settings(context: dict = Depends(get_admin_context)):
    result = await settings_service.get_settings(context["tenant_code"])
    return ApiResponse.success(data=result.model_dump())


@router.put("", response_model=ApiResponse)
async def update_settings(
    req: TenantSettingsUpdate,
    context: dict = Depends(get_admin_context),
):
    result = await settings_service.update_settings(context["tenant_code"], req)
    return ApiResponse.success(data=result.model_dump())
