"""P2 端到端自动测试

覆盖：
    1. 微信订阅配置接口（未配置模板时应为关闭）
    2. 订阅上报接口（无模板时记录 0）
    3. 员工通知偏好读写
    4. 关闭截止提醒的员工不进入提醒候选
    5. 管理端通知送达统计（已通知/已读/未绑定微信）

运行：python scripts/test_p2_features.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.auth import create_admin_token, create_employee_token  # noqa: E402
from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402
from app.repositories import notification_repository  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
TENANT = "demo"

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")


async def _fixtures():
    pool = get_mysql_pool()
    assert pool is not None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT name FROM question_banks WHERE tenant_code = %s AND id = 6",
                (TENANT,),
            )
            row = await cur.fetchone()
            if row is None:
                raise RuntimeError("题库 6 不存在")
            bank_name = row[0]

            await cur.execute(
                "SELECT id, name, employee_no, notify_deadline FROM employees "
                "WHERE tenant_code = %s AND status = 'active' ORDER BY id ASC LIMIT 2",
                (TENANT,),
            )
            rows = await cur.fetchall()
    if len(rows) < 2:
        raise RuntimeError("至少需要 2 名在职员工")
    employees = [
        {
            "id": int(item[0]),
            "name": item[1],
            "employee_no": item[2],
            "notify_deadline": bool(item[3]),
        }
        for item in rows
    ]
    return bank_name, employees


async def _cleanup(exam_id: int) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM notifications WHERE biz_id = %s AND biz_type IN "
                "('exam','exam_deadline','exam_closed')",
                (exam_id,),
            )
            await cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))


async def main() -> int:
    await init_mysql()
    bank_name, employees = await _fixtures()
    first, second = employees
    print(f"[INFO] 使用员工：{[item['name'] for item in employees]}")

    first_token = create_employee_token(
        first["id"], TENANT, first["name"], first["employee_no"]
    )
    first_headers = {"Authorization": f"Bearer {first_token}"}
    admin_token = create_admin_token("admin", "tenant_admin", TENANT, "测试管理员")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    exam_id: int | None = None
    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
            # 1. 微信订阅配置
            resp = await client.get(
                "/employee/wechat-subscribe/config", headers=first_headers
            )
            config = resp.json().get("data") or {}
            check("订阅配置接口可用", resp.json().get("code") == 0, str(config))
            if not config.get("templates"):
                check("未配置模板时为关闭", config.get("enabled") is False)

            # 2. 订阅上报
            resp = await client.post(
                "/employee/wechat-subscribe/subscriptions",
                headers=first_headers,
                json={"template_ids": ["not-configured-template"]},
            )
            recorded = (resp.json().get("data") or {}).get("recorded")
            check("未配置模板时上报被忽略", recorded == 0, f"recorded={recorded}")

            # 3. 通知偏好
            resp = await client.get(
                "/employee/notification-preferences", headers=first_headers
            )
            original_pref = (resp.json().get("data") or {}).get("notify_deadline")
            check("读取通知偏好", resp.json().get("code") == 0, str(original_pref))

            resp = await client.put(
                "/employee/notification-preferences",
                headers=first_headers,
                json={"notify_deadline": False},
            )
            check(
                "关闭截止提醒",
                (resp.json().get("data") or {}).get("notify_deadline") is False,
            )

            # 4. 创建考试并指派两人
            start_at = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            end_at = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

            resp = await client.post(
                "/admin/exams",
                headers=admin_headers,
                json={
                    "title": f"P2测试-{int(time.time())}",
                    "bank_name": bank_name,
                    "question_count": 3,
                    "pass_score": 60,
                    "duration_minutes": 30,
                    "max_attempts": 1,
                    "start_at": start_at,
                    "end_at": end_at,
                },
            )
            body = resp.json()
            if body.get("code") != 0:
                check("创建临时考试", False, str(body))
                return 1
            exam_id = body["data"]["id"]

            await client.put(
                f"/admin/exams/{exam_id}/assignments",
                headers=admin_headers,
                json={
                    "scope": "employees",
                    "org_ids": [],
                    "employee_ids": [first["id"], second["id"]],
                },
            )
            resp = await client.post(
                f"/admin/exams/{exam_id}/publish", headers=admin_headers
            )
            check("发布临时考试", resp.json().get("code") == 0)

            # 5. 截止提醒候选应排除关闭提醒的员工
            candidates = await notification_repository.list_deadline_candidates(24)
            exam_candidates = {
                int(row[4])
                for row in candidates
                if int(row[1]) == exam_id
            }
            check(
                "关闭提醒的员工不进入候选",
                first["id"] not in exam_candidates,
                f"候选={sorted(exam_candidates)}",
            )
            check(
                "其他员工仍在候选",
                second["id"] in exam_candidates,
                f"候选={sorted(exam_candidates)}",
            )

            # 恢复偏好
            resp = await client.put(
                "/employee/notification-preferences",
                headers=first_headers,
                json={"notify_deadline": bool(original_pref)},
            )
            check("恢复通知偏好", resp.json().get("code") == 0)

            # 6. 送达统计
            resp = await client.get(
                f"/admin/exams/{exam_id}/notification-stats", headers=admin_headers
            )
            stats = resp.json().get("data") or {}
            check(
                "统计：指派与通知人数",
                stats.get("assigned") == 2 and stats.get("notified") == 2,
                str(stats),
            )
            check(
                "统计：已读为 0",
                stats.get("read") == 0,
                f"read={stats.get('read')}",
            )
            check(
                "统计：未绑定微信名单",
                {item["id"] for item in stats.get("unbound", [])}
                == {first["id"], second["id"]},
                str([item["name"] for item in stats.get("unbound", [])]),
            )
            check(
                "统计：微信绑定人数",
                stats.get("bound_wechat") == 0,
                f"bound={stats.get('bound_wechat')}",
            )

            # 7. 员工已读后统计变化
            resp = await client.post(
                "/employee/notifications/read-exams",
                headers=first_headers,
                json={"exam_ids": [exam_id]},
            )
            check("员工标记已读", resp.json().get("code") == 0, str(resp.json().get("data")))

            resp = await client.get(
                f"/admin/exams/{exam_id}/notification-stats", headers=admin_headers
            )
            stats = resp.json().get("data") or {}
            check("统计：已读数更新", stats.get("read") == 1, f"read={stats.get('read')}")

    finally:
        if exam_id is not None:
            await _cleanup(exam_id)
            print(f"[INFO] 已清理临时考试 exam_id={exam_id}")
        await close_mysql_pool()

    failed = [item for item in checks if not item[1]]
    print()
    if failed:
        print(f"RESULT: {len(checks) - len(failed)}/{len(checks)} passed, {len(failed)} failed")
        return 1
    print(f"RESULT: {len(checks)}/{len(checks)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
