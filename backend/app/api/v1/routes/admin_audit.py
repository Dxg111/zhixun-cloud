"""管理端审计日志路由"""

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_admin_context
from app.models.common import ApiResponse
from app.services import audit_service

router = APIRouter(prefix="/admin/audit-logs", tags=["admin"])


@router.get("", response_model=ApiResponse)
async def list_audit_logs(
    action: str = Query("", max_length=50),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    context: dict = Depends(get_admin_context),
):
    result = await audit_service.list_logs(
        context["tenant_code"], action.strip(), page, page_size
    )
    return ApiResponse.success(data=result.model_dump())
