"""管理后台认证路由"""

from fastapi import APIRouter, Depends

from app.core.auth import get_admin_context
from app.models.auth import AdminLoginRequest
from app.models.common import ApiResponse
from app.services.admin_auth_service import handle_admin_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/admin/login", response_model=ApiResponse)
async def admin_login(req: AdminLoginRequest):
    result = await handle_admin_login(req)
    return ApiResponse.success(data=result.model_dump())


@router.get("/me", response_model=ApiResponse)
async def admin_me(context: dict = Depends(get_admin_context)):
    return ApiResponse.success(
        data={
            "login_name": context.get("login_name"),
            "name": context.get("display_name"),
            "role": context.get("role"),
            "tenant_code": context.get("tenant_code"),
        }
    )
