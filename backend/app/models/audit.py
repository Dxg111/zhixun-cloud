"""审计日志模型"""

from pydantic import BaseModel, Field


class AuditLogItem(BaseModel):
    id: int
    operator_name: str
    action: str
    target_type: str
    target_id: str
    detail: str = ""
    created_at: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem] = []
    total: int = 0
    page: int = 1
    page_size: int = 20


class AuditLogCreate(BaseModel):
    action: str = Field(min_length=1, max_length=50)
    target_type: str = ""
    target_id: str = ""
    detail: dict | None = None
