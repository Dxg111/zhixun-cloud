"""手动添加员工测试"""

import pytest

from app.core.exceptions import AdminOrgError
from app.models.admin_org import EmployeeCreateRequest
from app.repositories import admin_org_repository
from app.services import admin_org_service


def _employee(employee_id: int = 9) -> dict:
    return {
        "id": employee_id,
        "tenant_code": "demo",
        "org_id": 3,
        "employee_no": "E1009",
        "name": "测试员工",
        "role": "员工",
        "status": "active",
        "invite_code": "ABCD1234",
        "invite_status": "unbound",
        "org_path": "华东区/上海门店/徐汇店",
        "created_at": "2026-11-03 10:00:00",
    }


@pytest.mark.asyncio
async def test_create_employee_success(monkeypatch):
    created = {}

    async def fake_find_no(tenant_code: str, employee_no: str):
        return None

    async def fake_find_invite(tenant_code: str, invite_code: str):
        return None

    async def fake_get_org(tenant_code: str, org_id: int):
        return {"id": org_id, "path": "华东区/上海门店/徐汇店"}

    async def fake_create(tenant_code, org_id, employee_no, name, role, invite_code):
        created.update(
            org_id=org_id,
            employee_no=employee_no,
            name=name,
            role=role,
            invite_code=invite_code,
        )
        return 9

    async def fake_get_employee(tenant_code: str, employee_id: int):
        return _employee(employee_id)

    monkeypatch.setattr(admin_org_repository, "find_employee_by_no", fake_find_no)
    monkeypatch.setattr(admin_org_repository, "find_employee_by_invite", fake_find_invite)
    monkeypatch.setattr(admin_org_repository, "get_org", fake_get_org)
    monkeypatch.setattr(admin_org_repository, "create_employee", fake_create)
    monkeypatch.setattr(admin_org_repository, "get_employee", fake_get_employee)

    result = await admin_org_service.create_employee(
        "demo",
        EmployeeCreateRequest(
            employee_no=" E1009 ",
            name=" 测试员工 ",
            org_id=3,
            role="员工",
        ),
    )

    assert result.id == 9
    assert result.employee_no == "E1009"
    assert created["name"] == "测试员工"
    assert created["org_id"] == 3


@pytest.mark.asyncio
async def test_create_employee_rejects_duplicate(monkeypatch):
    async def fake_find_no(tenant_code: str, employee_no: str):
        return _employee()

    monkeypatch.setattr(admin_org_repository, "find_employee_by_no", fake_find_no)

    with pytest.raises(AdminOrgError, match="已存在"):
        await admin_org_service.create_employee(
            "demo",
            EmployeeCreateRequest(employee_no="E1009", name="测试员工", org_id=3, role="员工"),
        )
