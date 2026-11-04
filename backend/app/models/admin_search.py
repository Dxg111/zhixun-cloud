"""管理后台全局搜索模型"""

from typing import Literal

from pydantic import BaseModel

SearchItemType = Literal["employee", "question", "exam", "card", "document"]


class GlobalSearchItem(BaseModel):
    type: SearchItemType
    id: int
    title: str
    subtitle: str
    status: str
    url: str


class GlobalSearchResponse(BaseModel):
    keyword: str
    total: int
    items: list[GlobalSearchItem]
