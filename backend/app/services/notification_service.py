"""站内通知服务

通知写入属于旁路逻辑：失败只记日志，不影响业务主流程（发布考试、判分等）。
幂等由 notifications 表的唯一键保证，同一事件重复写入会被忽略。
"""

from __future__ import annotations

import json
from typing import Iterable

import structlog

from app.models.notification import (
    NotificationListResponse,
    NotificationSummary,
)
from app.repositories import notification_repository

logger = structlog.get_logger()

RECIPIENT_EMPLOYEE = "employee"
RECIPIENT_USER = "user"


async def notify_recipients(
    tenant_code: str,
    recipient_type: str,
    recipient_ids: Iterable[int],
    *,
    type: str,
    title: str,
    content: str = "",
    link_page: str = "",
    link_params: dict | None = None,
    biz_type: str = "",
    biz_id: int | None = None,
) -> int:
    ids = sorted({int(item) for item in recipient_ids if item})
    if not ids:
        return 0

    params_text = (
        json.dumps(link_params, ensure_ascii=False) if link_params else ""
    )
    rows = [
        {
            "tenant_code": tenant_code,
            "recipient_type": recipient_type,
            "recipient_id": recipient_id,
            "type": type,
            "title": title[:200],
            "content": content[:500],
            "link_page": link_page[:120],
            "link_params": params_text[:500],
            "biz_type": biz_type[:30],
            "biz_id": biz_id,
        }
        for recipient_id in ids
    ]

    try:
        inserted = await notification_repository.insert_many(rows)
    except Exception as exc:  # 通知失败不能影响业务
        logger.error(
            "notification_insert_failed",
            tenant_code=tenant_code,
            type=type,
            biz_type=biz_type,
            biz_id=biz_id,
            error=str(exc),
            exc_info=True,
        )
        return 0

    logger.info(
        "notification_inserted",
        tenant_code=tenant_code,
        type=type,
        recipients=len(ids),
        inserted=inserted,
    )
    return inserted


async def notify_exam_assigned(
    tenant_code: str,
    exam_id: int,
    exam_title: str,
    employee_ids: list[int],
    *,
    end_at: str | None = None,
    question_count: int | None = None,
) -> int:
    parts = []
    if question_count:
        parts.append(f"共 {question_count} 题")
    if end_at:
        parts.append(f"截止 {end_at}")
    parts.append("建议先看考前速览再开始")

    return await notify_recipients(
        tenant_code,
        RECIPIENT_EMPLOYEE,
        employee_ids,
        type="exam_assigned",
        title=f"新考试：{exam_title}",
        content="，".join(parts),
        link_page="pages/employee-exams/index",
        biz_type="exam",
        biz_id=exam_id,
    )


async def list_summary(
    tenant_code: str, recipient_type: str, recipient_id: int
) -> NotificationSummary:
    unread, items = await notification_repository.list_summary(
        tenant_code, recipient_type, recipient_id, limit=3
    )
    if recipient_type != RECIPIENT_EMPLOYEE:
        return NotificationSummary(unread_count=unread, items=items)

    unread_exam_ids = await notification_repository.list_unread_exam_ids(
        tenant_code, recipient_type, recipient_id
    )
    pending_exam_count = await notification_repository.count_pending_exams(
        tenant_code, recipient_id
    )
    return NotificationSummary(
        unread_count=unread,
        unread_exam_ids=unread_exam_ids,
        pending_exam_count=pending_exam_count,
        items=items,
    )


async def list_notifications(
    tenant_code: str,
    recipient_type: str,
    recipient_id: int,
    unread_only: bool,
    page: int,
    page_size: int,
) -> NotificationListResponse:
    items, total, unread = await notification_repository.list_notifications(
        tenant_code, recipient_type, recipient_id, unread_only, page, page_size
    )
    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread,
        page=page,
        page_size=page_size,
    )
