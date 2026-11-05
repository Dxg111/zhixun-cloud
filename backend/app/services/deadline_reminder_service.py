"""考试截止提醒后台扫描

每 10 分钟扫描一次「即将截止且未提交」的指派员工，写入站内通知。
幂等由 notifications 唯一键保证；命名锁避免多进程重复扫描。
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

import structlog

from app.core.config import get_settings
from app.core.db import get_mysql_pool
from app.repositories import notification_repository
from app.services import notification_service, settings_service

logger = structlog.get_logger()

LOCK_NAME = "zhixun_deadline_reminder"


async def scan_once() -> int:
    """执行一次扫描，返回新写入的提醒条数。"""
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT GET_LOCK(%s, 0)", (LOCK_NAME,))
            row = await cur.fetchone()
            if not row or int(row[0]) != 1:
                logger.debug("deadline_reminder_skipped", reason="lock_busy")
                return 0

        try:
            return await _scan_and_notify()
        finally:
            async with conn.cursor() as cur:
                await cur.execute("SELECT RELEASE_LOCK(%s)", (LOCK_NAME,))


async def _scan_and_notify() -> int:
    """锁内逻辑：查询候选并按租户/考试分组发送提醒。"""
    settings = get_settings()
    rows = await notification_repository.list_deadline_candidates(
        settings.deadline_reminder_hours
    )
    if not rows:
        return 0

    # tenant -> exam_id -> {title, end_at, employee_ids}
    grouped: dict[str, dict[int, dict]] = defaultdict(dict)
    for tenant_code, exam_id, title, end_at, employee_id in rows:
        exam = grouped[tenant_code].setdefault(
            int(exam_id),
            {"title": title, "end_at": end_at, "employee_ids": []},
        )
        exam["employee_ids"].append(int(employee_id))

    inserted = 0
    for tenant_code, exams in grouped.items():
        tenant_settings = await settings_service.get_settings(tenant_code)
        if not tenant_settings.notify_deadline:
            continue
        for exam_id, exam in exams.items():
            end_text = exam["end_at"].strftime("%Y-%m-%d %H:%M")
            inserted += await notification_service.notify_exam_deadline(
                tenant_code,
                exam_id,
                exam["title"],
                exam["employee_ids"],
                end_text,
            )

    if inserted:
        logger.info("deadline_reminder_sent", inserted=inserted)
    return inserted


async def run_loop() -> None:
    """后台循环；应用关闭时随 lifespan 取消。"""
    settings = get_settings()
    interval = max(settings.deadline_reminder_interval_seconds, 60)

    # 启动后先等一轮，避免与建表/首屏请求争抢连接
    await asyncio.sleep(60)
    while True:
        try:
            await scan_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("deadline_reminder_failed", error=str(exc), exc_info=True)
        await asyncio.sleep(interval)
