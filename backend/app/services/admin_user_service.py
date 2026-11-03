"""管理后台账号管理服务"""

from __future__ import annotations

import structlog
from pymysql.err import IntegrityError

from app.core.exceptions import AdminUserError
from app.core.passwords import hash_password
from app.models.auth import AdminCreateRequest, AdminUserItem, AdminUserListResponse
from app.repositories import admin_user_repository

logger = structlog.get_logger()


def _to_item(admin: dict) -> AdminUserItem:
    return AdminUserItem(
        id=admin["id"],
        tenant_code=admin["tenant_code"],
        login_name=admin["login_name"],
        display_name=admin["display_name"],
        role=admin["role"],
        status=admin["status"],
        created_at=admin["created_at"],
        updated_at=admin["updated_at"],
    )


async def list_admins(tenant_code: str) -> AdminUserListResponse:
    rows = await admin_user_repository.list_admins(tenant_code)
    return AdminUserListResponse(items=[_to_item(row) for row in rows])


async def create_admin(tenant_code: str, req: AdminCreateRequest) -> AdminUserItem:
    existing = await admin_user_repository.find_admin_by_login(
        tenant_code=tenant_code,
        login_name=req.login_name,
    )
    if existing is not None:
        raise AdminUserError("登录名已存在")

    try:
        admin_id = await admin_user_repository.create_admin(
            tenant_code=tenant_code,
            login_name=req.login_name,
            password_hash=hash_password(req.password),
            display_name=req.display_name,
            role="tenant_admin",
        )
    except IntegrityError as exc:
        # 并发创建时唯一键兜底
        raise AdminUserError("登录名已存在") from exc

    created = await admin_user_repository.get_admin_by_id(tenant_code, admin_id)
    if created is None:
        raise AdminUserError("创建管理员失败")

    logger.info(
        "admin_created",
        tenant_code=tenant_code,
        admin_id=admin_id,
        login_name=req.login_name,
    )
    return _to_item(created)


async def reset_admin_password(
    tenant_code: str,
    admin_id: int,
    new_password: str,
) -> AdminUserItem:
    target = await admin_user_repository.get_admin_by_id(tenant_code, admin_id)
    if target is None:
        raise AdminUserError("管理员不存在")

    await admin_user_repository.update_admin_password(
        tenant_code=tenant_code,
        admin_id=admin_id,
        password_hash=hash_password(new_password),
    )

    updated = await admin_user_repository.get_admin_by_id(tenant_code, admin_id)
    if updated is None:
        raise AdminUserError("管理员不存在")

    logger.info(
        "admin_password_reset",
        tenant_code=tenant_code,
        admin_id=admin_id,
        login_name=updated["login_name"],
    )
    return _to_item(updated)


async def update_admin_status(
    tenant_code: str,
    admin_id: int,
    status: str,
    actor_login_name: str,
) -> AdminUserItem:
    target = await admin_user_repository.get_admin_by_id(tenant_code, admin_id)
    if target is None:
        raise AdminUserError("管理员不存在")

    if target["status"] == status:
        return _to_item(target)

    if status == "disabled":
        if target["login_name"] == actor_login_name:
            raise AdminUserError("不能停用当前登录账号")

        if target["status"] == "active":
            active_count = await admin_user_repository.count_active_admins(tenant_code)
            if active_count <= 1:
                raise AdminUserError("至少保留一个启用状态的管理员")

    await admin_user_repository.set_admin_status(tenant_code, admin_id, status)

    updated = await admin_user_repository.get_admin_by_id(tenant_code, admin_id)
    if updated is None:
        raise AdminUserError("管理员不存在")

    logger.info(
        "admin_status_updated",
        tenant_code=tenant_code,
        admin_id=admin_id,
        login_name=updated["login_name"],
        status=status,
        actor_login_name=actor_login_name,
    )
    return _to_item(updated)
