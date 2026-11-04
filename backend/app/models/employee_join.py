"""企业加入申请与成员身份模型"""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.employee_exam import EmployeeInfo

JoinRequestStatus = Literal["pending", "approved", "rejected"]


class JoinRequestCreate(BaseModel):
    tenant_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    employee_no: str = Field(min_length=1, max_length=64)
    remark: str | None = Field(default=None, max_length=500)


class JoinRequestItem(BaseModel):
    id: int
    tenant_code: str
    tenant_name: str
    user_id: int
    name: str
    employee_no: str
    org_id: int | None = None
    org_path: str = ""
    role: str
    remark: str | None = None
    status: JoinRequestStatus
    reject_reason: str | None = None
    reviewed_by: str | None = None
    reviewed_at: str = ""
    created_at: str


class JoinRequestListResponse(BaseModel):
    items: list[JoinRequestItem]
    total: int
    page: int
    page_size: int


class JoinRequestApproveRequest(BaseModel):
    org_id: int | None = None
    role: str = Field(default="员工", min_length=1, max_length=30)


class JoinRequestRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class EmployeeMembershipResponse(BaseModel):
    status: Literal["none", "pending", "rejected", "approved", "disabled"]
    tenant_code: str | None = None
    tenant_name: str | None = None
    employee: EmployeeInfo | None = None
    request: JoinRequestItem | None = None
    message: str = ""
