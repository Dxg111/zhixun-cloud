"""考试与工作台数据访问层"""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()

EXAM_SELECT = """
SELECT e.id, e.tenant_code, e.title, e.bank_id, b.name AS bank_name,
       e.question_count, e.pass_score, e.duration_minutes, e.max_attempts,
       e.start_at, e.end_at, e.status,
       (SELECT COUNT(*) FROM exam_assignments a WHERE a.exam_id = e.id) AS assigned,
       (SELECT COUNT(DISTINCT at.employee_id) FROM exam_attempts at
        WHERE at.exam_id = e.id AND at.status = 'submitted') AS completed,
       (SELECT COUNT(DISTINCT at.employee_id) FROM exam_attempts at
        WHERE at.exam_id = e.id AND at.status = 'submitted' AND at.passed = 1) AS passed,
       (SELECT COUNT(DISTINCT v.employee_id)
        FROM knowledge_card_views v
        JOIN exam_knowledge_cards ekc ON ekc.card_id = v.card_id
        JOIN exam_assignments ea ON ea.exam_id = ekc.exam_id AND ea.employee_id = v.employee_id
        WHERE ekc.exam_id = e.id AND v.tenant_code = e.tenant_code) AS card_viewers,
       e.created_at
FROM exams e
JOIN question_banks b ON e.bank_id = b.id
"""


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _date_text(value: Any) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M") if value else None


def _to_exam(row: tuple) -> dict:
    assigned = int(row[12] or 0)
    completed = int(row[13] or 0)
    passed = int(row[14] or 0)
    card_viewers = int(row[15] or 0)
    pass_rate = round(passed / completed * 100) if completed else 0
    card_view_rate = round(card_viewers / assigned * 100) if assigned else 0
    return {
        "id": row[0],
        "tenant_code": row[1],
        "title": row[2],
        "bank_id": row[3],
        "bank_name": row[4],
        "question_count": row[5],
        "pass_score": row[6],
        "duration_minutes": row[7],
        "max_attempts": row[8],
        "start_at": _date_text(row[9]),
        "end_at": _date_text(row[10]),
        "status": row[11],
        "assigned": assigned,
        "completed": completed,
        "pass_rate": pass_rate,
        "card_view_rate": card_view_rate,
        "created_at": _datetime_text(row[16]),
    }


async def get_bank_by_name(tenant_code: str, bank_name: str) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name FROM question_banks WHERE tenant_code = %s AND name = %s",
                (tenant_code, bank_name),
            )
            row = await cur.fetchone()
            return {"id": row[0], "name": row[1]} if row else None


async def list_exams(
    tenant_code: str,
    status: str,
    keyword: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int, dict]:
    pool = get_mysql_pool()
    empty = {"all": 0, "draft": 0, "published": 0, "closed": 0}
    if pool is None:
        return [], 0, empty

    clauses = ["e.tenant_code = %s"]
    params: list[Any] = [tenant_code]
    if status != "all":
        clauses.append("e.status = %s")
        params.append(status)
    normalized = keyword.strip()
    if normalized:
        like = f"%{normalized}%"
        clauses.append("(e.title LIKE %s OR b.name LIKE %s)")
        params.extend([like, like])
    where = " AND ".join(clauses)
    offset = (page - 1) * page_size

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM exams e JOIN question_banks b ON e.bank_id = b.id "
                f"WHERE {where}",
                tuple(params),
            )
            total = int((await cur.fetchone())[0])

            await cur.execute(
                "SELECT e.status, COUNT(*) FROM exams e "
                "WHERE e.tenant_code = %s GROUP BY e.status",
                (tenant_code,),
            )
            counts = dict(empty)
            for row in await cur.fetchall():
                if row[0] in counts:
                    counts[row[0]] = int(row[1])
            counts["all"] = counts["draft"] + counts["published"] + counts["closed"]

            await cur.execute(
                f"{EXAM_SELECT} WHERE {where} ORDER BY e.created_at DESC, e.id DESC "
                "LIMIT %s OFFSET %s",
                tuple([*params, page_size, offset]),
            )
            rows = await cur.fetchall()

    return [_to_exam(row) for row in rows], total, counts


async def get_exam(tenant_code: str, exam_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{EXAM_SELECT} WHERE e.tenant_code = %s AND e.id = %s",
                (tenant_code, exam_id),
            )
            row = await cur.fetchone()
            return _to_exam(row) if row else None


