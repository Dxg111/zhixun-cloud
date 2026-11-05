"""组织与员工数据访问层"""

from __future__ import annotations

import secrets
from typing import Any, Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _to_org(row: tuple) -> dict:
    return {
        "id": row[0],
        "parent_id": row[1],
        "name": row[2],
        "path": row[3],
        "sort": row[4],
        "employee_count": int(row[5]) if row[5] is not None else 0,
    }


def _to_employee(row: tuple) -> dict:
    return {
        "id": row[0],
        "tenant_code": row[1],
        "org_id": row[2],
        "user_id": row[3],
        "employee_no": row[4],
        "name": row[5],
        "role": row[6],
        "status": row[7],
        "org_path": row[8] or "",
        "created_at": _datetime_text(row[9]),
    }


async def list_org_units(tenant_code: str) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT o.id, o.parent_id, o.name, o.path, o.sort, "
                "(SELECT COUNT(*) FROM employees e "
                " WHERE e.tenant_code = o.tenant_code AND e.org_id = o.id AND e.status = 'active') "
                "FROM org_units o WHERE o.tenant_code = %s ORDER BY o.sort ASC, o.id ASC",
                (tenant_code,),
            )
            rows = await cur.fetchall()
            return [_to_org(row) for row in rows]


async def get_org(tenant_code: str, org_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT o.id, o.parent_id, o.name, o.path, o.sort, 0 "
                "FROM org_units o WHERE o.tenant_code = %s AND o.id = %s",
                (tenant_code, org_id),
            )
            row = await cur.fetchone()
            return _to_org(row) if row else None


async def find_org_by_path(tenant_code: str, path: str) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT o.id, o.parent_id, o.name, o.path, o.sort, 0 "
                "FROM org_units o WHERE o.tenant_code = %s AND o.path = %s",
                (tenant_code, path),
            )
            row = await cur.fetchone()
            return _to_org(row) if row else None


async def create_org(
    tenant_code: str,
    parent_id: Optional[int],
    name: str,
    path: str,
    sort: int = 0,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法创建部门")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO org_units (tenant_code, parent_id, name, path, sort, status) "
                "VALUES (%s, %s, %s, %s, %s, 'active')",
                (tenant_code, parent_id, name, path, sort),
            )
            return int(cur.lastrowid)


async def list_employees(
    tenant_code: str,
    org_id: Optional[int],
    keyword: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    pool = get_mysql_pool()
    if pool is None:
        return [], 0

    clauses = ["e.tenant_code = %s"]
    params: list[Any] = [tenant_code]

    if org_id is not None:
        org = await get_org(tenant_code, org_id)
        if org is None:
            return [], 0
        clauses.append("(e.org_id = %s OR o.path LIKE %s)")
        params.extend([org_id, f"{org['path']}/%"])

    normalized = keyword.strip()
    if normalized:
        like = f"%{normalized}%"
        clauses.append("(e.name LIKE %s OR e.employee_no LIKE %s)")
        params.extend([like, like])

    where = " AND ".join(clauses)
    offset = (page - 1) * page_size

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM employees e "
                "LEFT JOIN org_units o ON e.org_id = o.id "
                f"WHERE {where}",
                tuple(params),
            )
            total_row = await cur.fetchone()
            total = int(total_row[0]) if total_row else 0

            await cur.execute(
                "SELECT e.id, e.tenant_code, e.org_id, e.user_id, e.employee_no, e.name, e.role, "
                "e.status, COALESCE(o.path, ''), e.created_at "
                "FROM employees e LEFT JOIN org_units o ON e.org_id = o.id "
                f"WHERE {where} ORDER BY e.created_at ASC, e.id ASC LIMIT %s OFFSET %s",
                tuple([*params, page_size, offset]),
            )
            rows = await cur.fetchall()

    return [_to_employee(row) for row in rows], total


async def get_employee(tenant_code: str, employee_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT e.id, e.tenant_code, e.org_id, e.user_id, e.employee_no, e.name, e.role, "
                "e.status, COALESCE(o.path, ''), e.created_at "
                "FROM employees e LEFT JOIN org_units o ON e.org_id = o.id "
                "WHERE e.tenant_code = %s AND e.id = %s",
                (tenant_code, employee_id),
            )
            row = await cur.fetchone()
            return _to_employee(row) if row else None


async def find_employee_by_no(tenant_code: str, employee_no: str) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT e.id, e.tenant_code, e.org_id, e.user_id, e.employee_no, e.name, e.role, "
                "e.status, COALESCE(o.path, ''), e.created_at "
                "FROM employees e LEFT JOIN org_units o ON e.org_id = o.id "
                "WHERE e.tenant_code = %s AND e.employee_no = %s",
                (tenant_code, employee_no),
            )
            row = await cur.fetchone()
            return _to_employee(row) if row else None


