"""管理后台登录服务：数据库账号 + bcrypt 密码校验。"""

from __future__ import annotations

import time

import structlog

from app.core.auth import create_admin_token
from app.core.config import get_settings
from app.core.db import get_mysql_pool
from app.core.exceptions import AuthenticationError
from app.core.passwords import verify_password
from app.models.auth import AdminLoginRequest, AdminLoginResponse, AdminUser
from app.repositories import admin_user_repository

logger = structlog.get_logger()

# 单进程内存限流：同一租户下同一账号连续失败 5 次，锁定 1 分钟
_failed_attempts: dict[str, dict] = {}


def _login_key(req: AdminLoginRequest) -> str:
    return f"{req.tenant_code}:{req.login_name}"


def _is_locked(key: str) -> bool:
    entry = _failed_attempts.get(key)
    if not entry:
        return False
    now = time.time()
    settings = get_settings()
    if entry.get("locked_until", 0) > now:
        return True
    if now - entry.get("last", 0) > settings.admin_login_lock_seconds:
        _failed_attempts.pop(key, None)
    return False


def _record_failure(key: str) -> None:
    settings = get_settings()
    now = time.time()
    window = settings.admin_login_lock_seconds
    entry = _failed_attempts.setdefault(
        key, {"count": 0, "first": now, "last": now, "locked_until": 0}
    )
    if now - entry["first"] > window:
        entry["count"] = 0
        entry["first"] = now
    entry["count"] += 1
    entry["last"] = now
    if entry["count"] >= settings.admin_login_max_failures:
        entry["locked_until"] = now + window
        logger.warning("admin_login_locked", key=key, failures=entry["count"])


async def handle_admin_login(req: AdminLoginRequest) -> AdminLoginResponse:
    if get_mysql_pool() is None:
        logger.error("admin_login_db_unavailable")
        raise AuthenticationError("管理员账号服务暂不可用，请稍后重试")

    key = _login_key(req)
    if _is_locked(key):
        raise AuthenticationError("登录失败次数过多，请 1 分钟后再试")

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
        _record_failure(key)
        logger.warning(
            "admin_login_failed",
            tenant_code=req.tenant_code,
            login_name=req.login_name,
            found=admin is not None,
        )
        raise AuthenticationError("租户编码、账号或密码不正确")

    _failed_attempts.pop(key, None)
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
