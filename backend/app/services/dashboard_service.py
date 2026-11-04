"""管理后台工作台服务"""

from __future__ import annotations

from app.models.admin_exam import DashboardResponse, ExamItem
from app.repositories import admin_exam_repository


async def get_dashboard(tenant_code: str) -> DashboardResponse:
    counts = await admin_exam_repository.dashboard_counts(tenant_code)
    recent, _, _ = await admin_exam_repository.list_exams(
        tenant_code=tenant_code,
        status="all",
        keyword="",
        page=1,
        page_size=3,
    )

    # 目前成绩只存总分，没有逐题作答明细，薄弱知识点暂返回空。
    return DashboardResponse(
        pending_questions=counts["pending_questions"],
        pending_cards=counts["pending_cards"],
        pending_join_requests=counts["pending_join_requests"],
        active_exams=counts["active_exams"],
        completion_rate=counts["completion_rate"],
        recent_exams=[ExamItem(**item) for item in recent],
        weak_points=[],
    )
