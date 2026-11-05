"""P0 缺口补齐端到端测试

覆盖：
    1. 部门创建 / 改名 / 删除
    2. 带描述的考试创建与发布
    3. 员工提交后成绩分析（平均分、题目正确率、薄弱点、部门对比）
    4. 成绩明细列表
    5. 审计日志可查询
    6. 导出任务带 24 小时有效期

运行：python scripts/test_p0_gaps_e2e.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.auth import create_admin_token, create_employee_token  # noqa: E402
from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402

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
                "SELECT id, name, employee_no FROM employees "
                "WHERE tenant_code = %s AND status = 'active' ORDER BY id ASC LIMIT 2",
                (TENANT,),
            )
            employees = [(int(r[0]), r[1], r[2]) for r in await cur.fetchall()]
    if len(employees) < 2:
        raise RuntimeError("至少需要 2 名在职员工")
    return bank_name, employees


async def _snapshot_answers(exam_id: int) -> list[dict]:
    pool = get_mysql_pool()
    assert pool is not None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT snapshot_json FROM exam_questions WHERE exam_id = %s ORDER BY sort",
                (exam_id,),
            )
            rows = await cur.fetchall()
    result = []
    for row in rows:
        snapshot = row[0]
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        result.append(
            {
                "question_id": snapshot["id"],
                "answer": snapshot.get("answer") or [],
            }
        )
    return result


async def _cleanup(exam_id: int | None, org_id: int | None, export_id: int | None) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            if export_id is not None:
                await cur.execute(
                    "SELECT file_path FROM export_tasks WHERE id = %s", (export_id,)
                )
                row = await cur.fetchone()
                if row and row[0] and os.path.exists(row[0]):
                    try:
                        os.remove(row[0])
                    except OSError:
                        pass
                await cur.execute("DELETE FROM export_tasks WHERE id = %s", (export_id,))
            if exam_id is not None:
                await cur.execute(
                    "DELETE FROM notifications WHERE biz_type IN "
                    "('exam','exam_deadline','exam_closed') AND biz_id = %s",
                    (exam_id,),
                )
                await cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))
            if org_id is not None:
                await cur.execute("DELETE FROM org_units WHERE id = %s", (org_id,))


async def main() -> int:
    await init_mysql()
    bank_name, employees = await _fixtures()

    admin_token = create_admin_token("admin", "tenant_admin", TENANT, "测试管理员")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    emp_headers: dict[int, dict] = {}
    for employee_id, name, employee_no in employees:
        token = create_employee_token(employee_id, TENANT, name, employee_no)
        emp_headers[employee_id] = {"Authorization": f"Bearer {token}"}

    exam_id: int | None = None
    org_id: int | None = None
    export_id: int | None = None

    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=60) as client:
            # 1. 部门创建/改名/删除
            org_name = f"测试部门{int(time.time())}"
            resp = await client.post(
                "/admin/org-units", headers=admin_headers, json={"name": org_name}
            )
            body = resp.json()
            if body.get("code") != 0:
                check("创建临时部门", False, str(body))
                return 1
            org_id = body["data"]["id"]
            check("创建临时部门", True, f"id={org_id}")

            resp = await client.put(
                f"/admin/org-units/{org_id}",
                headers=admin_headers,
                json={"name": f"{org_name}改", "parent_id": None},
            )
            renamed = (resp.json().get("data") or {}).get("name")
            check("部门改名", renamed == f"{org_name}改", str(renamed))

            # 2. 创建带描述的考试
            start_at = (datetime.now() - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            end_at = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
            resp = await client.post(
                "/admin/exams",
                headers=admin_headers,
                json={
                    "title": f"P0补齐测试-{int(time.time())}",
                    "description": "本次考试用于验证成绩分析与审计日志",
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
                check("创建带描述考试", False, str(body))
                return 1
            exam_id = body["data"]["id"]
            check(
                "创建带描述考试",
                body["data"].get("description") == "本次考试用于验证成绩分析与审计日志",
                str(body["data"].get("description")),
            )

            resp = await client.put(
                f"/admin/exams/{exam_id}/assignments",
                headers=admin_headers,
                json={
                    "scope": "employees",
                    "org_ids": [],
                    "employee_ids": [employee[0] for employee in employees],
                },
            )
            resp = await client.post(
                f"/admin/exams/{exam_id}/publish", headers=admin_headers
            )
            check("发布考试", resp.json().get("code") == 0)

            # 3. 两名员工提交：一人全对，一人错一题
            answers = await _snapshot_answers(exam_id)
            plan = [
                (employees[0][0], [item["answer"] for item in answers]),
                (
                    employees[1][0],
                    [
                        answers[0]["answer"],
                        ["Z"] if answers[1]["answer"] else [],
                        answers[2]["answer"],
                    ],
                ),
            ]
            for employee_id, selections in plan:
                resp = await client.post(
                    f"/employee/exams/{exam_id}/start",
                    headers=emp_headers[employee_id],
                )
                paper = resp.json().get("data") or {}
                if resp.json().get("code") != 0:
                    check("员工开始考试", False, str(resp.json()))
                    return 1
                payload = {
                    "answers": [
                        {"question_id": answers[index]["question_id"], "selected": selected}
                        for index, selected in enumerate(selections)
                    ]
                }
                resp = await client.post(
                    f"/employee/attempts/{paper['attempt_id']}/submit",
                    headers=emp_headers[employee_id],
                    json=payload,
                )
                check("员工提交答卷", resp.json().get("code") == 0)

            # 4. 成绩分析
            resp = await client.get(
                f"/admin/exams/{exam_id}/analytics", headers=admin_headers
            )
            analytics = resp.json().get("data") or {}
            check(
                "分析：平均分",
                75 <= float(analytics.get("avg_score") or 0) <= 90,
                f"avg={analytics.get('avg_score')}",
            )
            check(
                "分析：题目正确率",
                len(analytics.get("question_accuracy") or []) == 3,
                str(len(analytics.get("question_accuracy") or [])),
            )
            check(
                "分析：薄弱知识点",
                len(analytics.get("weak_points") or []) >= 1,
                str(len(analytics.get("weak_points") or [])),
            )
            check(
                "分析：部门对比",
                len(analytics.get("departments") or []) >= 1,
                str([d["org_path"] for d in analytics.get("departments") or []]),
            )

            # 5. 成绩明细
            resp = await client.get(
                f"/admin/exams/{exam_id}/attempts?page=1&page_size=10",
                headers=admin_headers,
            )
            detail = resp.json().get("data") or {}
            check(
                "成绩明细返回两人",
                detail.get("total") == 2,
                f"total={detail.get('total')}",
            )
            scores = sorted(
                item["best_score"] for item in detail.get("items") or []
                if item["best_score"] is not None
            )
            check(
                "成绩明细分数",
                len(scores) == 2 and scores[-1] == 100.0 and scores[0] < 70,
                str(scores),
            )

            # 6. 审计日志
            resp = await client.get(
                "/admin/audit-logs?page=1&page_size=50", headers=admin_headers
            )
            actions = {item["action"] for item in (resp.json().get("data") or {}).get("items", [])}
            check(
                "审计日志包含部门与考试操作",
                {"org.create", "org.update", "exam.create", "exam.publish"}.issubset(actions),
                str(sorted(actions)),
            )

            # 7. 导出有效期
            resp = await client.post(
                f"/admin/exams/{exam_id}/export", headers=admin_headers
            )
            task = resp.json().get("data") or {}
            export_id = task.get("id")
            check(
                "导出任务带有效期",
                bool(task.get("expires_at")),
                str(task.get("expires_at")),
            )

            # 8. 部门删除（无员工）
            resp = await client.delete(
                f"/admin/org-units/{org_id}", headers=admin_headers
            )
            check("删除临时部门", resp.json().get("code") == 0)
            org_id = None

    finally:
        await _cleanup(exam_id, org_id, export_id)
        print("[INFO] 临时数据已清理")
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
