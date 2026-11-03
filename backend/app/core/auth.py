"""JWT 鉴权模块"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import structlog
from fastapi import Depends, Request

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

logger = structlog.get_logger()

ALGORITHM = "HS256"


def create_token(user_id: int, openid: str) -> str:
    """生成 JWT token。"""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "user_id": user_id,
        "openid": openid,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """解析 JWT token，失败时抛出 AuthenticationError。"""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise AuthenticationError("无效的登录凭证")


def _extract_token(request: Request) -> Optional[str]:
    """从请求 Header 中提取 Bearer token。"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def get_current_user(request: Request) -> int:
    """必选鉴权依赖，返回 user_id。未登录时抛出 AuthenticationError。"""
    token = _extract_token(request)
    if not token:
        raise AuthenticationError()
    payload = decode_token(token)
    return payload["user_id"]


async def get_optional_user(request: Request) -> Optional[int]:
    """可选鉴权依赖，返回 user_id 或 None。不抛异常。"""
    token = _extract_token(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
        return payload["user_id"]
    except AuthenticationError:
        return None


def create_admin_token(
    login_name: str,
    role: str,
    tenant_code: str,
    display_name: str,
) -> str:
    """生成管理后台 JWT。

    MVP 使用环境变量单管理员；后续接入 users 表后，改为从数据库用户生成。
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.admin_jwt_expire_minutes)
    payload = {
        "sub": login_name,
        "login_name": login_name,
        "role": role,
        "tenant_code": tenant_code,
        "display_name": display_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


async def get_admin_context(request: Request) -> dict:
    """管理后台鉴权依赖，返回管理员 token 上下文。"""
    token = _extract_token(request)
    if not token:
        raise AuthenticationError()

    payload = decode_token(token)
    if payload.get("role") not in {"tenant_admin", "platform_admin"}:
        raise AuthenticationError("无管理后台访问权限")
    if not payload.get("tenant_code"):
        raise AuthenticationError("登录凭证缺少租户信息")
    return payload


def create_employee_token(
    employee_id: int,
    tenant_code: str,
    display_name: str,
    employee_no: str,
) -> str:
    """生成员工 JWT。MVP 使用邀请码登录；后续替换为微信 openid 绑定。"""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(employee_id),
        "employee_id": employee_id,
        "employee_no": employee_no,
        "role": "employee",
        "tenant_code": tenant_code,
        "display_name": display_name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


async def get_employee_context(request: Request) -> dict:
    """员工鉴权依赖。"""
    token = _extract_token(request)
    if not token:
        raise AuthenticationError()

    payload = decode_token(token)
    if payload.get("role") != "employee":
        raise AuthenticationError("无员工访问权限")
    if not payload.get("employee_id") or not payload.get("tenant_code"):
        raise AuthenticationError("登录凭证缺少员工信息")
    return payload