async def find_employee_by_invite(tenant_code: str, invite_code: str) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT e.id, e.tenant_code, e.org_id, e.user_id, e.employee_no, e.name, e.role, "
                "e.status, COALESCE(o.path, ''), e.created_at "
                "FROM employees e LEFT JOIN org_units o ON e.org_id = o.id "
                "WHERE e.tenant_code = %s AND e.invite_code = %s",
                (tenant_code, invite_code),
            )
            row = await cur.fetchone()
            return _to_employee(row) if row else None


async def create_employee(
    tenant_code: str,
    org_id: Optional[int],
    employee_no: str,
    name: str,
    role: str,
    user_id: Optional[int] = None,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法创建员工")

    # invite_code 是历史字段，仍保留 NOT NULL 约束；不再对外暴露。
    legacy_invite_code = secrets.token_hex(8).upper()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO employees "
                "(tenant_code, org_id, user_id, employee_no, name, role, status, invite_code, invite_status) "
                "VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, 'bound')",
                (tenant_code, org_id, user_id, employee_no, name, role, legacy_invite_code),
            )
            return int(cur.lastrowid)


async def find_employee_by_user(user_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT e.id, e.tenant_code, e.org_id, e.user_id, e.employee_no, e.name, e.role, "
                "e.status, COALESCE(o.path, ''), e.created_at "
                "FROM employees e LEFT JOIN org_units o ON e.org_id = o.id "
                "WHERE e.user_id = %s",
                (user_id,),
            )
            row = await cur.fetchone()
            return _to_employee(row) if row else None


async def bind_employee_user(tenant_code: str, employee_id: int, user_id: int) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法绑定员工")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE employees SET user_id = %s, invite_status = 'bound' "
                "WHERE tenant_code = %s AND id = %s AND user_id IS NULL",
                (user_id, tenant_code, employee_id),
            )
            return int(cur.rowcount)


async def update_employee_assignment(
    tenant_code: str,
    employee_id: int,
    org_id: Optional[int],
    role: str,
    name: Optional[str] = None,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新员工")

    fields = ["org_id = %s", "role = %s"]
    values: list[Any] = [org_id, role]
    if name:
        fields.append("name = %s")
        values.append(name)
    values.extend([tenant_code, employee_id])

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"UPDATE employees SET {', '.join(fields)} "
                "WHERE tenant_code = %s AND id = %s",
                tuple(values),
            )
            return int(cur.rowcount)


async def update_employee_status(tenant_code: str, employee_id: int, status: str) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新员工状态")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE employees SET status = %s WHERE tenant_code = %s AND id = %s",
                (status, tenant_code, employee_id),
            )
            return int(cur.rowcount)


async def reset_invite(tenant_code: str, employee_id: int, invite_code: str) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法重置邀请码")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE employees SET invite_code = %s, invite_status = 'unbound' "
                "WHERE tenant_code = %s AND id = %s",
                (invite_code, tenant_code, employee_id),
            )
            return int(cur.rowcount)


async def mark_invite_bound(tenant_code: str, employee_id: int) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE employees SET invite_status = 'bound' "
                "WHERE tenant_code = %s AND id = %s AND invite_status = 'unbound'",
                (tenant_code, employee_id),
            )
            return int(cur.rowcount)


async def list_active_employee_ids(tenant_code: str) -> list[int]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM employees WHERE tenant_code = %s AND status = 'active' ORDER BY id ASC",
                (tenant_code,),
            )
            rows = await cur.fetchall()
            return [int(row[0]) for row in rows]


async def update_org(
    tenant_code: str,
    org_id: int,
    name: str,
    parent_id: int | None,
    path: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新部门")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE org_units SET name = %s, parent_id = %s, path = %s "
                "WHERE tenant_code = %s AND id = %s",
                (name, parent_id, path, tenant_code, org_id),
            )
            return int(cur.rowcount)


async def rewrite_descendant_paths(
    tenant_code: str,
    old_path: str,
    new_path: str,
) -> int:
    """把 old_path/ 前缀替换为 new_path/，用于部门改名或移动。"""
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新部门")

    prefix_length = len(old_path) + 1
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE org_units SET path = CONCAT(%s, SUBSTRING(path, %s)) "
                "WHERE tenant_code = %s AND path LIKE %s",
                (new_path, prefix_length, tenant_code, f"{old_path}/%"),
            )
            return int(cur.rowcount)


async def count_org_children(tenant_code: str, org_id: int) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM org_units WHERE tenant_code = %s AND parent_id = %s",
                (tenant_code, org_id),
            )
            return int((await cur.fetchone())[0])


async def delete_org(tenant_code: str, org_id: int) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法删除部门")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM org_units WHERE tenant_code = %s AND id = %s",
                (tenant_code, org_id),
            )
            return int(cur.rowcount)


async def count_org_employees(tenant_code: str, org_id: int) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM employees "
                "WHERE tenant_code = %s AND org_id = %s AND status = 'active'",
                (tenant_code, org_id),
            )
            return int((await cur.fetchone())[0])
