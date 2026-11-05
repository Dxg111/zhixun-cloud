"""导出任务数据访问层"""

from __future__ import annotations

from typing import Any, Optional

from app.core.db import get_mysql_pool


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _to_task(row: tuple) -> dict:
    return {
        "id": row[0],
        "tenant_code": row[1],
        "exam_id": row[2],
        "file_name": row[3],
        "export_type": row[4],
        "status": row[5],
        "rows": row[6],
        "file_path": row[7],
        "created_at": _datetime_text(row[8]),
        "expires_at": _datetime_text(row[9]) if len(row) > 9 else "",
    }


async def list_tasks(tenant_code: str) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, tenant_code, exam_id, file_name, export_type, status, row_count, "
                "file_path, created_at, expires_at FROM export_tasks "
                "WHERE tenant_code = %s ORDER BY created_at DESC, id DESC",
                (tenant_code,),
            )
            rows = await cur.fetchall()
            return [_to_task(row) for row in rows]


async def get_task(tenant_code: str, task_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, tenant_code, exam_id, file_name, export_type, status, row_count, "
                "file_path, created_at, expires_at FROM export_tasks "
                "WHERE tenant_code = %s AND id = %s",
                (tenant_code, task_id),
            )
            row = await cur.fetchone()
            return _to_task(row) if row else None


async def create_task(
    tenant_code: str,
    exam_id: int | None,
    file_name: str,
    export_type: str,
    status: str,
    rows: int,
    file_path: str | None,
    created_by: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法创建导出任务")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO export_tasks "
                "(tenant_code, exam_id, file_name, export_type, status, row_count, file_path, "
                "expires_at, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, DATE_ADD(NOW(), INTERVAL 24 HOUR), %s)",
                (tenant_code, exam_id, file_name, export_type, status, rows, file_path, created_by),
            )
            return int(cur.lastrowid)


async def list_exam_attempts(tenant_code: str, exam_id: int) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT e.employee_no, e.name, COALESCE(o.path, ''), "
                "MAX(a.score) AS best_score, MAX(a.passed) AS passed, "
                "MAX(a.submitted_at) AS submitted_at, COUNT(*) AS attempt_count "
                "FROM exam_attempts a "
                "JOIN employees e ON a.employee_id = e.id "
                "LEFT JOIN org_units o ON e.org_id = o.id "
                "JOIN exams ex ON a.exam_id = ex.id "
                "WHERE ex.tenant_code = %s AND a.exam_id = %s AND a.status = 'submitted' "
                "GROUP BY e.id, e.employee_no, e.name, o.path "
                "ORDER BY e.employee_no ASC",
                (tenant_code, exam_id),
            )
            rows = await cur.fetchall()

    return [
        {
            "employee_no": row[0],
            "name": row[1],
            "org_path": row[2],
            "score": float(row[3]) if row[3] is not None else 0,
            "passed": bool(row[4]),
            "submitted_at": _datetime_text(row[5]),
            "attempt_count": int(row[6]),
        }
        for row in rows
    ]
