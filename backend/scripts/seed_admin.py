"""创建或重置管理后台账号。

用法：
    cd backend
    python scripts/seed_admin.py

账号信息来自环境变量（或 .env）：
    ADMIN_TENANT_CODE=demo
    ADMIN_LOGIN_NAME=admin
    ADMIN_PASSWORD=demo1234
    ADMIN_DISPLAY_NAME=李培训
"""

import asyncio
import sys
from pathlib import Path

# 允许直接执行 scripts/seed_admin.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.db import close_mysql_pool, init_mysql  # noqa: E402
from app.core.passwords import hash_password  # noqa: E402
from app.repositories import admin_user_repository  # noqa: E402


async def seed_admin() -> None:
    settings = get_settings()
    await init_mysql()
    try:
        await admin_user_repository.upsert_admin(
            tenant_code=settings.admin_tenant_code,
            login_name=settings.admin_login_name,
            password_hash=hash_password(settings.admin_password),
            display_name=settings.admin_display_name,
            role="tenant_admin",
        )
        print(
            "管理员账号已就绪："
            f"{settings.admin_tenant_code}/{settings.admin_login_name} "
            f"({settings.admin_display_name})"
        )
    finally:
        await close_mysql_pool()


if __name__ == "__main__":
    asyncio.run(seed_admin())
