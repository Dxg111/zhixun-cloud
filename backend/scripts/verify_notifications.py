"""P0 通知链路自检

验证：
1. notifications 表已创建；
2. 通知写入 -> 员工 summary 未读 -> 按业务标记已读 的完整链路；
3. 管理端发布预览接口可用。

脚本会自动清理自己写入的测试通知，不会改动业务数据。
运行：python scripts/verify_notifications.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.auth import create_employee_token  # noqa: E402
from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
TEST_BIZ_ID = 999_999_999


async def _pick_employee() -> tuple[int, str, str, str] | None:
    pool = get_mysql_pool()
    if pool is None:
        return None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, tenant_code, name, employee_no FROM employees "
                "WHERE status = 'active' ORDER BY id ASC LIMIT 1"
            )
            row = await cur.fetchone()
    if not row:
        return None
    return int(row[0]), row[1], row[2], row[3]


async def _cleanup(employee_id: int) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM notifications WHERE recipient_id = %s AND biz_id = %s",
                (employee_id, TEST_BIZ_ID),
            )


async def main() -> int:
    await init_mysql()
    employee = await _pick_employee()
    if employee is None:
        print("[FAIL] 数据库中没有在职员工，请先创建员工")
        return 1

    employee_id, tenant_code, name, employee_no = employee
    token = create_employee_token(employee_id, tenant_code, name, employee_no)
    headers = {"Authorization": f"Bearer {token}"}

    failures: list[str] = []

    async with httpx.AsyncClient(base_url=BASE, timeout=20) as client:
        # 1. 写入一条测试通知（走真实服务层）
        from app.services import notification_service

        inserted = await notification_service.notify_recipients(
            tenant_code,
            "employee",
            [employee_id],
            type="exam_assigned",
            title="通知链路自检",
            content="这是一条自检通知，脚本结束后会自动删除",
            link_page="pages/employee-exams/index",
            biz_type="exam",
            biz_id=TEST_BIZ_ID,
        )
        print(f"[INFO] 写入通知 {inserted} 条（employee_id={employee_id}）")

        # 2. 员工未读数
        resp = await client.get("/employee/notifications/summary", headers=headers)
        body = resp.json()
        data = body.get("data") or {}
        unread = data.get("unread_count", 0)
        unread_exam_ids = data.get("unread_exam_ids", [])
        pending = data.get("pending_exam_count", 0)
        print(
            f"[INFO] summary: unread={unread} unread_exam_ids={unread_exam_ids} "
            f"pending_exams={pending}"
        )
        if resp.status_code != 200 or body.get("code") != 0:
            failures.append(f"summary 接口异常: {resp.status_code} {body}")
        elif TEST_BIZ_ID not in unread_exam_ids:
            failures.append("summary 未返回刚写入的未读考试 id")

        # 3. 按业务标记已读
        resp = await client.post(
            "/employee/notifications/read-by-biz",
            headers=headers,
            json={"biz_type": "exam", "biz_id": TEST_BIZ_ID},
        )
        body = resp.json()
        updated = (body.get("data") or {}).get("updated", 0)
        print(f"[INFO] 标记已读 {updated} 条")
        if resp.status_code != 200 or body.get("code") != 0:
            failures.append(f"read-by-biz 接口异常: {resp.status_code} {body}")
        elif updated < 1:
            failures.append("read-by-biz 未更新任何记录")

        # 4. 已读后不再出现在未读列表
        resp = await client.get("/employee/notifications/summary", headers=headers)
        data = resp.json().get("data") or {}
        if TEST_BIZ_ID in data.get("unread_exam_ids", []):
            failures.append("标记已读后仍出现在 unread_exam_ids")
        print(f"[INFO] 已读后 unread={data.get('unread_count', 0)}")

        # 5. 管理端发布预览（账号密码取 .env，便于本地/测试环境复用）
        from app.core.config import get_settings

        settings = get_settings()
        login = await client.post(
            "/auth/admin/login",
            json={
                "tenant_code": "demo",
                "login_name": settings.admin_login_name,
                "password": settings.admin_password,
            },
        )
        login_data = login.json().get("data") or {}
        admin_token = login_data.get("token")
        if not admin_token:
            print(f"[WARN] 管理员登录失败，跳过发布预览检查: {login.text[:200]}")
        else:
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            exams = await client.get("/admin/exams?page_size=1", headers=admin_headers)
            items = ((exams.json().get("data") or {}).get("items")) or []
            if not items:
                print("[WARN] 没有考试，跳过发布预览检查")
            else:
                exam_id = items[0]["id"]
                preview = await client.get(
                    f"/admin/exams/{exam_id}/notify-preview", headers=admin_headers
                )
                preview_body = preview.json()
                print(
                    f"[INFO] notify-preview(exam_id={exam_id}): "
                    f"{preview_body.get('data')}"
                )
                if preview.status_code != 200 or preview_body.get("code") != 0:
                    failures.append(
                        f"notify-preview 接口异常: {preview.status_code} {preview_body}"
                    )

    await _cleanup(employee_id)
    await close_mysql_pool()

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        return 1

    print("[PASS] 通知链路自检通过")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
