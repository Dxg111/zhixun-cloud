"""组织与员工模型"""

from typing import Literal

from pydantic import BaseModel, Field


class OrgUnitItem(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    path: str
    sort: int
    employee_count: int


class OrgUnitListResponse(BaseModel):
    items: list[OrgUnitItem]


class OrgUnitCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: int | None = None


class EmployeeItem(BaseModel):
    id: int
    tenant_code: str
    org_id: int | None = None
    employee_no: str
    name: str
    role: str
    status: Literal["active", "disabled"]
    invite_code: str
    invite_status: Literal["bound", "unbound"]
    org_path: str
    created_at: str


class EmployeeListResponse(BaseModel):
    items: list[EmployeeItem]
    total: int
    page: int
    page_size: int


class EmployeeCreateRequest(BaseModel):
    employee_no: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    org_id: int | None = None
    role: str = Field(default="员工", min_length=1, max_length=30)


class EmployeeStatusRequest(BaseModel):
    status: Literal["active", "disabled"]


class EmployeeImportResponse(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
