"""初始化管理后台演示数据：组织、员工、文档、考试、成绩、导出、设置。

用法：
    cd backend
    python scripts/seed_admin_console.py
    python scripts/seed_admin_console.py --force
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402

TENANT = "demo"

ORGS = [
    ("华东区", None, "华东区"),
    ("上海门店", "华东区", "华东区/上海门店"),
    ("徐汇店", "华东区/上海门店", "华东区/上海门店/徐汇店"),
    ("静安店", "华东区/上海门店", "华东区/上海门店/静安店"),
    ("杭州门店", "华东区", "华东区/杭州门店"),
    ("华南区", None, "华南区"),
    ("深圳门店", "华南区", "华南区/深圳门店"),
    ("广州门店", "华南区", "华南区/广州门店"),
]

EMPLOYEES = [
    ("E1001", "张敏", "华东区/上海门店/徐汇店", "店长", "active", "INV1001", "bound"),
    ("E1002", "王磊", "华东区/上海门店/徐汇店", "员工", "active", "INV1002", "bound"),
    ("E1003", "李婷", "华东区/上海门店/静安店", "员工", "active", "INV1003", "unbound"),
    ("E1004", "陈浩", "华东区/杭州门店", "区域经理", "active", "INV1004", "bound"),
    ("E1005", "赵雪", "华南区/深圳门店", "店长", "active", "INV1005", "bound"),
    ("E1006", "周杰", "华南区/深圳门店", "员工", "disabled", "INV1006", "bound"),
    ("E1007", "孙悦", "华南区/广州门店", "员工", "active", "INV1007", "unbound"),
    ("E1008", "吴凡", "华东区/上海门店/静安店", "员工", "active", "INV1008", "bound"),
]

DOCS = [
    ("门店SOP手册-v3.pdf", "pdf", 8808038, "ready", 86, "2026-11-01 14:20:00"),
    ("食品安全操作规范.docx", "docx", 2202009, "ready", 42, "2026-10-30 10:12:00"),
    ("新人入职手册.md", "md", 327680, "ready", 18, "2026-10-28 16:40:00"),
    ("消防应急预案.pdf", "pdf", 5872025, "failed", 0, "2026-10-27 09:05:00"),
    ("客诉处理指引.pdf", "pdf", 1887436, "processing", 0, "2026-11-02 09:30:00"),
]

EXAMS = [
    ("门店食品安全考核", "食品安全题库", 20, 60, 30, 1, "2026-11-05 18:00:00", "published"),
    ("新人上岗考核", "新人培训题库", 15, 60, 20, 1, "2026-10-28 18:00:00", "closed"),
    ("秋季消防演练", "消防安全题库", 12, 60, 25, 1, None, "draft"),
    ("收银 SOP 复训", "门店SOP题库", 10, 60, 20, 2, "2026-11-08 20:00:00", "published"),
]

ATTEMPT_SCORES = {
    "门店食品安全考核": [55, 62, 68, 72, 80, 90],
    "新人上岗考核": [65, 70, 75, 80, 85, 90, 95],
    "收银 SOP 复训": [58, 70, 76, 82, 88],
}

EXPORTS = [
    ("门店食品安全考核-成绩-20261102.xlsx", "成绩明细", "ready", 86),
    ("新人上岗考核-成绩-20261028.xlsx", "成绩明细", "ready", 48),
    ("收银SOP复训-题目明细.xlsx", "题目明细", "processing", 0),
]


async def seed(force: bool) -> None:
    await init_mysql()
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("MySQL 未初始化")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT COUNT(*) FROM employees WHERE tenant_code = %s", (TENANT,))
            existing = int((await cur.fetchone())[0])
            if existing and not force:
                print(f"管理后台演示数据已有 {existing} 名员工，跳过。需要重刷请加 --force")
                return

            if force:
                for table in [
                    "exam_attempts", "exam_assignments", "exam_questions", "export_tasks",
                    "exams", "employees", "org_units", "admin_documents", "tenant_settings",
                ]:
                    await cur.execute(f"DELETE FROM {table} WHERE tenant_code = %s", (TENANT,)) if table not in (
                        "exam_questions", "exam_assignments", "exam_attempts"
                    ) else None
                await cur.execute(
                    "DELETE a FROM exam_questions a JOIN exams e ON a.exam_id = e.id WHERE e.tenant_code = %s",
                    (TENANT,),
                )
                await cur.execute(
                    "DELETE a FROM exam_assignments a JOIN exams e ON a.exam_id = e.id WHERE e.tenant_code = %s",
                    (TENANT,),
                )
                await cur.execute(
                    "DELETE a FROM exam_attempts a JOIN exams e ON a.exam_id = e.id WHERE e.tenant_code = %s",
                    (TENANT,),
                )
                for table in [
                    "export_tasks", "exams", "employees", "org_units",
                    "admin_documents", "tenant_settings",
                ]:
                    await cur.execute(f"DELETE FROM {table} WHERE tenant_code = %s", (TENANT,))
                print("已清空管理后台演示数据")

            org_ids: dict[str, int] = {}
            for name, parent_path, path in ORGS:
                parent_id = org_ids.get(parent_path) if parent_path else None
                await cur.execute(
                    "INSERT INTO org_units (tenant_code, parent_id, name, path, sort, status) "
                    "VALUES (%s, %s, %s, %s, 0, 'active') "
                    "ON DUPLICATE KEY UPDATE name = VALUES(name)",
                    (TENANT, parent_id, name, path),
                )
                await cur.execute(
                    "SELECT id FROM org_units WHERE tenant_code = %s AND path = %s",
                    (TENANT, path),
                )
                org_ids[path] = int((await cur.fetchone())[0])

            employee_ids: dict[str, int] = {}
            for no, name, path, role, status, invite, invite_status in EMPLOYEES:
                await cur.execute(
                    "INSERT INTO employees "
                    "(tenant_code, org_id, employee_no, name, role, status, invite_code, invite_status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE name = VALUES(name), org_id = VALUES(org_id), status = VALUES(status)",
                    (TENANT, org_ids[path], no, name, role, status, invite, invite_status),
                )
                await cur.execute(
                    "SELECT id FROM employees WHERE tenant_code = %s AND employee_no = %s",
                    (TENANT, no),
                )
                employee_ids[no] = int((await cur.fetchone())[0])

            for file_name, file_type, size, status, chunks, created_at in DOCS:
                await cur.execute(
                    "INSERT INTO admin_documents "
                    "(tenant_code, file_name, file_type, file_size, status, chunks, error_message, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        TENANT, file_name, file_type, size, status, chunks,
                        "加密 PDF，无法提取文本" if status == "failed" else None,
                        created_at,
                    ),
                )

            banks: dict[str, int] = {}
            for bank_name in {exam[1] for exam in EXAMS}:
                await cur.execute(
                    "SELECT id FROM question_banks WHERE tenant_code = %s AND name = %s",
                    (TENANT, bank_name),
                )
                row = await cur.fetchone()
                if row is None:
                    raise RuntimeError(f"题库不存在：{bank_name}，请先运行 seed_question_bank.py")
                banks[bank_name] = int(row[0])

            active_employee_ids = [
                employee_ids[no]
                for no, _, _, _, status, _, _ in EMPLOYEES
                if status == "active"
            ]

            exam_ids: dict[str, int] = {}
            for title, bank_name, question_count, pass_score, duration, attempts, end_at, status in EXAMS:
                await cur.execute(
                    "INSERT INTO exams "
                    "(tenant_code, title, bank_id, question_count, pass_score, duration_minutes, "
                    "max_attempts, end_at, status, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'admin')",
                    (
                        TENANT, title, banks[bank_name], question_count, pass_score,
                        duration, attempts, end_at, status,
                    ),
                )
                exam_id = int(cur.lastrowid)
                exam_ids[title] = exam_id

                if status in ("published", "closed"):
                    for employee_id in active_employee_ids:
                        await cur.execute(
                            "INSERT INTO exam_assignments (exam_id, employee_id) VALUES (%s, %s)",
                            (exam_id, employee_id),
                        )

                    scores = ATTEMPT_SCORES.get(title, [])
                    for index, score in enumerate(scores):
                        employee_id = active_employee_ids[index % len(active_employee_ids)]
                        submitted_at = datetime.now() - timedelta(days=index + 1)
                        await cur.execute(
                            "INSERT INTO exam_attempts "
                            "(exam_id, employee_id, attempt_no, status, score, passed, "
                            "started_at, submitted_at, duration_seconds) "
                            "VALUES (%s, %s, 1, 'submitted', %s, %s, %s, %s, %s)",
                            (
                                exam_id,
                                employee_id,
                                score,
                                1 if score >= pass_score else 0,
                                submitted_at - timedelta(minutes=duration),
                                submitted_at,
                                duration * 60 - 120,
                            ),
                        )

            # 一场带题目快照、可直接答题的演示考试
            await cur.execute(
                "SELECT id FROM exams WHERE tenant_code = %s AND title = %s",
                (TENANT, "门店 SOP 月度复训（演示）"),
            )
            if await cur.fetchone() is None:
                demo_bank_id = banks["门店SOP题库"]
                await cur.execute(
                    "SELECT id, type, stem, options_json, answer_json, explanation, "
                    "knowledge_point, difficulty, source_ref FROM questions "
                    "WHERE tenant_code = %s AND bank_id = %s AND status = 'approved' "
                    "ORDER BY id ASC LIMIT 3",
                    (TENANT, demo_bank_id),
                )
                demo_questions = await cur.fetchall()
                if demo_questions:
                    await cur.execute(
                        "INSERT INTO exams (tenant_code, title, bank_id, question_count, pass_score, "
                        "duration_minutes, max_attempts, end_at, status, created_by) "
                        "VALUES (%s, %s, %s, %s, 60, 20, 1, '2026-12-31 18:00:00', 'published', 'admin')",
                        (TENANT, "门店 SOP 月度复训（演示）", demo_bank_id, len(demo_questions)),
                    )
                    demo_exam_id = int(cur.lastrowid)
                    demo_score = round(100 / len(demo_questions), 2)
                    for index, row in enumerate(demo_questions, start=1):
                        snapshot = {
                            "id": row[0], "type": row[1], "stem": row[2],
                            "options": json.loads(row[3]) if isinstance(row[3], str) else row[3],
                            "answer": json.loads(row[4]) if isinstance(row[4], str) else row[4],
                            "explanation": row[5], "knowledge_point": row[6],
                            "difficulty": row[7], "source": row[8],
                        }
                        await cur.execute(
                            "INSERT INTO exam_questions (exam_id, question_id, snapshot_json, sort, score) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (demo_exam_id, row[0], json.dumps(snapshot, ensure_ascii=False), index, demo_score),
                        )
                    for employee_id in active_employee_ids:
                        await cur.execute(
                            "INSERT INTO exam_assignments (exam_id, employee_id) VALUES (%s, %s)",
                            (demo_exam_id, employee_id),
                        )

            for file_name, export_type, status, rows in EXPORTS:
                await cur.execute(
                    "INSERT INTO export_tasks "
                    "(tenant_code, exam_id, file_name, export_type, status, row_count, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, 'admin')",
                    (TENANT, exam_ids.get("门店食品安全考核"), file_name, export_type, status, rows),
                )

            await cur.execute(
                "INSERT INTO tenant_settings "
                "(tenant_code, tenant_name, admin_email, retention, default_pass_score, "
                "default_duration, default_attempts, random_order, notify_assigned, notify_result, "
                "notify_deadline, notify_cards) "
                "VALUES (%s, '演示企业', 'training@demo.com', '合同期 + 90 天', 60, 30, 1, '随机', 1, 1, 0, 0) "
                "ON DUPLICATE KEY UPDATE tenant_name = VALUES(tenant_name)",
                (TENANT,),
            )

            print(
                f"已写入 {len(ORGS)} 个部门、{len(EMPLOYEES)} 名员工、"
                f"{len(DOCS)} 篇文档、{len(EXAMS)} 场考试、{len(EXPORTS)} 个导出任务"
            )

    await close_mysql_pool()


if __name__ == "__main__":
    asyncio.run(seed("--force" in sys.argv))
