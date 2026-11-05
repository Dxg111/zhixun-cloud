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


async def notify_result_ready(
    tenant_code: str,
    exam_id: int,
    exam_title: str,
    employee_id: int,
    attempt_id: int,
    score: float,
    passed: bool,
) -> int:
    status_text = "已通过" if passed else "未通过，可重练错题后再考"
    return await notify_recipients(
        tenant_code,
        RECIPIENT_EMPLOYEE,
        [employee_id],
        type="result_ready",
        title=f"成绩已出：{exam_title}",
        content=f"得分 {score} 分，{status_text}",
        link_page="pages/employee-result/index",
        link_params={"attemptId": attempt_id},
        biz_type="attempt",
        biz_id=attempt_id,
    )


async def notify_exam_closed(
    tenant_code: str,
    exam_id: int,
    exam_title: str,
    employee_ids: list[int],
) -> int:
    return await notify_recipients(
        tenant_code,
        RECIPIENT_EMPLOYEE,
        employee_ids,
        type="exam_closed",
        title=f"考试已结束：{exam_title}",
        content="该考试已由管理员关闭，未完成的场次不再计入待办",
        link_page="pages/employee-exams/index",
        biz_type="exam_closed",
        biz_id=exam_id,
    )


async def notify_exam_deadline(
    tenant_code: str,
    exam_id: int,
    exam_title: str,
    employee_ids: list[int],
    end_at: str,
) -> int:
    return await notify_recipients(
        tenant_code,
        RECIPIENT_EMPLOYEE,
        employee_ids,
        type="exam_deadline",
        title=f"考试即将截止：{exam_title}",
        content=f"请在 {end_at} 前完成考试",
        link_page="pages/employee-exams/index",
        biz_type="exam_deadline",
        biz_id=exam_id,
    )


async def notify_join_result(
    tenant_code: str,
    user_id: int,
    request_id: int,
    *,
    approved: bool,
    tenant_name: str = "",
    reject_reason: str = "",
) -> int:
    if approved:
        title = f"已加入{tenant_name or '企业'}"
        content = "审核已通过，现在可以进入企业培训查看考试"
        biz_type = "join_approved"
    else:
        title = "加入申请未通过"
        content = reject_reason or "如信息有误，可修改后重新提交申请"
        biz_type = "join_rejected"

    return await notify_recipients(
        tenant_code,
        RECIPIENT_USER,
        [user_id],
        type=biz_type,
        title=title,
        content=content,
        link_page="pages/employee-login/index",
        biz_type="join_request",
        biz_id=request_id,
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
