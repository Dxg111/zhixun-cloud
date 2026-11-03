"""管理后台登录测试"""

import pytest

from app.core.auth import decode_token
from app.core.exceptions import AuthenticationError
from app.core.passwords import hash_password, verify_password
from app.models.auth import AdminLoginRequest
from app.repositories import admin_user_repository
from app.services.admin_auth_service import handle_admin_login

PASSWORD = "demo1234"
PASSWORD_HASH = hash_password(PASSWORD)


@pytest.fixture(autouse=True)
def fake_db_pool(monkeypatch):
    """管理员登录测试不连接真实 MySQL。"""
    monkeypatch.setattr("app.services.admin_auth_service.get_mysql_pool", lambda: object())


def _request(password: str = PASSWORD, tenant_code: str = "demo", login_name: str = "admin"):
    return AdminLoginRequest(
        tenant_code=tenant_code,
        login_name=login_name,
        password=password,
    )


def _fake_find(admin: dict | None):
    async def fake_find(tenant_code: str, login_name: str):
        return admin

    return fake_find


def _admin(status: str = "active", role: str = "tenant_admin") -> dict:
    return {
        "id": 7,
        "tenant_code": "demo",
        "login_name": "admin",
        "password_hash": PASSWORD_HASH,
        "display_name": "李培训",
        "role": role,
        "status": status,
    }


def test_password_hash_roundtrip():
    assert verify_password(PASSWORD, PASSWORD_HASH) is True
    assert verify_password("wrong", PASSWORD_HASH) is False
    assert verify_password(PASSWORD, "not-a-bcrypt-hash") is False


@pytest.mark.asyncio
async def test_admin_login_success(monkeypatch):
    monkeypatch.setattr(admin_user_repository, "find_admin_by_login", _fake_find(_admin()))

    result = await handle_admin_login(_request())

    assert result.user.id == 7
    assert result.user.name == "李培训"
    payload = decode_token(result.token)
    assert payload["role"] == "tenant_admin"
    assert payload["tenant_code"] == "demo"
    assert payload["login_name"] == "admin"


@pytest.mark.asyncio
async def test_admin_login_rejects_wrong_password(monkeypatch):
    monkeypatch.setattr(admin_user_repository, "find_admin_by_login", _fake_find(_admin()))

    with pytest.raises(AuthenticationError):
        await handle_admin_login(_request(password="wrong"))


@pytest.mark.asyncio
async def test_admin_login_rejects_disabled_account(monkeypatch):
    monkeypatch.setattr(
        admin_user_repository,
        "find_admin_by_login",
        _fake_find(_admin(status="disabled")),
    )

    with pytest.raises(AuthenticationError):
        await handle_admin_login(_request())


@pytest.mark.asyncio
async def test_admin_login_rejects_unknown_account(monkeypatch):
    monkeypatch.setattr(admin_user_repository, "find_admin_by_login", _fake_find(None))

    with pytest.raises(AuthenticationError):
        await handle_admin_login(_request())
