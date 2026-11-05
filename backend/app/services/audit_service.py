"""审计日志服务

审计属于旁路逻辑：写失败只记应用日志，不影响业务操作。
"""

from __future__ import annotations

import structlog

from app.models.audit import AuditLogListResponse
from app.repositories import audit_repository

logger = structlog.get_logger()


async def record(
    tenant_code: str,
    context: dict | None,
    action: str,
    *,
    target_type: str = "",
    target_id: str | int = "",
    detail: dict | None = None,
) -> None:
    """记录一条审计日志。context 为管理员路由的鉴权上下文。"""
    context = context or {}
    operator_name = (
        context.get("display_name") or context.get("login_name") or "管理员"
    )
    operator_id = str(context.get("login_name") or context.get("sub") or "")

    try:
        await audit_repository.insert(
            tenant_code=tenant_code,
            operator_id=operator_id,
            operator_name=operator_name,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            detail=detail,
        )
    except Exception as exc:  # 审计失败不能影响业务
        logger.error(
            "audit_record_failed",
            tenant_code=tenant_code,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            error=str(exc),
            exc_info=True,
        )


async def list_logs(
    tenant_code: str, action: str, page: int, page_size: int
) -> AuditLogListResponse:
    items, total = await audit_repository.list_logs(
        tenant_code, action, page, page_size
    )
    return AuditLogListResponse(
        items=items, total=total, page=page, page_size=page_size
    )
