"""管理后台认证模型"""

from typing import Literal

from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    tenant_code: str = Field(min_length=1, max_length=64, description="租户编码")
    login_name: str = Field(min_length=1, max_length=64, description="管理员登录名")
    password: str = Field(min_length=1, max_length=128, description="管理员密码")


class AdminUser(BaseModel):
    id: int = 0
    name: str
    role: str
    tenant_code: str


class AdminLoginResponse(BaseModel):
    token: str
    user: AdminUser


class AdminUserItem(BaseModel):
    id: int
    tenant_code: str
    login_name: str
    display_name: str
    role: str
    status: Literal["active", "disabled"]
    created_at: str
    updated_at: str


class AdminUserListResponse(BaseModel):
    items: list[AdminUserItem]


class AdminStatusUpdateRequest(BaseModel):
    status: Literal["active", "disabled"]


class AdminCreateRequest(BaseModel):
    login_name: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9_.-]+$",
        description="登录名，只允许字母、数字、下划线、点和短横线",
    )
    display_name: str = Field(min_length=1, max_length=100, description="显示名称")
    password: str = Field(min_length=8, max_length=128, description="初始密码，至少 8 位")


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128, description="新密码，至少 8 位")
