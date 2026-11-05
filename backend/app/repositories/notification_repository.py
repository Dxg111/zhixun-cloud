"""站内通知数据访问层"""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()

NOTIFICATION_SELECT = (
    "SELECT id, type, title, content, link_page, link_params, biz_type, biz_id, "
    "read_at, created_at FROM notifications "
)


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _to_item(row: tuple) -> dict:
    return {
        "id": row[0],
        "type": row[1],
        "title": row[2],
        "content": row[3] or "",
        "link_page": row[4] or "",
        "link_params": row[5] or "",
        "biz_type": row[6] or "",
        "biz_id": row[7],
        "read": row[8] is not None,
        "created_at": _datetime_text(row[9]),
    }


async def insert_many(rows: list[dict]) -> int:
    """批量写入通知；同一事件（唯一键）重复写入时忽略。返回实际新增条数。"""
    if not rows:
        return 0

    pool = get_mysql_pool()
    if pool is None:
        logger.warning("notification_insert_skipped", reason="db_unavailable", count=len(rows))
        return 0

    values = [
        (
            row["tenant_code"],
            row["recipient_type"],
            row["recipient_id"],
            row["type"],
            row["title"],
            row.get("content", ""),
            row.get("link_page", ""),
            row.get("link_params", ""),
            row.get("biz_type", ""),
            row.get("biz_id"),
        )
        for row in rows
    ]

    inserted = 0
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for start in range(0, len(values), 500):
                chunk = values[start : start + 500]
                await cur.executemany(
                    "INSERT IGNORE INTO notifications "
                    "(tenant_code, recipient_type, recipient_id, type, title, content, "
                    "link_page, link_params, biz_type, biz_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    chunk,
                )
                inserted += max(int(cur.rowcount), 0)
    return inserted


async def count_unread(
    tenant_code: str, recipient_type: str, recipient_id: int
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM notifications "
                "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "AND read_at IS NULL",
                (tenant_code, recipient_type, recipient_id),
            )
            row = await cur.fetchone()
    return int(row[0]) if row else 0


async def list_summary(
    tenant_code: str, recipient_type: str, recipient_id: int, limit: int = 3
) -> tuple[int, list[dict]]:
    pool = get_mysql_pool()
    if pool is None:
        return 0, []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM notifications "
                "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "AND read_at IS NULL",
                (tenant_code, recipient_type, recipient_id),
            )
            row = await cur.fetchone()
            unread = int(row[0]) if row else 0

            await cur.execute(
                NOTIFICATION_SELECT
                + "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "ORDER BY id DESC LIMIT %s",
                (tenant_code, recipient_type, recipient_id, limit),
            )
            rows = await cur.fetchall()

    return unread, [_to_item(item) for item in rows]


async def list_unread_exam_ids(
    tenant_code: str, recipient_type: str, recipient_id: int
) -> list[int]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT biz_id FROM notifications "
                "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "AND read_at IS NULL AND biz_type = 'exam' AND biz_id IS NOT NULL",
                (tenant_code, recipient_type, recipient_id),
            )
            rows = await cur.fetchall()
    return [int(row[0]) for row in rows]


async def count_pending_exams(
    tenant_code: str, employee_id: int
) -> int:
    """待完成考试数：已发布、已指派、尚未提交。"""
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM exam_assignments a "
                "JOIN exams e ON e.id = a.exam_id "
                "WHERE a.employee_id = %s AND e.tenant_code = %s AND e.status = 'published' "
                "AND NOT EXISTS (SELECT 1 FROM exam_attempts at "
                "WHERE at.exam_id = e.id AND at.employee_id = a.employee_id "
                "AND at.status = 'submitted')",
                (employee_id, tenant_code),
            )
            row = await cur.fetchone()
    return int(row[0]) if row else 0


async def list_notifications(
    tenant_code: str,
    recipient_type: str,
    recipient_id: int,
    unread_only: bool,
    page: int,
    page_size: int,
) -> tuple[list[dict], int, int]:
    pool = get_mysql_pool()
    if pool is None:
        return [], 0, 0

    where = (
        "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s"
    )
    params: list[Any] = [tenant_code, recipient_type, recipient_id]
    if unread_only:
        where += " AND read_at IS NULL"

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) FROM notifications {where}", tuple(params))
            row = await cur.fetchone()
            total = int(row[0]) if row else 0

            await cur.execute(
                "SELECT COUNT(*) FROM notifications "
                "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "AND read_at IS NULL",
                (tenant_code, recipient_type, recipient_id),
            )
            row = await cur.fetchone()
            unread = int(row[0]) if row else 0

            offset = max(page - 1, 0) * page_size
            await cur.execute(
                NOTIFICATION_SELECT + where + " ORDER BY id DESC LIMIT %s OFFSET %s",
                tuple(params) + (page_size, offset),
            )
            rows = await cur.fetchall()

    return [_to_item(item) for item in rows], total, unread


async def mark_read(
    tenant_code: str, recipient_type: str, recipient_id: int, notification_id: int
) -> bool:
    pool = get_mysql_pool()
    if pool is None:
        return False

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE notifications SET read_at = NOW() "
                "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "AND id = %s AND read_at IS NULL",
                (tenant_code, recipient_type, recipient_id, notification_id),
            )
            return cur.rowcount > 0


async def mark_all_read(
    tenant_code: str, recipient_type: str, recipient_id: int
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE notifications SET read_at = NOW() "
                "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "AND read_at IS NULL",
                (tenant_code, recipient_type, recipient_id),
            )
            return max(int(cur.rowcount), 0)


async def mark_read_by_biz(
    tenant_code: str,
    recipient_type: str,
    recipient_id: int,
    biz_type: str,
    biz_id: int,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE notifications SET read_at = NOW() "
                "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "AND biz_type = %s AND biz_id = %s AND read_at IS NULL",
                (tenant_code, recipient_type, recipient_id, biz_type, biz_id),
            )
            return max(int(cur.rowcount), 0)


async def mark_read_by_exam_ids(
    tenant_code: str,
    recipient_type: str,
    recipient_id: int,
    exam_ids: list[int],
) -> int:
    if not exam_ids:
        return 0

    pool = get_mysql_pool()
    if pool is None:
        return 0

    placeholders = ",".join(["%s"] * len(exam_ids))
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE notifications SET read_at = NOW() "
                "WHERE tenant_code = %s AND recipient_type = %s AND recipient_id = %s "
                "AND biz_type = 'exam' AND read_at IS NULL "
                f"AND biz_id IN ({placeholders})",
                (tenant_code, recipient_type, recipient_id, *exam_ids),
            )
            return max(int(cur.rowcount), 0)


async def count_bound_wechat(employee_ids: list[int]) -> int:
    """统计指派员工中已绑定微信的用户数。"""
    if not employee_ids:
        return 0

    pool = get_mysql_pool()
    if pool is None:
        return 0

    placeholders = ",".join(["%s"] * len(employee_ids))
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) FROM employees WHERE id IN ({placeholders}) "
                "AND user_id IS NOT NULL",
                tuple(employee_ids),
            )
            row = await cur.fetchone()
    return int(row[0]) if row else 0
