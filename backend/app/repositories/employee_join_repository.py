"""企业加入申请数据访问层"""

from __future__ import annotations

from typing import Any, Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()

REQUEST_SELECT = (
    "SELECT r.id, r.tenant_code, COALESCE(ts.tenant_name, r.tenant_code), r.user_id, "
    "r.name, r.employee_no, r.org_id, COALESCE(o.path, ''), r.role, r.remark, r.status, "
    "r.reject_reason, r.reviewed_by, r.reviewed_at, r.created_at "
    "FROM employee_join_requests r "
    "LEFT JOIN tenant_settings ts ON ts.tenant_code = r.tenant_code "
    "LEFT JOIN org_units o ON o.id = r.org_id "
)


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _to_request(row: tuple) -> dict:
    return {
        "id": row[0],
        "tenant_code": row[1],
        "tenant_name": row[2],
        "user_id": row[3],
        "name": row[4],
        "employee_no": row[5],
        "org_id": row[6],
        "org_path": row[7] or "",
        "role": row[8],
        "remark": row[9],
        "status": row[10],
        "reject_reason": row[11],
        "reviewed_by": row[12],
        "reviewed_at": _datetime_text(row[13]),
        "created_at": _datetime_text(row[14]),
    }


async def create_request(
    tenant_code: str,
    user_id: int,
    name: str,
    employee_no: str,
    remark: Optional[str],
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法提交加入申请")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO employee_join_requests "
                "(tenant_code, user_id, name, employee_no, remark, status) "
                "VALUES (%s, %s, %s, %s, %s, 'pending')",
                (tenant_code, user_id, name, employee_no, remark),
            )
            return int(cur.lastrowid)


async def get_request(tenant_code: str, request_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                REQUEST_SELECT + "WHERE r.tenant_code = %s AND r.id = %s",
                (tenant_code, request_id),
            )
            row = await cur.fetchone()
            return _to_request(row) if row else None


async def get_pending_request_for_user(user_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                REQUEST_SELECT + "WHERE r.user_id = %s AND r.status = 'pending' "
                "ORDER BY r.id DESC LIMIT 1",
                (user_id,),
            )
            row = await cur.fetchone()
            return _to_request(row) if row else None


async def get_latest_request_for_user(user_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                REQUEST_SELECT + "WHERE r.user_id = %s ORDER BY r.id DESC LIMIT 1",
                (user_id,),
            )
            row = await cur.fetchone()
            return _to_request(row) if row else None


async def list_requests(
    tenant_code: str,
    status: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    pool = get_mysql_pool()
    if pool is None:
        return [], 0

    clauses = ["r.tenant_code = %s"]
    params: list[Any] = [tenant_code]
    if status and status != "all":
        clauses.append("r.status = %s")
        params.append(status)
    where = " AND ".join(clauses)
    offset = (page - 1) * page_size

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM employee_join_requests r " f"WHERE {where}",
                tuple(params),
            )
            total = int((await cur.fetchone())[0])
            await cur.execute(
                REQUEST_SELECT + f"WHERE {where} ORDER BY r.created_at DESC, r.id DESC "
                "LIMIT %s OFFSET %s",
                tuple([*params, page_size, offset]),
            )
            rows = await cur.fetchall()
    return [_to_request(row) for row in rows], total


async def count_pending(tenant_code: str) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM employee_join_requests "
                "WHERE tenant_code = %s AND status = 'pending'",
                (tenant_code,),
            )
            return int((await cur.fetchone())[0])


async def mark_approved(
    tenant_code: str,
    request_id: int,
    org_id: Optional[int],
    role: str,
    reviewed_by: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法审核加入申请")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE employee_join_requests SET status = 'approved', org_id = %s, role = %s, "
                "reject_reason = NULL, reviewed_by = %s, reviewed_at = NOW() "
                "WHERE tenant_code = %s AND id = %s AND status = 'pending'",
                (org_id, role, reviewed_by, tenant_code, request_id),
            )
            return int(cur.rowcount)


async def mark_rejected(
    tenant_code: str,
    request_id: int,
    reason: str,
    reviewed_by: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法审核加入申请")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE employee_join_requests SET status = 'rejected', reject_reason = %s, "
                "reviewed_by = %s, reviewed_at = NOW() "
                "WHERE tenant_code = %s AND id = %s AND status = 'pending'",
                (reason, reviewed_by, tenant_code, request_id),
            )
            return int(cur.rowcount)
