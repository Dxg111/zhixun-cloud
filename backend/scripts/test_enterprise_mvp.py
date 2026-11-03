"""企业 MVP 真实闭环测试。

覆盖：
    管理员登录 -> 上传文档 -> AI 生成题目 -> 审核通过
    -> AI 生成知识卡 -> 发布知识卡
    -> 创建考试 -> 按部门指派 -> 关联知识卡 -> 发布
    -> 员工登录 -> 查看知识卡并记录阅读
    -> 开始考试 -> 保存答案 -> 超时自动判分
    -> 提交幂等 -> 错题收集 -> 连续答对 2 次掌握 -> 取消掌握
    -> 管理员查看知识卡查看率 -> 导出 Excel

运行：
    cd backend
    python scripts/test_enterprise_mvp.py

说明：
    - 使用真实 MySQL 和真实 DeepSeek 调用；
    - 脚本结束会清理本次创建的文档、题库、题目、知识卡、考试和导出文件。
"""

import asyncio
import io
import json
import os
import sys
import time
from pathlib import Path

import httpx
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402
from app.main import app  # noqa: E402

DOC_CONTENT = (
    "食品安全培训资料：冷藏食品应保持在0-4摄氏度。"
    "营业期间每4小时记录一次冷藏柜温度。"
    "发现过期原料必须立即隔离并按规定处理，不能继续使用。"
    "顾客投诉时先道歉并倾听，再记录、解决和回访。"
    "收银差异超过10元需要立即上报店长并填写差异记录。"
) * 8


