"""管理后台登录服务：数据库账号 + bcrypt 密码校验。"""

from __future__ import annotations

import structlog

from app.core.auth import create_admin_token
from app.core.db import get_mysql_pool
from app.core.exceptions import AuthenticationError
from app.core.passwords import verify_password
from app.models.auth import AdminLoginRequest, AdminLoginResponse, AdminUser
from app.repositories import admin_user_repository

logger = structlog.get_logger()


async def handle_admin_login(req: AdminLoginRequest) -> AdminLoginResponse:
    if get_mysql_pool() is None:
        logger.error("admin_login_db_unavailable")
        raise AuthenticationError("管理员账号服务暂不可用，请稍后重试")

    admin = await admin_user_repository.find_admin_by_login(
        tenant_code=req.tenant_code,
        login_name=req.login_name,
    )

    valid = (
        admin is not None
        and admin.get("status") == "active"
        and verify_password(req.password, admin.get("password_hash", ""))
    )

    if not valid:
        logger.warning(
            "admin_login_failed",
            tenant_code=req.tenant_code,
            login_name=req.login_name,
            found=admin is not None,
        )
        raise AuthenticationError("租户编码、账号或密码不正确")

    token = create_admin_token(
        login_name=admin["login_name"],
        role=admin["role"],
        tenant_code=admin["tenant_code"],
        display_name=admin["display_name"],
    )

    logger.info(
        "admin_login_success",
        tenant_code=admin["tenant_code"],
        login_name=admin["login_name"],
        admin_id=admin["id"],
    )

    return AdminLoginResponse(
        token=token,
        user=AdminUser(
            id=admin["id"],
            name=admin["display_name"],
            role=admin["role"],
            tenant_code=admin["tenant_code"],
        ),
    )
