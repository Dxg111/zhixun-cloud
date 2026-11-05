"""考试与导出服务"""

from __future__ import annotations

import os
import re
from datetime import datetime

import structlog
from openpyxl import Workbook

from app.core.exceptions import AdminExamError
from app.models.admin_exam import (
    ExamCreateRequest,
    ExamDetailResponse,
    ExamItem,
    ExamListResponse,
    ExportTaskItem,
    ExportTaskListResponse,
)
from app.models.knowledge_card import KnowledgeCardItem
from app.repositories import (
    admin_exam_repository,
    admin_org_repository,
    export_repository,
    knowledge_card_repository,
    notification_repository,
)
from app.services import notification_service, settings_service

logger = structlog.get_logger()

EXPORT_DIR = "./data/exports"


def _to_item(exam: dict) -> ExamItem:
    return ExamItem(**exam)


async def list_exams(
    tenant_code: str,
    status: str,
    keyword: str,
    page: int,
    page_size: int,
) -> ExamListResponse:
    items, total, counts = await admin_exam_repository.list_exams(
        tenant_code, status, keyword, page, page_size
    )
    return ExamListResponse(
        items=[_to_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        counts=counts,
    )


async def create_exam(
    tenant_code: str,
    req: ExamCreateRequest,
    created_by: str,
) -> ExamItem:
    bank = await admin_exam_repository.get_bank_by_name(tenant_code, req.bank_name)
    if bank is None:
        raise AdminExamError("题库不存在")

    exam_id = await admin_exam_repository.create_exam(
        tenant_code=tenant_code,
        title=req.title,
        bank_id=bank["id"],
        question_count=req.question_count,
        pass_score=req.pass_score,
        duration_minutes=req.duration_minutes,
        max_attempts=req.max_attempts,
        start_at=req.start_at,
        end_at=req.end_at,
        created_by=created_by,
    )
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("创建考试失败")
    return _to_item(exam)


async def get_exam_detail(tenant_code: str, exam_id: int) -> ExamDetailResponse:
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")
    distribution = await admin_exam_repository.get_distribution(tenant_code, exam_id)
    cards = await knowledge_card_repository.list_cards_by_exam(tenant_code, exam_id)
    return ExamDetailResponse(
        **_to_item(exam).model_dump(),
        distribution=distribution,
        weak_points=[],
        card_titles=[card["title"] for card in cards],
    )


async def get_exam_knowledge_cards(
    tenant_code: str,
    exam_id: int,
) -> list[KnowledgeCardItem]:
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")
    cards = await knowledge_card_repository.list_cards_by_exam(tenant_code, exam_id)
    return [KnowledgeCardItem(**card) for card in cards]


async def set_exam_knowledge_cards(
    tenant_code: str,
    exam_id: int,
    card_ids: list[int],
) -> list[KnowledgeCardItem]:
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")
    if exam["status"] != "draft":
        raise AdminExamError("只有草稿考试可以调整知识卡")

    published_ids = await knowledge_card_repository.list_published_card_ids(
        tenant_code, card_ids
    )
    if set(published_ids) != set(card_ids):
        raise AdminExamError("存在未发布或不属于当前租户的知识卡")

    await knowledge_card_repository.set_exam_cards(tenant_code, exam_id, card_ids)
    return await get_exam_knowledge_cards(tenant_code, exam_id)


async def get_exam_assignments(
    tenant_code: str,
    exam_id: int,
) -> dict:
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")
    employee_ids = await admin_exam_repository.list_assigned_employee_ids(exam_id)
    return {"employee_ids": employee_ids, "assigned": len(employee_ids)}


async def assign_exam(
    tenant_code: str,
    exam_id: int,
    scope: str,
    org_ids: list[int],
    employee_ids: list[int],
) -> dict:
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")
    if exam["status"] not in {"draft", "published"}:
        raise AdminExamError("考试已关闭，不能调整指派")

    resolved_ids: list[int] = []
    if scope == "all":
        resolved_ids = await admin_org_repository.list_active_employee_ids(tenant_code)
    elif scope == "org":
        paths: list[str] = []
        for org_id in org_ids:
            org = await admin_org_repository.get_org(tenant_code, org_id)
            if org is None:
                raise AdminExamError("部门不存在")
            paths.append(org["path"])
        resolved_ids = await admin_exam_repository.list_employee_ids_by_org_paths(
            tenant_code, paths
        )
    elif scope == "employees":
        resolved_ids = await admin_exam_repository.list_active_employee_ids_by_ids(
            tenant_code, employee_ids
        )
    else:
        raise AdminExamError("不支持的指派方式")

    if not resolved_ids:
        raise AdminExamError("指派对象为空或已停用，请重新选择")

    if exam["status"] == "published":
        # 已发布考试只做追加：保留已有指派，避免已参加考试的员工被移除
        existing = await admin_exam_repository.list_assigned_employee_ids(exam_id)
        merged = sorted(set(existing) | set(resolved_ids))
        new_ids = sorted(set(merged) - set(existing))
        assigned = await admin_exam_repository.replace_assignments(
            tenant_code, exam_id, merged
        )
        if new_ids:
            await _notify_assigned_added(tenant_code, exam_id, exam, new_ids)
        return {"assigned": assigned, "employee_ids": merged, "added": len(new_ids)}

    assigned = await admin_exam_repository.replace_assignments(
        tenant_code, exam_id, resolved_ids
    )
    return {"assigned": assigned, "employee_ids": resolved_ids, "added": 0}


async def _notify_assigned_added(
    tenant_code: str,
    exam_id: int,
    exam: dict,
    employee_ids: list[int],
) -> None:
    try:
        settings = await settings_service.get_settings(tenant_code)
        if not settings.notify_assigned:
            return
        await notification_service.notify_exam_assigned(
            tenant_code,
            exam_id,
            exam["title"],
            employee_ids,
            end_at=exam.get("end_at"),
            question_count=exam.get("question_count"),
        )
    except Exception as exc:
        logger.error(
            "exam_assignment_notify_failed",
            tenant_code=tenant_code,
            exam_id=exam_id,
            error=str(exc),
            exc_info=True,
        )


async def get_notify_preview(tenant_code: str, exam_id: int) -> dict:
    """发布前预览：本次会通知多少人、其中多少人已绑定微信。"""
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")

    employee_ids = await admin_exam_repository.list_assigned_employee_ids(exam_id)
    if not employee_ids:
        # 未配置指派时，发布逻辑会回退为全部在职员工
        employee_ids = await admin_org_repository.list_active_employee_ids(tenant_code)

    bound = await notification_repository.count_bound_wechat(employee_ids)
    return {"assigned": len(employee_ids), "bound_wechat": bound}


async def publish_exam(tenant_code: str, exam_id: int) -> ExamItem:
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")
    if exam["status"] != "draft":
        raise AdminExamError("只有草稿考试可以发布")

    cards = await knowledge_card_repository.list_cards_by_exam(tenant_code, exam_id)
    if cards:
        published = await knowledge_card_repository.list_published_card_ids(
            tenant_code, [card["id"] for card in cards]
        )
        if len(published) != len(cards):
            raise AdminExamError("有关联知识卡已下线，请重新关联后再发布")

    try:
        assigned = await admin_exam_repository.publish_exam(tenant_code, exam_id)
    except ValueError as exc:
        raise AdminExamError(str(exc)) from exc

    updated = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if updated is None:
        raise AdminExamError("考试不存在")
    await _notify_publish(tenant_code, exam_id, updated)
    logger.info("exam_published", tenant_code=tenant_code, exam_id=exam_id, assigned=assigned)
    return _to_item(updated)


async def _notify_publish(tenant_code: str, exam_id: int, exam: dict) -> None:
    """发布后通知被指派员工；通知失败不影响发布结果。"""
    try:
        settings = await settings_service.get_settings(tenant_code)
        if not settings.notify_assigned:
            return
        employee_ids = await admin_exam_repository.list_assigned_employee_ids(exam_id)
        await notification_service.notify_exam_assigned(
            tenant_code,
            exam_id,
            exam["title"],
            employee_ids,
            end_at=exam.get("end_at"),
            question_count=exam.get("question_count"),
        )
    except Exception as exc:
        logger.error(
            "exam_publish_notify_failed",
            tenant_code=tenant_code,
            exam_id=exam_id,
            error=str(exc),
            exc_info=True,
        )


async def close_exam(tenant_code: str, exam_id: int) -> ExamItem:
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")
    if exam["status"] != "published":
        raise AdminExamError("只有进行中的考试可以关闭")

    await admin_exam_repository.close_exam(tenant_code, exam_id)
    updated = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if updated is None:
        raise AdminExamError("考试不存在")
    await _notify_closed(tenant_code, exam_id, updated)
    return _to_item(updated)


async def _notify_closed(tenant_code: str, exam_id: int, exam: dict) -> None:
    """关闭考试后提醒尚未完成的员工；通知失败不影响关闭。"""
    try:
        settings = await settings_service.get_settings(tenant_code)
        if not settings.notify_assigned:
            return
        employee_ids = await admin_exam_repository.list_incomplete_employee_ids(exam_id)
        await notification_service.notify_exam_closed(
            tenant_code, exam_id, exam["title"], employee_ids
        )
    except Exception as exc:
        logger.error(
            "exam_close_notify_failed",
            tenant_code=tenant_code,
            exam_id=exam_id,
            error=str(exc),
            exc_info=True,
        )


async def export_exam(
    tenant_code: str,
    exam_id: int,
    created_by: str,
) -> ExportTaskItem:
    exam = await admin_exam_repository.get_exam(tenant_code, exam_id)
    if exam is None:
        raise AdminExamError("考试不存在")

    rows = await export_repository.list_exam_attempts(tenant_code, exam_id)
    if not rows:
        raise AdminExamError("暂无成绩可导出")

    os.makedirs(EXPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", exam["title"])
    file_name = f"{safe_title}-成绩-{timestamp}.xlsx"
    file_path = os.path.join(EXPORT_DIR, f"{tenant_code}_{exam_id}_{timestamp}.xlsx")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "成绩明细"
    sheet.append(["工号", "姓名", "部门", "分数", "是否通过", "提交时间", "重考次数", "状态"])
    for row in rows:
        sheet.append(
            [
                row["employee_no"],
                row["name"],
                row["org_path"],
                row["score"],
                "是" if row["passed"] else "否",
                row["submitted_at"],
                row.get("attempt_count", 1),
                "已完成",
            ]
        )
    for column, width in {
        "A": 16,
        "B": 14,
        "C": 36,
        "D": 10,
        "E": 10,
        "F": 22,
        "G": 12,
        "H": 10,
    }.items():
        sheet.column_dimensions[column].width = width
    workbook.save(file_path)

    task_id = await export_repository.create_task(
        tenant_code=tenant_code,
        exam_id=exam_id,
        file_name=file_name,
        export_type="成绩明细",
        status="ready",
        rows=len(rows),
        file_path=file_path,
        created_by=created_by,
    )
    task = await export_repository.get_task(tenant_code, task_id)
    if task is None:
        raise AdminExamError("导出任务创建失败")
    return ExportTaskItem(**task)


async def list_export_tasks(tenant_code: str) -> ExportTaskListResponse:
    rows = await export_repository.list_tasks(tenant_code)
    return ExportTaskListResponse(
        items=[ExportTaskItem(**row) for row in rows],
        total=len(rows),
    )


async def get_export_task(tenant_code: str, task_id: int) -> dict:
    task = await export_repository.get_task(tenant_code, task_id)
    if task is None:
        raise AdminExamError("导出任务不存在")
    return task