async def main() -> None:
    await init_mysql()
    suffix = str(int(time.time()))
    bank_name = f"MVP测试题库_{suffix}"
    doc_name = f"MVP测试文档_{suffix}.txt"
    exam_title = f"MVP测试考试_{suffix}"
    exam_id = None
    doc_id = None
    attempt_id = None
    card_ids: list[int] = []

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", timeout=300
    ) as client:
        try:
            login = await client.post(
                "/api/v1/auth/admin/login",
                json={"tenant_code": "demo", "login_name": "admin", "password": "demo1234"},
            )
            login.raise_for_status()
            admin_headers = {"Authorization": f"Bearer {login.json()['data']['token']}"}
            print("[1/12] 管理员登录成功")

            upload = await client.post(
                "/api/v1/admin/documents",
                files={"file": (doc_name, DOC_CONTENT.encode("utf-8"), "text/plain")},
                headers=admin_headers,
            )
            upload.raise_for_status()
            doc_id = upload.json()["data"]["id"]
            assert upload.json()["data"]["status"] == "ready"
            print(f"[2/12] 文档上传并解析成功，片段数={upload.json()['data']['chunks']}")

            generated = await client.post(
                f"/api/v1/admin/documents/{doc_id}/generate-questions",
                json={"bank_name": bank_name, "question_count": 3, "difficulty": "medium"},
                headers=admin_headers,
            )
            generated.raise_for_status()
            created = generated.json()["data"]["created"]
            assert created >= 2
            print(f"[3/12] AI 生成题目成功，草稿数={created}")

            questions = await client.get(
                "/api/v1/admin/questions?status=draft&page_size=100",
                headers=admin_headers,
            )
            bank_questions = [
                item for item in questions.json()["data"]["items"] if item["bank_name"] == bank_name
            ]
            assert len(bank_questions) >= 2
            for question in bank_questions[:2]:
                reviewed = await client.post(
                    f"/api/v1/admin/questions/{question['id']}/review",
                    json={"action": "approve", "note": "MVP 自动测试通过"},
                    headers=admin_headers,
                )
                reviewed.raise_for_status()
            print("[4/12] 题目审核通过")

            cards_resp = await client.post(
                "/api/v1/admin/knowledge-cards/generate",
                json={
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "count": 3,
                    "style": "操作要点",
                },
                headers=admin_headers,
            )
            cards_resp.raise_for_status()
            cards = cards_resp.json()["data"]["items"]
            assert cards, "AI 未生成知识卡"
            card_ids = [card["id"] for card in cards]

            card_detail = await client.get(
                f"/api/v1/admin/knowledge-cards/{card_ids[0]}",
                headers=admin_headers,
            )
            card_detail.raise_for_status()
            detail_data = card_detail.json()["data"]
            assert detail_data["points"], "知识卡没有要点内容"
            edited = await client.put(
                f"/api/v1/admin/knowledge-cards/{card_ids[0]}",
                json={
                    "title": detail_data["title"],
                    "excerpt": detail_data["excerpt"],
                    "points": detail_data["points"],
                },
                headers=admin_headers,
            )
            edited.raise_for_status()
            assert len(edited.json()["data"]["points"]) == len(detail_data["points"])

            for card_id in card_ids:
                published = await client.put(
                    f"/api/v1/admin/knowledge-cards/{card_id}/status",
                    json={"status": "published"},
                    headers=admin_headers,
                )
                published.raise_for_status()
            print(f"[5/12] AI 生成并发布知识卡 {len(card_ids)} 张")

            orgs = await client.get("/api/v1/admin/org-units", headers=admin_headers)
            orgs.raise_for_status()
            target_org = next(
                org
                for org in orgs.json()["data"]["items"]
                if org["path"] == "华东区/上海门店/徐汇店"
            )

            exam = await client.post(
                "/api/v1/admin/exams",
                json={
                    "title": exam_title,
                    "bank_name": bank_name,
                    "question_count": 2,
                    "pass_score": 60,
                    "duration_minutes": 30,
                    "max_attempts": 1,
                },
                headers=admin_headers,
            )
            exam.raise_for_status()
            exam_id = exam.json()["data"]["id"]

            assigned = await client.put(
                f"/api/v1/admin/exams/{exam_id}/assignments",
                json={"scope": "org", "org_ids": [target_org["id"]], "employee_ids": []},
                headers=admin_headers,
            )
            assigned.raise_for_status()
            assert assigned.json()["data"]["assigned"] >= 1

            linked = await client.put(
                f"/api/v1/admin/exams/{exam_id}/knowledge-cards",
                json={"card_ids": card_ids},
                headers=admin_headers,
            )
            linked.raise_for_status()
            assert len(linked.json()["data"]) == len(card_ids)
            linked_list = await client.get(
                f"/api/v1/admin/exams/{exam_id}/knowledge-cards",
                headers=admin_headers,
            )
            linked_list.raise_for_status()
            assert len(linked_list.json()["data"]) == len(card_ids)

            publish = await client.post(
                f"/api/v1/admin/exams/{exam_id}/publish",
                headers=admin_headers,
            )
            publish.raise_for_status()
            assert publish.json()["data"]["status"] == "published"
            print(
                f"[6/12] 考试发布成功，指派人数={publish.json()['data']['assigned']}，"
                f"关联知识卡={len(card_ids)}"
            )

            employee_login = await client.post(
                "/api/v1/employee/login",
                json={"tenant_code": "demo", "invite_code": "INV1001"},
            )
            employee_login.raise_for_status()
            employee_headers = {
                "Authorization": f"Bearer {employee_login.json()['data']['token']}"
            }
            print(f"[7/12] 员工邀请码登录成功：{employee_login.json()['data']['employee']['name']}")

            exam_cards = await client.get(
                f"/api/v1/employee/exams/{exam_id}/cards",
                headers=employee_headers,
            )
            exam_cards.raise_for_status()
            employee_cards = exam_cards.json()["data"]["items"]
            assert len(employee_cards) == len(card_ids)
            assert all(not card["viewed"] for card in employee_cards)

            view = await client.post(
                f"/api/v1/employee/cards/{employee_cards[0]['id']}/view",
                headers=employee_headers,
            )
            view.raise_for_status()
            exam_cards = await client.get(
                f"/api/v1/employee/exams/{exam_id}/cards",
                headers=employee_headers,
            )
            assert exam_cards.json()["data"]["items"][0]["viewed"] is True
            print("[8/12] 员工查看知识卡并记录阅读")

            paper = await client.post(
                f"/api/v1/employee/exams/{exam_id}/start",
                headers=employee_headers,
            )
            paper.raise_for_status()
            paper_data = paper.json()["data"]
            attempt_id = paper_data["attempt_id"]
            assert paper_data["questions"]
            assert all("answer" not in question for question in paper_data["questions"])

            pool = get_mysql_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "SELECT snapshot_json FROM exam_questions WHERE exam_id = %s ORDER BY sort",
                        (exam_id,),
                    )
                    snapshots = [
                        json.loads(row[0]) if isinstance(row[0], str) else row[0]
                        for row in await cur.fetchall()
                    ]

            def wrong_choice(snapshot: dict) -> list[str]:
                correct = set(snapshot["answer"])
                for option in snapshot["options"]:
                    if option["key"] not in correct:
                        return [option["key"]]
                return [snapshot["options"][0]["key"]]

            answers = [
                {
                    "question_id": int(snapshot["id"]),
                    "selected": wrong_choice(snapshot) if index == 0 else snapshot["answer"],
                    "duration_ms": 5000,
                }
                for index, snapshot in enumerate(snapshots)
            ]

            save = await client.put(
                f"/api/v1/employee/attempts/{attempt_id}/answers",
                json={"answers": answers},
                headers=employee_headers,
            )
            save.raise_for_status()

            # 把进行中场次改成已过期，验证懒过期按已保存答案判分
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "UPDATE exam_attempts SET expires_at = NOW() - INTERVAL 1 MINUTE "
                        "WHERE id = %s",
                        (attempt_id,),
                    )

            expired_save = await client.put(
                f"/api/v1/employee/attempts/{attempt_id}/answers",
                json={"answers": answers},
                headers=employee_headers,
            )
            assert expired_save.json()["code"] == 4006
            print("[9/12] 超时保存被拒绝，系统已按已保存答案自动判分")

            submit = await client.post(
                f"/api/v1/employee/attempts/{attempt_id}/submit",
                json={"answers": answers},
                headers=employee_headers,
            )
            submit.raise_for_status()
            result = submit.json()["data"]
            assert result["score"] < 100, result
            assert result["passed"] is False
            print(
                f"[10/12] 提交幂等，服务端判分 score={result['score']} "
                f"correct={result['correct_count']}/{result['total_count']}"
            )

            wrong_list = await client.get(
                "/api/v1/employee/wrong-questions?mastered=false",
                headers=employee_headers,
            )
            wrong_list.raise_for_status()
            wrong_items = wrong_list.json()["data"]["items"]
            assert wrong_items, "错题未入库"
            wrong = wrong_items[0]
            correct_answer = next(
                snapshot["answer"]
                for snapshot in snapshots
                if int(snapshot["id"]) == wrong["question_id"]
            )

            first_retry = await client.post(
                f"/api/v1/employee/wrong-questions/{wrong['id']}/retry",
                json={"selected": correct_answer},
                headers=employee_headers,
            )
            first_retry.raise_for_status()
            assert first_retry.json()["data"]["correct_streak"] == 1
            assert first_retry.json()["data"]["mastered"] is False

            second_retry = await client.post(
                f"/api/v1/employee/wrong-questions/{wrong['id']}/retry",
                json={"selected": correct_answer},
                headers=employee_headers,
            )
            second_retry.raise_for_status()
            assert second_retry.json()["data"]["mastered"] is True

            unmaster = await client.post(
                f"/api/v1/employee/wrong-questions/{wrong['id']}/master",
                json={"mastered": False},
                headers=employee_headers,
            )
            unmaster.raise_for_status()
            assert unmaster.json()["data"]["mastered"] is False

            result_again = await client.get(
                f"/api/v1/employee/attempts/{attempt_id}/result",
                headers=employee_headers,
            )
            assert result_again.json()["data"]["score"] == result["score"]
            print("[11/12] 错题收集、连续答对掌握、取消掌握均正确，原成绩未变化")

            detail = await client.get(
                f"/api/v1/admin/exams/{exam_id}",
                headers=admin_headers,
            )
            detail.raise_for_status()
            stats = detail.json()["data"]
            assert stats["completed"] >= 1
            assert stats["card_view_rate"] > 0
            assert len(stats["card_titles"]) == len(card_ids)

            export = await client.post(
                f"/api/v1/admin/exams/{exam_id}/export",
                headers=admin_headers,
            )
            export.raise_for_status()
            task = export.json()["data"]
            assert task["file_name"].endswith(".xlsx")

            download = await client.get(
                f"/api/v1/admin/exports/{task['id']}/download",
                headers=admin_headers,
            )
            download.raise_for_status()
            assert download.content.startswith(b"PK")
            workbook = load_workbook(io.BytesIO(download.content))
            sheet = workbook.active
            headers = [cell.value for cell in next(sheet.iter_rows(max_row=1))]
            assert headers[:6] == ["工号", "姓名", "部门", "分数", "是否通过", "提交时间"]
            print(
                f"[12/12] 看板与 Excel 导出成功：card_view_rate={stats['card_view_rate']}% "
                f"rows={task['rows']}"
            )
            print("\nENTERPRISE MVP E2E: PASS")
        finally:
            pool = get_mysql_pool()
            if pool is not None:
                async with pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        if attempt_id is not None:
                            await cur.execute(
                                "DELETE FROM wrong_questions WHERE tenant_code = %s AND source_id = %s",
                                ("demo", str(attempt_id)),
                            )
                        if card_ids:
                            placeholders = ", ".join(["%s"] * len(card_ids))
                            await cur.execute(
                                f"DELETE FROM knowledge_card_views WHERE tenant_code = %s "
                                f"AND card_id IN ({placeholders})",
                                tuple(["demo", *card_ids]),
                            )
                        if exam_id is not None:
                            await cur.execute(
                                "SELECT file_path FROM export_tasks WHERE exam_id = %s",
                                (exam_id,),
                            )
                            for row in await cur.fetchall():
                                if row[0] and os.path.exists(row[0]):
                                    os.remove(row[0])
                            await cur.execute(
                                "DELETE FROM export_tasks WHERE exam_id = %s", (exam_id,)
                            )
                            await cur.execute("DELETE FROM exams WHERE id = %s", (exam_id,))
                        if doc_id is not None:
                            await cur.execute(
                                "DELETE FROM knowledge_cards WHERE tenant_code = %s AND doc_id = %s",
                                ("demo", doc_id),
                            )
                        await cur.execute(
                            "DELETE q FROM questions q JOIN question_banks b ON q.bank_id = b.id "
                            "WHERE q.tenant_code = %s AND b.name = %s",
                            ("demo", bank_name),
                        )
                        await cur.execute(
                            "DELETE FROM question_banks WHERE tenant_code = %s AND name = %s",
                            ("demo", bank_name),
                        )
                        if doc_id is not None:
                            await cur.execute(
                                "SELECT file_path FROM admin_documents WHERE id = %s", (doc_id,)
                            )
                            row = await cur.fetchone()
                            if row and row[0] and os.path.exists(row[0]):
                                os.remove(row[0])
                            await cur.execute(
                                "DELETE FROM admin_documents WHERE id = %s", (doc_id,)
                            )
            await close_mysql_pool()


if __name__ == "__main__":
    asyncio.run(main())
