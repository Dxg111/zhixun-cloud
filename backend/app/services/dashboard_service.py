"""管理后台工作台服务"""

from __future__ import annotations

from app.models.admin_exam import DashboardResponse, DashboardTrendPoint, ExamItem
from app.repositories import admin_exam_repository


def _trend_label(exam: dict) -> str:
    value = exam.get("created_at") or exam.get("end_at") or ""
    if len(value) >= 10:
        return value[5:10].replace("-", "/")
    return value


async def get_dashboard(tenant_code: str) -> DashboardResponse:
    counts = await admin_exam_repository.dashboard_counts(tenant_code)
    exams, _, _ = await admin_exam_repository.list_exams(
        tenant_code=tenant_code,
        status="all",
        keyword="",
        page=1,
        page_size=20,
    )

    # 趋势只统计已发布的考试，按创建时间取最近 6 场。
    published = [
        exam
        for exam in exams
        if exam["status"] != "draft" and exam["assigned"] > 0
    ]
    published.sort(key=lambda exam: exam.get("created_at") or "")
    trend_rows = published[-6:]

    trend = [
        DashboardTrendPoint(
            exam_id=exam["id"],
            label=_trend_label(exam),
            title=exam["title"],
            assigned=exam["assigned"],
            completed=exam["completed"],
            completion_rate=round(exam["completed"] / exam["assigned"] * 100)
            if exam["assigned"]
            else 0,
            pass_rate=exam["pass_rate"],
        )
        for exam in trend_rows
    ]

    # 目前成绩只存总分，没有逐题作答明细，薄弱知识点暂返回空。
    return DashboardResponse(
        pending_questions=counts["pending_questions"],
        pending_cards=counts["pending_cards"],
        pending_join_requests=counts["pending_join_requests"],
        active_exams=counts["active_exams"],
        completion_rate=counts["completion_rate"],
        recent_exams=[ExamItem(**item) for item in exams[:3]],
        trend=trend,
        weak_points=[],
    )
