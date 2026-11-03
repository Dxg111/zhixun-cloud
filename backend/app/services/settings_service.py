"""租户设置服务"""

from __future__ import annotations

from app.models.admin_console import TenantSettings, TenantSettingsUpdate
from app.repositories import settings_repository


async def _default_settings(tenant_code: str) -> TenantSettings:
    await settings_repository.upsert_settings(
        tenant_code=tenant_code,
        tenant_name="演示企业",
        admin_email="training@demo.com",
        retention="合同期 + 90 天",
        default_pass_score=60,
        default_duration=30,
        default_attempts=1,
        random_order="随机",
        notify_assigned=True,
        notify_result=True,
        notify_deadline=False,
        notify_cards=False,
    )
    row = await settings_repository.get_settings(tenant_code)
    if row is None:
        raise RuntimeError("初始化租户设置失败")
    return TenantSettings(**row)


async def get_settings(tenant_code: str) -> TenantSettings:
    row = await settings_repository.get_settings(tenant_code)
    if row is None:
        return await _default_settings(tenant_code)
    return TenantSettings(**row)


async def update_settings(
    tenant_code: str,
    req: TenantSettingsUpdate,
) -> TenantSettings:
    await settings_repository.upsert_settings(
        tenant_code=tenant_code,
        tenant_name=req.tenant_name,
        admin_email=req.admin_email,
        retention=req.retention,
        default_pass_score=req.default_pass_score,
        default_duration=req.default_duration,
        default_attempts=req.default_attempts,
        random_order=req.random_order,
        notify_assigned=req.notify_assigned,
        notify_result=req.notify_result,
        notify_deadline=req.notify_deadline,
        notify_cards=req.notify_cards,
    )
    row = await settings_repository.get_settings(tenant_code)
    if row is None:
        raise RuntimeError("保存租户设置失败")
    return TenantSettings(**row)
