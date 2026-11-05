"""微信订阅消息数据访问层"""

from __future__ import annotations

from typing import Optional

from app.core.db import get_mysql_pool


async def add_quota(user_id: int, template_id: str, times: int = 1) -> int:
    """记录一次用户授权；同一模板累加可用次数。"""
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO wechat_subscriptions (user_id, template_id, remaining) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE remaining = remaining + VALUES(remaining)",
                (user_id, template_id, max(1, times)),
            )
            await cur.execute(
                "SELECT remaining FROM wechat_subscriptions "
                "WHERE user_id = %s AND template_id = %s",
                (user_id, template_id),
            )
            row = await cur.fetchone()
    return int(row[0]) if row else 0


async def get_quota(user_id: int) -> dict[str, int]:
    pool = get_mysql_pool()
    if pool is None:
        return {}

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT template_id, remaining FROM wechat_subscriptions WHERE user_id = %s",
                (user_id,),
            )
            return {row[0]: int(row[1]) for row in await cur.fetchall()}


async def consume(user_id: int, template_id: str) -> bool:
    """扣减一次可用额度；没有剩余时返回 False。"""
    pool = get_mysql_pool()
    if pool is None:
        return False

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE wechat_subscriptions SET remaining = remaining - 1 "
                "WHERE user_id = %s AND template_id = %s AND remaining > 0",
                (user_id, template_id),
            )
            return cur.rowcount > 0


async def find_employee_contact(employee_id: int) -> Optional[dict]:
    """返回员工绑定的用户与 openid。"""
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT e.user_id, u.openid FROM employees e "
                "JOIN users u ON u.id = e.user_id "
                "WHERE e.id = %s AND e.status = 'active'",
                (employee_id,),
            )
            row = await cur.fetchone()
    if row is None:
        return None
    return {"user_id": int(row[0]), "openid": row[1]}


async def get_notification_prefs(employee_id: int) -> dict:
    pool = get_mysql_pool()
    if pool is None:
        return {"notify_deadline": True}

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT notify_deadline FROM employees WHERE id = %s",
                (employee_id,),
            )
            row = await cur.fetchone()
    return {"notify_deadline": bool(row[0]) if row else True}


async def update_notification_prefs(employee_id: int, notify_deadline: bool) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE employees SET notify_deadline = %s WHERE id = %s",
                (1 if notify_deadline else 0, employee_id),
            )
