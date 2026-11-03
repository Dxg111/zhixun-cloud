"""员工学习：知识卡与错题模型"""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.quiz import QuestionOption


class EmployeeCardPoint(BaseModel):
    heading: str
    body: str


class EmployeeCardItem(BaseModel):
    id: int
    title: str
    excerpt: str
    source: str
    points: list[EmployeeCardPoint] = Field(default_factory=list)
    viewed: bool = False
    view_count: int = 0


class EmployeeCardListResponse(BaseModel):
    items: list[EmployeeCardItem]
    total: int


class EmployeeWrongQuestionItem(BaseModel):
    id: int
    question_id: int
    type: Literal["single", "multiple", "judge"]
    stem: str
    options: list[QuestionOption]
    knowledge_point: str = ""
    wrong_count: int
    correct_streak: int
    mastered: bool
    last_wrong_at: str


class EmployeeWrongQuestionListResponse(BaseModel):
    items: list[EmployeeWrongQuestionItem]
    total: int


class EmployeeWrongRetryRequest(BaseModel):
    selected: list[str] = Field(default_factory=list)


class EmployeeWrongRetryResponse(BaseModel):
    is_correct: bool
    answer: list[str]
    explanation: str
    correct_streak: int
    mastered: bool


class EmployeeWrongMasterRequest(BaseModel):
    mastered: bool
