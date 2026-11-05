"""发布考试 -> 员工收到通知 的端到端测试

流程（全部走真实 HTTP 接口）：
    1. 创建临时考试（草稿）
    2. 指派 3 名员工
    3. 发布前预览通知人数
    4. 发布考试
    5. 校验 notifications 表写入
    6. 员工 token 调 summary，确认出现未读考试
    7. 标记已读，确认归零
    8. 清理临时考试与通知

运行：python scripts/test_publish_notification.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.auth import create_admin_token, create_employee_token  # noqa: E402
from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
TENANT = "demo"


async def _prepare() -> tuple[str, list[tuple[int, str, str]]]:
    pool = get_mysql_pool()
    assert pool is not None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT b.name FROM question_banks b "
                "WHERE b.tenant_code = %s AND b.id = 6",
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

    if len(employees) < 1:
        raise RuntimeError("没有在职员工")
    return bank_name, employees


async def _cleanup(exam_id: int) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM notifications WHERE biz_type = 'exam' AND biz_id = %s",
                (exam_id,),
            )
            await cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))


async def main() -> int:
    await init_mysql()

    bank_name, employees = await _prepare()
    print(f"[1] 使用题库「{bank_name}」，员工: {[e[1] for e in employees]}")

    admin_token = create_admin_token(
        login_name="admin",
        role="tenant_admin",
        tenant_code=TENANT,
        display_name="测试管理员",
    )
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    employee_ids = [e[0] for e in employees]

    exam_id: int | None = None
    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
            title = f"通知测试-{int(time.time())}"

            # 1. 创建草稿考试
            resp = await client.post(
                "/admin/exams",
                headers=admin_headers,
                json={
                    "title": title,
                    "bank_name": bank_name,
                    "question_count": 3,
                    "pass_score": 60,
                    "duration_minutes": 30,
                    "max_attempts": 1,
                },
            )
            body = resp.json()
            if resp.status_code != 200 or body.get("code") != 0:
                print(f"[FAIL] 创建考试失败: {resp.status_code} {body}")
                return 1
            exam = body["data"]
            exam_id = exam["id"]
            print(f"[2] 创建草稿考试 exam_id={exam_id} title={title}")

            # 2. 指派员工
            resp = await client.put(
                f"/admin/exams/{exam_id}/assignments",
                headers=admin_headers,
                json={"scope": "employees", "org_ids": [], "employee_ids": employee_ids},
            )
            body = resp.json()
            if resp.status_code != 200 or body.get("code") != 0:
                print(f"[FAIL] 指派失败: {resp.status_code} {body}")
                return 1
            print(f"[3] 指派结果: {body['data']}")

            # 3. 发布预览
            resp = await client.get(
                f"/admin/exams/{exam_id}/notify-preview", headers=admin_headers
            )
            preview = resp.json().get("data") or {}
            print(f"[4] 发布预览: 将通知 {preview.get('assigned')} 人，"
                  f"其中已绑定微信 {preview.get('bound_wechat')} 人")

            # 4. 发布
            resp = await client.post(
                f"/admin/exams/{exam_id}/publish", headers=admin_headers
            )
            body = resp.json()
            if resp.status_code != 200 or body.get("code") != 0:
                print(f"[FAIL] 发布失败: {resp.status_code} {body}")
                return 1
            print(f"[5] 发布成功，状态={body['data']['status']}，已指派 {body['data']['assigned']} 人")

            # 5. 数据库中的通知
            pool = get_mysql_pool()
            assert pool is not None
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT recipient_id, type, title, read_at FROM notifications "
                        "WHERE biz_type = 'exam' AND biz_id = %s ORDER BY recipient_id",
                        (exam_id,),
                    )
                    rows = await cur.fetchall()
            print(f"[6] 通知表写入 {len(rows)} 条:")
            for row in rows:
                print(f"    recipient={row[0]} type={row[1]} read={row[3] is not None} title={row[2]}")

            expected = len(employee_ids)
            if len(rows) != expected:
                print(f"[FAIL] 期望 {expected} 条通知，实际 {len(rows)} 条")
                return 1

            # 6. 模拟员工查看
            emp_id, emp_name, emp_no = employees[0]
            emp_token = create_employee_token(emp_id, TENANT, emp_name, emp_no)
            emp_headers = {"Authorization": f"Bearer {emp_token}"}

            resp = await client.get("/employee/notifications/summary", headers=emp_headers)
            data = resp.json().get("data") or {}
            print(f"[7] 员工 {emp_name} 未读: {data.get('unread_count')}，"
                  f"未读考试: {data.get('unread_exam_ids')}，"
                  f"待完成: {data.get('pending_exam_count')}")
            print(f"    最新消息: {[item['title'] for item in data.get('items', [])]}")
            if exam_id not in (data.get("unread_exam_ids") or []):
                print("[FAIL] 员工未读到新考试通知")
                return 1

            # 7. 标记已读
            resp = await client.post(
                "/employee/notifications/read-by-biz",
                headers=emp_headers,
                json={"biz_type": "exam", "biz_id": exam_id},
            )
            print(f"[8] 标记已读: {resp.json().get('data')}")

            resp = await client.get("/employee/notifications/summary", headers=emp_headers)
            data = resp.json().get("data") or {}
            print(f"[9] 已读后未读: {data.get('unread_count')}，"
                  f"未读考试: {data.get('unread_exam_ids')}")
            if exam_id in (data.get("unread_exam_ids") or []):
                print("[FAIL] 标记已读后仍未清除")
                return 1

            print("[PASS] 发布考试通知链路通过")
            return 0

    finally:
        if exam_id is not None:
            await _cleanup(exam_id)
            print(f"[10] 已清理临时考试 exam_id={exam_id}")
        await close_mysql_pool()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