async def create_exam(
    tenant_code: str,
    title: str,
    bank_id: int,
    question_count: int,
    pass_score: int,
    duration_minutes: int,
    max_attempts: int,
    start_at: str | None,
    end_at: str | None,
    created_by: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法创建考试")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO exams "
                "(tenant_code, title, bank_id, question_count, pass_score, duration_minutes, "
                "max_attempts, start_at, end_at, status, created_by) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft', %s)",
                (
                    tenant_code,
                    title,
                    bank_id,
                    question_count,
                    pass_score,
                    duration_minutes,
                    max_attempts,
                    start_at,
                    end_at,
                    created_by,
                ),
            )
            return int(cur.lastrowid)


async def publish_exam(tenant_code: str, exam_id: int) -> int:
    """发布考试：冻结题目快照并指派全部在职员工。"""
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法发布考试")

    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT bank_id, question_count, status FROM exams "
                    "WHERE tenant_code = %s AND id = %s",
                    (tenant_code, exam_id),
                )
                exam = await cur.fetchone()
                if exam is None:
                    raise ValueError("考试不存在")
                bank_id, question_count, status = exam
                if status != "draft":
                    raise ValueError("只有草稿考试可以发布")

                await cur.execute(
                    "SELECT id, type, stem, options_json, answer_json, explanation, "
                    "knowledge_point, difficulty, source_ref FROM questions "
                    "WHERE tenant_code = %s AND bank_id = %s AND status = 'approved' "
                    "ORDER BY id ASC LIMIT %s",
                    (tenant_code, bank_id, question_count),
                )
                questions = await cur.fetchall()
                if len(questions) < question_count:
                    raise ValueError(
                        f"可用已通过题目不足：需要 {question_count} 道，当前 {len(questions)} 道"
                    )

                base_score = round(100 / len(questions), 2)
                scores = [base_score] * len(questions)
                scores[-1] = round(100 - sum(scores[:-1]), 2)

                for index, (row, score) in enumerate(zip(questions, scores), start=1):
                    snapshot = {
                        "id": row[0],
                        "type": row[1],
                        "stem": row[2],
                        "options": json.loads(row[3]) if isinstance(row[3], str) else row[3],
                        "answer": json.loads(row[4]) if isinstance(row[4], str) else row[4],
                        "explanation": row[5],
                        "knowledge_point": row[6],
                        "difficulty": row[7],
                        "source": row[8],
                    }
                    await cur.execute(
                        "INSERT INTO exam_questions (exam_id, question_id, snapshot_json, sort, score) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (exam_id, row[0], json.dumps(snapshot, ensure_ascii=False), index, score),
                    )

                await cur.execute(
                    "SELECT COUNT(*) FROM exam_assignments WHERE exam_id = %s",
                    (exam_id,),
                )
                assigned_row = await cur.fetchone()
                assigned = int(assigned_row[0]) if assigned_row else 0
                if assigned == 0:
                    await cur.execute(
                        "SELECT id FROM employees WHERE tenant_code = %s AND status = 'active' ORDER BY id ASC",
                        (tenant_code,),
                    )
                    employees = await cur.fetchall()
                    for employee in employees:
                        await cur.execute(
                            "INSERT IGNORE INTO exam_assignments (exam_id, employee_id) VALUES (%s, %s)",
                            (exam_id, employee[0]),
                        )
                    assigned = len(employees)

                await cur.execute(
                    "UPDATE exams SET status = 'published' WHERE tenant_code = %s AND id = %s",
                    (tenant_code, exam_id),
                )
            await conn.commit()
            return assigned
        except Exception:
            await conn.rollback()
            raise


async def close_exam(tenant_code: str, exam_id: int) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法关闭考试")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE exams SET status = 'closed' "
                "WHERE tenant_code = %s AND id = %s AND status = 'published'",
                (tenant_code, exam_id),
            )
            return int(cur.rowcount)


async def list_assigned_employee_ids(exam_id: int) -> list[int]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT employee_id FROM exam_assignments WHERE exam_id = %s ORDER BY employee_id ASC",
                (exam_id,),
            )
            return [int(row[0]) for row in await cur.fetchall()]


async def list_incomplete_employee_ids(exam_id: int) -> list[int]:
    """已指派但尚未提交的考试员工。"""
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT a.employee_id FROM exam_assignments a "
                "WHERE a.exam_id = %s AND NOT EXISTS ("
                "SELECT 1 FROM exam_attempts at WHERE at.exam_id = a.exam_id "
                "AND at.employee_id = a.employee_id AND at.status = 'submitted') "
                "ORDER BY a.employee_id ASC",
                (exam_id,),
            )
            return [int(row[0]) for row in await cur.fetchall()]


