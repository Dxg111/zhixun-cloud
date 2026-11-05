"""站内通知模型"""

from typing import Literal

from pydantic import BaseModel, Field

NotificationType = Literal[
    "exam_assigned",
    "exam_updated",
    "exam_closed",
    "exam_deadline",
    "result_ready",
    "card_published",
    "join_approved",
    "join_rejected",
]


class NotificationItem(BaseModel):
    id: int
    type: str
    title: str
    content: str = ""
    link_page: str = ""
    link_params: str = ""
    biz_type: str = ""
    biz_id: int | None = None
    read: bool = False
    created_at: str


class NotificationSummary(BaseModel):
    unread_count: int = 0
    # 未读的新考试通知对应的 exam_id，用于考试列表打「新」标签
    unread_exam_ids: list[int] = []
    # 待完成考试数（首页入口展示，避免为了一个数字拉全量列表）
    pending_exam_count: int = 0
    items: list[NotificationItem] = []


class NotificationListResponse(BaseModel):
    items: list[NotificationItem] = []
    total: int = 0
    unread_count: int = 0
    page: int = 1
    page_size: int = 20


class ReadByBizRequest(BaseModel):
    biz_type: str = Field(min_length=1, max_length=30)
    biz_id: int = Field(ge=1)


class ReadExamsRequest(BaseModel):
    """进入考试列表后批量清除新考试提醒。"""

    exam_ids: list[int] = Field(default_factory=list, max_length=100)


class WechatSubscribeReport(BaseModel):
    template_ids: list[str] = Field(default_factory=list, max_length=10)


class NotificationPreferences(BaseModel):
    notify_deadline: bool = True
