"""审计日志数据访问层"""

from __future__ import annotations

import json
from typing import Any

from app.core.db import get_mysql_pool


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return value
        return json.dumps(parsed, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


async def insert(
    tenant_code: str,
    operator_id: str,
    operator_name: str,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict | None,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return

    detail_text = json.dumps(detail, ensure_ascii=False) if detail else None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO audit_logs "
                "(tenant_code, operator_id, operator_name, action, target_type, "
                "target_id, detail_json) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    tenant_code,
                    operator_id[:64],
                    operator_name[:100],
                    action[:50],
                    target_type[:50],
                    target_id[:64],
                    detail_text,
                ),
            )


async def list_logs(
    tenant_code: str,
    action: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    pool = get_mysql_pool()
    if pool is None:
        return [], 0

    where = "WHERE tenant_code = %s"
    params: list[Any] = [tenant_code]
    if action:
        where += " AND action = %s"
        params.append(action)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) FROM audit_logs {where}", tuple(params))
            row = await cur.fetchone()
            total = int(row[0]) if row else 0

            offset = max(page - 1, 0) * page_size
            await cur.execute(
                "SELECT id, operator_name, action, target_type, target_id, "
                f"detail_json, created_at FROM audit_logs {where} "
                "ORDER BY id DESC LIMIT %s OFFSET %s",
                tuple(params) + (page_size, offset),
            )
            rows = await cur.fetchall()

    return (
        [
            {
                "id": int(item[0]),
                "operator_name": item[1],
                "action": item[2],
                "target_type": item[3],
                "target_id": item[4],
                "detail": _json_text(item[5]),
                "created_at": _datetime_text(item[6]),
            }
            for item in rows
        ],
        total,
    )