async def replace_assignments(
    tenant_code: str,
    exam_id: int,
    employee_ids: list[int],
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法配置指派")

    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM exam_assignments WHERE exam_id = %s",
                    (exam_id,),
                )
                for employee_id in employee_ids:
                    await cur.execute(
                        "INSERT IGNORE INTO exam_assignments (exam_id, employee_id) VALUES (%s, %s)",
                        (exam_id, employee_id),
                    )
                await cur.execute(
                    "SELECT COUNT(*) FROM exam_assignments WHERE exam_id = %s",
                    (exam_id,),
                )
                row = await cur.fetchone()
                assigned = int(row[0]) if row else 0
            await conn.commit()
            return assigned
        except Exception:
            await conn.rollback()
            raise


async def list_employee_ids_by_org_paths(
    tenant_code: str,
    org_paths: list[str],
) -> list[int]:
    if not org_paths:
        return []

    pool = get_mysql_pool()
    if pool is None:
        return []

    clauses = []
    params: list[Any] = [tenant_code]
    for path in org_paths:
        clauses.append("(o.path = %s OR o.path LIKE %s)")
        params.extend([path, f"{path}/%"])

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT DISTINCT e.id FROM employees e "
                "LEFT JOIN org_units o ON e.org_id = o.id "
                "WHERE e.tenant_code = %s AND e.status = 'active' "
                f"AND ({' OR '.join(clauses)}) ORDER BY e.id ASC",
                tuple(params),
            )
            return [int(row[0]) for row in await cur.fetchall()]


async def list_active_employee_ids_by_ids(
    tenant_code: str,
    employee_ids: list[int],
) -> list[int]:
    if not employee_ids:
        return []

    pool = get_mysql_pool()
    if pool is None:
        return []

    placeholders = ", ".join(["%s"] * len(employee_ids))
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM employees "
                f"WHERE tenant_code = %s AND status = 'active' AND id IN ({placeholders}) "
                "ORDER BY id ASC",
                tuple([tenant_code, *employee_ids]),
            )
            return [int(row[0]) for row in await cur.fetchall()]


async def get_distribution(tenant_code: str, exam_id: int) -> list[int]:
    pool = get_mysql_pool()
    if pool is None:
        return [0, 0, 0, 0, 0]

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT a.score FROM exam_attempts a "
                "JOIN exams e ON a.exam_id = e.id "
                "WHERE e.tenant_code = %s AND a.exam_id = %s AND a.status = 'submitted'",
                (tenant_code, exam_id),
            )
            scores = [float(row[0]) for row in await cur.fetchall() if row[0] is not None]

    buckets = [0, 0, 0, 0, 0]
    for score in scores:
        if score < 60:
            buckets[0] += 1
        elif score < 70:
            buckets[1] += 1
        elif score < 80:
            buckets[2] += 1
        elif score < 90:
            buckets[3] += 1
        else:
            buckets[4] += 1
    return buckets


async def dashboard_counts(tenant_code: str) -> dict:
    pool = get_mysql_pool()
    if pool is None:
        return {
            "pending_questions": 0,
            "pending_cards": 0,
            "pending_join_requests": 0,
            "active_exams": 0,
            "completion_rate": 0,
        }

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM questions WHERE tenant_code = %s AND status = 'draft'",
                (tenant_code,),
            )
            pending_questions = int((await cur.fetchone())[0])

            await cur.execute(
                "SELECT COUNT(*) FROM knowledge_cards WHERE tenant_code = %s AND status = 'draft'",
                (tenant_code,),
            )
            pending_cards = int((await cur.fetchone())[0])

            await cur.execute(
                "SELECT COUNT(*) FROM employee_join_requests "
                "WHERE tenant_code = %s AND status = 'pending'",
                (tenant_code,),
            )
            pending_join_requests = int((await cur.fetchone())[0])

            await cur.execute(
                "SELECT COUNT(*) FROM exams WHERE tenant_code = %s AND status = 'published'",
                (tenant_code,),
            )
            active_exams = int((await cur.fetchone())[0])

            await cur.execute(
                "SELECT COUNT(*) FROM exam_assignments a "
                "JOIN exams e ON a.exam_id = e.id "
                "WHERE e.tenant_code = %s",
                (tenant_code,),
            )
            assigned = int((await cur.fetchone())[0])

            await cur.execute(
                "SELECT COUNT(DISTINCT a.exam_id, a.employee_id) FROM exam_assignments a "
                "JOIN exams e ON a.exam_id = e.id "
                "JOIN exam_attempts at ON at.exam_id = a.exam_id AND at.employee_id = a.employee_id "
                "WHERE e.tenant_code = %s AND at.status = 'submitted'",
                (tenant_code,),
            )
            completed = int((await cur.fetchone())[0])

    return {
        "pending_questions": pending_questions,
        "pending_cards": pending_cards,
        "pending_join_requests": pending_join_requests,
        "active_exams": active_exams,
        "completion_rate": round(completed / assigned * 100) if assigned else 0,
    }
