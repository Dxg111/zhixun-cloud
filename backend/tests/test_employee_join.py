"""企业加入申请与审核测试"""

import pytest

from app.models.employee_join import JoinRequestApproveRequest, JoinRequestCreate
from app.repositories import admin_org_repository, employee_join_repository, settings_repository
from app.services import employee_join_service


def _request_row(status: str = "pending") -> dict:
    return {
        "id": 11,
        "tenant_code": "demo",
        "tenant_name": "演示企业",
        "user_id": 7,
        "name": "张三",
        "employee_no": "E1009",
        "org_id": None,
        "org_path": "",
        "role": "员工",
        "remark": "测试申请",
        "status": status,
        "reject_reason": None,
        "reviewed_by": None,
        "reviewed_at": "",
        "created_at": "2026-11-04 10:00:00",
    }


def _employee(user_id: int | None = None) -> dict:
    return {
        "id": 9,
        "tenant_code": "demo",
        "org_id": 3,
        "user_id": user_id,
        "employee_no": "E1009",
        "name": "张三",
        "role": "员工",
        "status": "active",
        "org_path": "华东区/上海门店/徐汇店",
        "created_at": "2026-11-04 10:00:00",
    }


@pytest.mark.asyncio
async def test_submit_join_request_creates_pending(monkeypatch):
    async def no_employee(user_id: int):
        return None

    async def no_pending(user_id: int):
        return None

    async def settings(tenant_code: str):
        return {"tenant_code": tenant_code, "tenant_name": "演示企业"}

    async def no_employee_no(tenant_code: str, employee_no: str):
        return None

    async def create_request(tenant_code, user_id, name, employee_no, remark):
        return 11

    async def get_request(tenant_code: str, request_id: int):
        return _request_row()

    monkeypatch.setattr(admin_org_repository, "find_employee_by_user", no_employee)
    monkeypatch.setattr(employee_join_repository, "get_pending_request_for_user", no_pending)
    monkeypatch.setattr(settings_repository, "get_settings", settings)
    monkeypatch.setattr(admin_org_repository, "find_employee_by_no", no_employee_no)
    monkeypatch.setattr(employee_join_repository, "create_request", create_request)
    monkeypatch.setattr(employee_join_repository, "get_request", get_request)

    result = await employee_join_service.submit_join_request(
        7,
        JoinRequestCreate(tenant_code="demo", name="张三", employee_no="E1009"),
    )
    assert result.status == "pending"
    assert result.tenant_name == "演示企业"


@pytest.mark.asyncio
async def test_membership_returns_approved_employee(monkeypatch):
    async def find_employee(user_id: int):
        return _employee(user_id)

    async def settings(tenant_code: str):
        return {"tenant_code": tenant_code, "tenant_name": "演示企业"}

    monkeypatch.setattr(admin_org_repository, "find_employee_by_user", find_employee)
    monkeypatch.setattr(settings_repository, "get_settings", settings)

    result = await employee_join_service.get_membership(7)
    assert result.status == "approved"
    assert result.employee is not None
    assert result.employee.name == "张三"


@pytest.mark.asyncio
async def test_approve_binds_existing_employee(monkeypatch):
    calls = {"bind": None, "approved": False}

    async def get_request(tenant_code: str, request_id: int):
        return _request_row()

    async def no_employee(user_id: int):
        return None

    async def existing(tenant_code: str, employee_no: str):
        return _employee(None)

    async def get_org(tenant_code: str, org_id: int):
        return {"id": org_id, "path": "华东区/上海门店/徐汇店"}

    async def update_assignment(**kwargs):
        return 1

    async def bind(tenant_code, employee_id, user_id):
        calls["bind"] = (tenant_code, employee_id, user_id)
        return 1

    async def mark_approved(**kwargs):
        calls["approved"] = True
        return 1

    async def updated_request(tenant_code: str, request_id: int):
        row = _request_row("approved")
        row["org_id"] = 3
        row["org_path"] = "华东区/上海门店/徐汇店"
        return row

    monkeypatch.setattr(employee_join_repository, "get_request", get_request)
    monkeypatch.setattr(admin_org_repository, "find_employee_by_user", no_employee)
    monkeypatch.setattr(admin_org_repository, "find_employee_by_no", existing)
    monkeypatch.setattr(admin_org_repository, "get_org", get_org)
    monkeypatch.setattr(admin_org_repository, "update_employee_assignment", update_assignment)
    monkeypatch.setattr(admin_org_repository, "bind_employee_user", bind)
    monkeypatch.setattr(employee_join_repository, "mark_approved", mark_approved)
    # 第二次 get_request 返回已通过记录
    original = get_request
    state = {"count": 0}

    async def get_request_sequence(tenant_code: str, request_id: int):
        state["count"] += 1
        return await (original(tenant_code, request_id) if state["count"] == 1 else updated_request(tenant_code, request_id))

    monkeypatch.setattr(employee_join_repository, "get_request", get_request_sequence)

    result = await employee_join_service.approve_request(
        "demo",
        11,
        "李培训",
        JoinRequestApproveRequest(org_id=3, role="员工"),
    )
    assert result.status == "approved"
    assert calls["bind"] == ("demo", 9, 7)
    assert calls["approved"] is True
