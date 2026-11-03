"""管理后台账号列表与停用测试"""

import pytest

from app.core.exceptions import AdminUserError
from app.core.passwords import verify_password
from app.models.auth import AdminCreateRequest
from app.repositories import admin_user_repository
from app.services import admin_user_service


def _admin(admin_id: int = 1, login_name: str = "admin", status: str = "active") -> dict:
    return {
        "id": admin_id,
        "tenant_code": "demo",
        "login_name": login_name,
        "display_name": "李培训" if login_name == "admin" else "运营管理员",
        "role": "tenant_admin",
        "status": status,
        "created_at": "2026-11-02 12:00:00",
        "updated_at": "2026-11-02 12:00:00",
    }


@pytest.mark.asyncio
async def test_list_admins(monkeypatch):
    rows = [_admin(), _admin(2, "ops", "disabled")]

    async def fake_list(tenant_code: str):
        return rows

    monkeypatch.setattr(admin_user_repository, "list_admins", fake_list)

    result = await admin_user_service.list_admins("demo")

    assert len(result.items) == 2
    assert result.items[0].login_name == "admin"
    assert result.items[1].status == "disabled"


@pytest.mark.asyncio
async def test_cannot_disable_self(monkeypatch):
    async def fake_get(tenant_code: str, admin_id: int):
        return _admin(1, "admin", "active")

    monkeypatch.setattr(admin_user_repository, "get_admin_by_id", fake_get)

    with pytest.raises(AdminUserError, match="当前登录账号"):
        await admin_user_service.update_admin_status("demo", 1, "disabled", "admin")


@pytest.mark.asyncio
async def test_cannot_disable_last_active_admin(monkeypatch):
    async def fake_get(tenant_code: str, admin_id: int):
        return _admin(2, "ops", "active")

    async def fake_count(tenant_code: str):
        return 1

    monkeypatch.setattr(admin_user_repository, "get_admin_by_id", fake_get)
    monkeypatch.setattr(admin_user_repository, "count_active_admins", fake_count)

    with pytest.raises(AdminUserError, match="至少保留一个"):
        await admin_user_service.update_admin_status("demo", 2, "disabled", "admin")


@pytest.mark.asyncio
async def test_disable_other_admin(monkeypatch):
    admin = _admin(2, "ops", "active")

    async def fake_get(tenant_code: str, admin_id: int):
        return admin

    async def fake_count(tenant_code: str):
        return 2

    async def fake_set(tenant_code: str, admin_id: int, status: str):
        admin["status"] = status

    monkeypatch.setattr(admin_user_repository, "get_admin_by_id", fake_get)
    monkeypatch.setattr(admin_user_repository, "count_active_admins", fake_count)
    monkeypatch.setattr(admin_user_repository, "set_admin_status", fake_set)

    result = await admin_user_service.update_admin_status("demo", 2, "disabled", "admin")

    assert result.status == "disabled"


@pytest.mark.asyncio
async def test_create_admin_success(monkeypatch):
    async def fake_find(tenant_code: str, login_name: str):
        return None

    async def fake_create(tenant_code: str, login_name: str, password_hash: str, display_name: str, role: str):
        return 3

    async def fake_get(tenant_code: str, admin_id: int):
        return _admin(3, "ops")

    monkeypatch.setattr(admin_user_repository, "find_admin_by_login", fake_find)
    monkeypatch.setattr(admin_user_repository, "create_admin", fake_create)
    monkeypatch.setattr(admin_user_repository, "get_admin_by_id", fake_get)

    result = await admin_user_service.create_admin(
        "demo",
        AdminCreateRequest(login_name="ops", display_name="运营管理员", password="ops12345"),
    )

    assert result.id == 3
    assert result.login_name == "ops"


@pytest.mark.asyncio
async def test_create_admin_rejects_duplicate_login(monkeypatch):
    async def fake_find(tenant_code: str, login_name: str):
        return _admin(2, "ops")

    monkeypatch.setattr(admin_user_repository, "find_admin_by_login", fake_find)

    with pytest.raises(AdminUserError, match="已存在"):
        await admin_user_service.create_admin(
            "demo",
            AdminCreateRequest(login_name="ops", display_name="运营管理员", password="ops12345"),
        )


@pytest.mark.asyncio
async def test_reset_admin_password(monkeypatch):
    admin = _admin(2, "ops")
    captured = {}

    async def fake_get(tenant_code: str, admin_id: int):
        return admin

    async def fake_update(tenant_code: str, admin_id: int, password_hash: str):
        captured["hash"] = password_hash

    monkeypatch.setattr(admin_user_repository, "get_admin_by_id", fake_get)
    monkeypatch.setattr(admin_user_repository, "update_admin_password", fake_update)

    result = await admin_user_service.reset_admin_password("demo", 2, "newpass123")

    assert result.id == 2
    assert verify_password("newpass123", captured["hash"]) is True


@pytest.mark.asyncio
async def test_reset_password_rejects_unknown_admin(monkeypatch):
    async def fake_get(tenant_code: str, admin_id: int):
        return None

    monkeypatch.setattr(admin_user_repository, "get_admin_by_id", fake_get)

    with pytest.raises(AdminUserError, match="不存在"):
        await admin_user_service.reset_admin_password("demo", 999, "newpass123")


@pytest.mark.asyncio
async def test_enable_admin(monkeypatch):
    admin = _admin(2, "ops", "disabled")

    async def fake_get(tenant_code: str, admin_id: int):
        return admin

    async def fake_set(tenant_code: str, admin_id: int, status: str):
        admin["status"] = status

    monkeypatch.setattr(admin_user_repository, "get_admin_by_id", fake_get)
    monkeypatch.setattr(admin_user_repository, "set_admin_status", fake_set)

    result = await admin_user_service.update_admin_status("demo", 2, "active", "admin")

    assert result.status == "active"
