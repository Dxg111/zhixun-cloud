"""员工登录与答题模型"""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.quiz import QuestionOption


class EmployeeLoginRequest(BaseModel):
    tenant_code: str = Field(min_length=1, max_length=64)
    invite_code: str = Field(min_length=1, max_length=32)


class EmployeeInfo(BaseModel):
    id: int
    tenant_code: str
    employee_no: str
    name: str
    org_path: str


class EmployeeLoginResponse(BaseModel):
    token: str
    employee: EmployeeInfo


class EmployeeExamItem(BaseModel):
    id: int
    title: str
    question_count: int
    duration_minutes: int
    pass_score: int
    max_attempts: int
    start_at: str | None = None
    end_at: str | None = None
    status: Literal["published", "closed"]
    assigned_at: str
    attempt_id: int | None = None
    attempt_status: str | None = None
    attempt_count: int = 0
    score: float | None = None
    passed: bool | None = None
    submitted_at: str | None = None


class EmployeeExamListResponse(BaseModel):
    items: list[EmployeeExamItem]


class PaperQuestion(BaseModel):
    id: int
    type: Literal["single", "multiple", "judge"]
    stem: str
    options: list[QuestionOption]
    score: float


class SavedAnswer(BaseModel):
    question_id: int
    selected: list[str] = []


class EmployeePaperResponse(BaseModel):
    attempt_id: int
    exam_id: int
    title: str
    duration_minutes: int
    expires_at: str
    questions: list[PaperQuestion]
    saved_answers: list[SavedAnswer] = []


class EmployeeAnswerInput(BaseModel):
    question_id: int
    selected: list[str] = Field(default_factory=list)
    duration_ms: int = Field(default=0, ge=0)


class EmployeeAnswersRequest(BaseModel):
    answers: list[EmployeeAnswerInput] = Field(default_factory=list)


class EmployeeResultDetail(BaseModel):
    question_id: int
    type: Literal["single", "multiple", "judge"]
    stem: str
    selected: list[str]
    answer: list[str]
    is_correct: bool
    explanation: str
    score: float


class EmployeeResultResponse(BaseModel):
    attempt_id: int
    exam_id: int
    title: str
    score: float
    passed: bool
    correct_count: int
    total_count: int
    submitted_at: str
    details: list[EmployeeResultDetail]
