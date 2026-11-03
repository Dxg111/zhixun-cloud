"""管理后台文档与设置模型"""

from typing import Literal

from pydantic import BaseModel, Field


class DocumentItem(BaseModel):
    id: int
    tenant_code: str
    file_name: str
    file_type: str
    file_size: int
    status: Literal["processing", "ready", "failed"]
    chunks: int
    error_message: str | None = None
    has_file: bool = True
    created_at: str


class DocumentListResponse(BaseModel):
    items: list[DocumentItem]
    total: int


class TenantSettings(BaseModel):
    tenant_code: str
    tenant_name: str
    admin_email: str | None = None
    retention: str
    default_pass_score: int
    default_duration: int
    default_attempts: int
    random_order: str
    notify_assigned: bool
    notify_result: bool
    notify_deadline: bool
    notify_cards: bool
    updated_at: str


class TenantSettingsUpdate(BaseModel):
    tenant_name: str = Field(min_length=1, max_length=200)
    admin_email: str | None = Field(default=None, max_length=200)
    retention: str = Field(default="合同期 + 90 天", max_length=50)
    default_pass_score: int = Field(default=60, ge=0, le=100)
    default_duration: int = Field(default=30, ge=5, le=180)
    default_attempts: int = Field(default=1, ge=1, le=5)
    random_order: Literal["随机", "固定"] = "随机"
    notify_assigned: bool = True
    notify_result: bool = True
    notify_deadline: bool = False
    notify_cards: bool = False
