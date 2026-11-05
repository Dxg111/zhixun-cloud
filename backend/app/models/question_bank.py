"""题库审核模型"""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.quiz import QuestionOption

QuestionStatus = Literal["draft", "approved", "rejected"]


class AdminQuestionItem(BaseModel):
    id: int
    tenant_code: str
    bank_id: int
    bank_name: str
    type: Literal["single", "multiple", "judge"]
    stem: str
    options: list[QuestionOption]
    answer: list[str]
    explanation: str
    knowledge_point: str
    difficulty: Literal["easy", "medium", "hard"]
    source: str
    status: QuestionStatus
    ai_meta: str
    review_note: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    created_at: str
    updated_at: str


class QuestionCounts(BaseModel):
    all: int = 0
    draft: int = 0
    approved: int = 0
    rejected: int = 0


class QuestionBankItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    approved_count: int = 0
    total_count: int = 0


class QuestionBankListResponse(BaseModel):
    items: list[QuestionBankItem]
    total: int


class QuestionListResponse(BaseModel):
    items: list[AdminQuestionItem]
    total: int
    page: int
    page_size: int
    counts: QuestionCounts


class QuestionReviewRequest(BaseModel):
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


class QuestionUpdateRequest(BaseModel):
    stem: str = Field(min_length=1, max_length=2000)
    options: list[QuestionOption] = Field(min_length=2, max_length=8)
    answer: list[str] = Field(min_length=1, max_length=8)
    explanation: str = Field(default="", max_length=2000)
    knowledge_point: str = Field(default="", max_length=200)
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class QuestionBulkReviewRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)
    action: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


class QuestionBulkReviewResponse(BaseModel):
    updated: int


class GenerateQuestionsRequest(BaseModel):
    bank_name: str = Field(default="AI 生成题库", min_length=1, max_length=200)
    question_count: int = Field(default=5, ge=3, le=10)
    difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed"


class GenerateQuestionsResponse(BaseModel):
    created: int
    bank_id: int
    bank_name: str
    skipped_duplicates: int = 0

