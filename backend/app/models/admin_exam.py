"""考试、导出、工作台模型"""

from typing import Literal

from pydantic import BaseModel, Field


class ExamItem(BaseModel):
    id: int
    tenant_code: str
    title: str
    bank_id: int
    bank_name: str
    question_count: int
    pass_score: int
    duration_minutes: int
    max_attempts: int
    start_at: str | None = None
    end_at: str | None = None
    status: Literal["draft", "published", "closed"]
    assigned: int
    completed: int
    pass_rate: int
    card_view_rate: int
    created_at: str


class ExamListResponse(BaseModel):
    items: list[ExamItem]
    total: int
    page: int
    page_size: int
    counts: dict[str, int]


class ExamCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    bank_name: str = Field(min_length=1, max_length=200)
    question_count: int = Field(default=5, ge=1, le=100)
    pass_score: int = Field(default=60, ge=0, le=100)
    duration_minutes: int = Field(default=30, ge=5, le=180)
    max_attempts: int = Field(default=1, ge=1, le=5)
    start_at: str | None = None
    end_at: str | None = None


class ExamDetailResponse(ExamItem):
    distribution: list[int]
    weak_points: list[str]
    card_titles: list[str] = Field(default_factory=list)


class ExamAssignRequest(BaseModel):
    scope: Literal["all", "org", "employees"] = "all"
    org_ids: list[int] = Field(default_factory=list)
    employee_ids: list[int] = Field(default_factory=list)


class ExamAssignResponse(BaseModel):
    assigned: int
    employee_ids: list[int]


class ExamKnowledgeCardsRequest(BaseModel):
    card_ids: list[int] = Field(default_factory=list)


class ExportTaskItem(BaseModel):
    id: int
    tenant_code: str
    exam_id: int | None = None
    file_name: str
    export_type: str
    status: Literal["processing", "ready", "failed"]
    rows: int
    created_at: str


class ExportTaskListResponse(BaseModel):
    items: list[ExportTaskItem]
    total: int


class DashboardResponse(BaseModel):
    pending_questions: int
    pending_cards: int
    pending_join_requests: int
    active_exams: int
    completion_rate: int
    recent_exams: list[ExamItem]
    weak_points: list[dict] = []
