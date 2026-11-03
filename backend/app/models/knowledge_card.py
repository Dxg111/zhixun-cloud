"""知识卡模型"""

from typing import Literal

from pydantic import BaseModel, Field

CardStatus = Literal["draft", "published", "offline"]


class KnowledgeCardPoint(BaseModel):
    heading: str = Field(min_length=1, max_length=60)
    body: str = Field(min_length=1, max_length=800)


class KnowledgeCardDraft(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    points: list[KnowledgeCardPoint] = Field(min_length=1)
    source_ref: str = Field(default="", max_length=255)


class KnowledgeCardBatchOutput(BaseModel):
    cards: list[KnowledgeCardDraft] = Field(min_length=1)


class KnowledgeCardItem(BaseModel):
    id: int
    tenant_code: str
    doc_id: int | None = None
    doc_name: str
    title: str
    excerpt: str
    source: str
    status: CardStatus
    view_rate: int
    created_by: str | None = None
    published_at: str | None = None
    created_at: str
    updated_at: str


class KnowledgeCardDetail(KnowledgeCardItem):
    points: list[KnowledgeCardPoint] = Field(default_factory=list)


class KnowledgeCardListResponse(BaseModel):
    items: list[KnowledgeCardItem]
    total: int
    page: int
    page_size: int


class KnowledgeCardGenerateRequest(BaseModel):
    doc_id: int | None = Field(default=None, gt=0)
    doc_name: str = Field(default="", max_length=255)
    count: int = Field(default=3, ge=3, le=5)
    style: Literal["操作要点", "概念解释", "易错提醒"] = "操作要点"


class KnowledgeCardUpdateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    excerpt: str = Field(min_length=1, max_length=1000)
    points: list[KnowledgeCardPoint] = Field(default_factory=list)


class KnowledgeCardStatusRequest(BaseModel):
    status: Literal["published", "offline"]
