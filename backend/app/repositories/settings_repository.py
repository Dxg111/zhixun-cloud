"""租户设置数据访问层"""

from __future__ import annotations

from typing import Any, Optional

from app.core.db import get_mysql_pool


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _to_settings(row: tuple) -> dict:
    return {
        "tenant_code": row[0],
        "tenant_name": row[1],
        "admin_email": row[2],
        "retention": row[3],
        "default_pass_score": row[4],
        "default_duration": row[5],
        "default_attempts": row[6],
        "random_order": row[7],
        "notify_assigned": bool(row[8]),
        "notify_result": bool(row[9]),
        "notify_deadline": bool(row[10]),
        "notify_cards": bool(row[11]),
        "updated_at": _datetime_text(row[12]),
    }


async def get_settings(tenant_code: str) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT tenant_code, tenant_name, admin_email, retention, default_pass_score, "
                "default_duration, default_attempts, random_order, notify_assigned, notify_result, "
                "notify_deadline, notify_cards, updated_at "
                "FROM tenant_settings WHERE tenant_code = %s",
                (tenant_code,),
            )
            row = await cur.fetchone()
            return _to_settings(row) if row else None


async def upsert_settings(
    tenant_code: str,
    tenant_name: str,
    admin_email: str | None,
    retention: str,
    default_pass_score: int,
    default_duration: int,
    default_attempts: int,
    random_order: str,
    notify_assigned: bool,
    notify_result: bool,
    notify_deadline: bool,
    notify_cards: bool,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法保存设置")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO tenant_settings "
                "(tenant_code, tenant_name, admin_email, retention, default_pass_score, "
                "default_duration, default_attempts, random_order, notify_assigned, notify_result, "
                "notify_deadline, notify_cards) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE "
                "tenant_name = VALUES(tenant_name), admin_email = VALUES(admin_email), "
                "retention = VALUES(retention), default_pass_score = VALUES(default_pass_score), "
                "default_duration = VALUES(default_duration), default_attempts = VALUES(default_attempts), "
                "random_order = VALUES(random_order), notify_assigned = VALUES(notify_assigned), "
                "notify_result = VALUES(notify_result), notify_deadline = VALUES(notify_deadline), "
                "notify_cards = VALUES(notify_cards)",
                (
                    tenant_code,
                    tenant_name,
                    admin_email,
                    retention,
                    default_pass_score,
                    default_duration,
                    default_attempts,
                    random_order,
                    int(notify_assigned),
                    int(notify_result),
                    int(notify_deadline),
                    int(notify_cards),
                ),
            )
