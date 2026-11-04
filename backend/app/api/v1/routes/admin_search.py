"""管理后台全局搜索路由"""

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_admin_context
from app.models.common import ApiResponse
from app.services import admin_search_service

router = APIRouter(prefix="/admin/search", tags=["admin"])


@router.get("", response_model=ApiResponse)
async def global_search(
    keyword: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(5, ge=1, le=10),
    context: dict = Depends(get_admin_context),
):
    result = await admin_search_service.search(
        tenant_code=context["tenant_code"],
        keyword=keyword,
        limit=limit,
    )
    return ApiResponse.success(data=result.model_dump())
