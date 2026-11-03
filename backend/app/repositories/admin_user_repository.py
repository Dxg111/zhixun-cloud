"""管理后台账号数据访问层"""

from __future__ import annotations

from typing import Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()


async def find_admin_by_login(tenant_code: str, login_name: str) -> Optional[dict]:
    """按租户编码和登录名查询管理员账号。"""
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, tenant_code, login_name, password_hash, display_name, role, status "
                "FROM admin_users WHERE tenant_code = %s AND login_name = %s",
                (tenant_code, login_name),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "tenant_code": row[1],
                "login_name": row[2],
                "password_hash": row[3],
                "display_name": row[4],
                "role": row[5],
                "status": row[6],
            }


async def upsert_admin(
    tenant_code: str,
    login_name: str,
    password_hash: str,
    display_name: str,
    role: str = "tenant_admin",
) -> None:
    """创建或更新管理员账号（用于初始化/重置密码）。"""
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法写入管理员账号")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO admin_users "
                "(tenant_code, login_name, password_hash, display_name, role, status) "
                "VALUES (%s, %s, %s, %s, %s, 'active') "
                "ON DUPLICATE KEY UPDATE "
                "password_hash = VALUES(password_hash), "
                "display_name = VALUES(display_name), "
                "role = VALUES(role), "
                "status = 'active'",
                (tenant_code, login_name, password_hash, display_name, role),
            )

    logger.info("admin_user_upserted", tenant_code=tenant_code, login_name=login_name)


def _to_admin_dict(row: tuple) -> dict:
    return {
        "id": row[0],
        "tenant_code": row[1],
        "login_name": row[2],
        "display_name": row[3],
        "role": row[4],
        "status": row[5],
        "created_at": row[6].strftime("%Y-%m-%d %H:%M:%S") if row[6] else "",
        "updated_at": row[7].strftime("%Y-%m-%d %H:%M:%S") if row[7] else "",
    }


async def create_admin(
    tenant_code: str,
    login_name: str,
    password_hash: str,
    display_name: str,
    role: str = "tenant_admin",
) -> int:
    """创建管理员账号，返回新账号 id。重复登录名由数据库唯一键拦截。"""
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法创建管理员账号")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO admin_users "
                "(tenant_code, login_name, password_hash, display_name, role, status) "
                "VALUES (%s, %s, %s, %s, %s, 'active')",
                (tenant_code, login_name, password_hash, display_name, role),
            )
            return int(cur.lastrowid)


async def update_admin_password(tenant_code: str, admin_id: int, password_hash: str) -> None:
    """更新管理员密码哈希。"""
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新管理员密码")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE admin_users SET password_hash = %s WHERE tenant_code = %s AND id = %s",
                (password_hash, tenant_code, admin_id),
            )


async def list_admins(tenant_code: str) -> list[dict]:
    """列出指定租户的管理员账号。"""
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, tenant_code, login_name, display_name, role, status, created_at, updated_at "
                "FROM admin_users WHERE tenant_code = %s ORDER BY created_at ASC, id ASC",
                (tenant_code,),
            )
            rows = await cur.fetchall()
            return [_to_admin_dict(row) for row in rows]


async def get_admin_by_id(tenant_code: str, admin_id: int) -> Optional[dict]:
    """按租户和 id 查询管理员账号。"""
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, tenant_code, login_name, display_name, role, status, created_at, updated_at "
                "FROM admin_users WHERE tenant_code = %s AND id = %s",
                (tenant_code, admin_id),
            )
            row = await cur.fetchone()
            return _to_admin_dict(row) if row else None


async def set_admin_status(tenant_code: str, admin_id: int, status: str) -> None:
    """更新管理员启用/停用状态。"""
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新管理员状态")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE admin_users SET status = %s WHERE tenant_code = %s AND id = %s",
                (status, tenant_code, admin_id),
            )


async def count_active_admins(tenant_code: str) -> int:
    """统计租户内启用状态的管理员数量。"""
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM admin_users WHERE tenant_code = %s AND status = 'active'",
                (tenant_code,),
            )
            row = await cur.fetchone()
            return int(row[0]) if row else 0
