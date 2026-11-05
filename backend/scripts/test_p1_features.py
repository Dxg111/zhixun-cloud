"""P1 端到端自动测试

覆盖：
    1. 发布考试通知被指派员工
    2. 已发布考试追加指派，只通知新增员工
    3. 截止前提醒：扫描一次全部发送，再扫一次不重复
    4. 员工提交后收到成绩通知
    5. 关闭考试通知未完成员工
    6. 员工列表返回 computed_state（done / expired）
    7. 消息列表接口与已读

脚本使用临时考试，结束后删除并恢复租户通知设置。

运行：python scripts/test_p1_features.py
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
from app.services import deadline_reminder_service  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
TENANT = "demo"

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")


async def _load_fixtures():
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
                "SELECT id, name, employee_no FROM employees "
                "WHERE tenant_code = %s AND status = 'active' ORDER BY id ASC LIMIT 3",
                (TENANT,),
            )
            employees = [(int(r[0]), r[1], r[2]) for r in await cur.fetchall()]

            await cur.execute(
                "SELECT notify_deadline FROM tenant_settings WHERE tenant_code = %s",
                (TENANT,),
            )
            row = await cur.fetchone()
            original_deadline = bool(row[0]) if row else False

    if len(employees) < 3:
        raise RuntimeError("至少需要 3 名在职员工")
    return bank_name, employees, original_deadline


async def _set_notify_deadline(enabled: bool) -> None:
    pool = get_mysql_pool()
    assert pool is not None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE tenant_settings SET notify_deadline = %s WHERE tenant_code = %s",
                (1 if enabled else 0, TENANT),
            )


async def _cleanup(exam_id: int, attempt_ids: list[int]) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM notifications WHERE "
                "(biz_type IN ('exam','exam_deadline','exam_closed') AND biz_id = %s)",
                (exam_id,),
            )
            if attempt_ids:
                placeholders = ",".join(["%s"] * len(attempt_ids))
                await cur.execute(
                    f"DELETE FROM notifications WHERE biz_type = 'attempt' "
                    f"AND biz_id IN ({placeholders})",
                    tuple(attempt_ids),
                )
            await cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))


async def _notifications(employee_id: int, headers: dict, client: httpx.AsyncClient) -> list[dict]:
    resp = await client.get(
        "/employee/notifications?page_size=50", headers=headers
    )
    body = resp.json()
    items = (body.get("data") or {}).get("items") or []
    return items


async def main() -> int:
    await init_mysql()
    bank_name, employees, original_deadline = await _load_fixtures()
    ids = [item[0] for item in employees]
    print(f"[INFO] 题库：{bank_name}；员工：{[item[1] for item in employees]}")

    admin_token = create_admin_token("admin", "tenant_admin", TENANT, "测试管理员")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    emp_headers: dict[int, dict] = {}
    for employee_id, name, employee_no in employees:
        token = create_employee_token(employee_id, TENANT, name, employee_no)
        emp_headers[employee_id] = {"Authorization": f"Bearer {token}"}

    await _set_notify_deadline(True)
    exam_id: int | None = None
    attempt_ids: list[int] = []

    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
            start_at = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            end_at = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

            # 1. 创建并指派 2 人
            resp = await client.post(
                "/admin/exams",
                headers=admin_headers,
                json={
                    "title": f"P1测试-{int(time.time())}",
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
            check("创建临时考试", True, f"exam_id={exam_id}")

            resp = await client.put(
                f"/admin/exams/{exam_id}/assignments",
                headers=admin_headers,
                json={"scope": "employees", "org_ids": [], "employee_ids": ids[:2]},
            )
            check("草稿指派 2 人", resp.json().get("code") == 0, str(resp.json().get("data")))

            resp = await client.post(f"/admin/exams/{exam_id}/publish", headers=admin_headers)
            check("发布考试", resp.json().get("code") == 0)

            # 2. 发布通知
            pool = get_mysql_pool()
            assert pool is not None
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT COUNT(*) FROM notifications WHERE biz_type='exam' AND biz_id=%s",
                        (exam_id,),
                    )
                    count = int((await cur.fetchone())[0])
            check("发布通知被指派 2 人", count == 2, f"实际 {count} 条")

            # 3. 追加指派第 3 人
            resp = await client.put(
                f"/admin/exams/{exam_id}/assignments",
                headers=admin_headers,
                json={"scope": "employees", "org_ids": [], "employee_ids": [ids[2]]},
            )
            data = resp.json().get("data") or {}
            check(
                "追加指派保留原指派",
                data.get("assigned") == 3 and data.get("added") == 1,
                str(data),
            )
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT COUNT(*) FROM notifications WHERE biz_type='exam' AND biz_id=%s",
                        (exam_id,),
                    )
                    count = int((await cur.fetchone())[0])
            check("追加指派通知新增员工", count == 3, f"实际 {count} 条")

            # 4. 截止提醒：首次发送，二次幂等
            # 扫描是全租户行为，其他考试也会被顺带提醒；统计只针对临时考试，
            # 并在结束后清理本次测试产生的其他考试提醒。
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT COALESCE(MAX(id), 0) FROM notifications")
                    before_max_id = int((await cur.fetchone())[0])

            await deadline_reminder_service.scan_once()

            async def temp_deadline_count() -> int:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "SELECT COUNT(*) FROM notifications "
                            "WHERE biz_type='exam_deadline' AND biz_id=%s",
                            (exam_id,),
                        )
                        return int((await cur.fetchone())[0])

            count = await temp_deadline_count()
            check("截止提醒首次发送", count == 3, f"实际 {count} 条")

            await deadline_reminder_service.scan_once()
            count_again = await temp_deadline_count()
            check("截止提醒重复扫描不重复发送", count_again == 3, f"实际 {count_again} 条")

            # 清理本次扫描对其他真实考试产生的提醒
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "DELETE FROM notifications WHERE id > %s "
                        "AND NOT (biz_type = 'exam_deadline' AND biz_id = %s)",
                        (before_max_id, exam_id),
                    )

            # 5. 员工提交 -> 成绩通知
            first = employees[0][0]
            resp = await client.post(
                f"/employee/exams/{exam_id}/start", headers=emp_headers[first]
            )
            body = resp.json()
            if body.get("code") != 0:
                check("员工开始考试", False, str(body))
                return 1
            attempt_id = body["data"]["attempt_id"]
            attempt_ids.append(attempt_id)
            check("员工开始考试", True, f"attempt_id={attempt_id}")

            resp = await client.post(
                f"/employee/attempts/{attempt_id}/submit",
                headers=emp_headers[first],
                json={"answers": []},
            )
            check("员工提交答卷", resp.json().get("code") == 0)

            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT COUNT(*) FROM notifications "
                        "WHERE biz_type='attempt' AND biz_id=%s AND type='result_ready'",
                        (attempt_id,),
                    )
                    count = int((await cur.fetchone())[0])
            check("成绩通知写入", count == 1, f"实际 {count} 条")

            # 6. 关闭考试 -> 未完成员工收到通知
            resp = await client.post(
                f"/admin/exams/{exam_id}/close", headers=admin_headers
            )
            check("关闭考试", resp.json().get("code") == 0)

            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT COUNT(*) FROM notifications "
                        "WHERE biz_type='exam_closed' AND biz_id=%s",
                        (exam_id,),
                    )
                    count = int((await cur.fetchone())[0])
            check("关闭考试通知未完成员工", count == 2, f"实际 {count} 条")

            # 7. computed_state
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT id, status FROM exams WHERE id=%s", (exam_id,)
                    )
                    print(f"[INFO] 考试状态：{await cur.fetchone()}")

            resp = await client.get("/employee/exams", headers=emp_headers[first])
            items = (resp.json().get("data") or {}).get("items") or []
            target = next((item for item in items if item["id"] == exam_id), None)
            check(
                "已提交考试状态为 done",
                bool(target) and target.get("computed_state") == "done",
                str(target.get("computed_state") if target else None),
            )

            second = employees[1][0]
            resp = await client.get("/employee/exams", headers=emp_headers[second])
            items = (resp.json().get("data") or {}).get("items") or []
            target = next((item for item in items if item["id"] == exam_id), None)
            check(
                "关闭后未完成考试状态为 expired",
                bool(target) and target.get("computed_state") == "expired",
                str(target.get("computed_state") if target else None),
            )

            # 8. 消息列表包含成绩与关闭通知
            items = await _notifications(second, emp_headers[second], client)
            types = {item["type"] for item in items if item["biz_id"] == exam_id}
            check(
                "消息列表包含考试关闭通知",
                "exam_closed" in types,
                str(sorted(types)),
            )

            items = await _notifications(first, emp_headers[first], client)
            types = {item["type"] for item in items if item["biz_id"] in (exam_id, attempt_id)}
            check(
                "消息列表包含成绩通知",
                "result_ready" in types,
                str(sorted(types)),
            )

            # 9. 全部已读
            resp = await client.post(
                "/employee/notifications/read-all", headers=emp_headers[first]
            )
            check("全部标为已读", resp.json().get("code") == 0, str(resp.json().get("data")))
            summary = await client.get(
                "/employee/notifications/summary", headers=emp_headers[first]
            )
            unread = (summary.json().get("data") or {}).get("unread_count")
            check("已读后未读数归零", unread == 0, f"unread={unread}")

    finally:
        if exam_id is not None:
            await _cleanup(exam_id, attempt_ids)
            print(f"[INFO] 已清理临时考试 exam_id={exam_id}")
        if original_deadline:
            await _set_notify_deadline(True)
        else:
            await _set_notify_deadline(False)
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
