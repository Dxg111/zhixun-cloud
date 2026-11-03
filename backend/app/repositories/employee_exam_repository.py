"""员工考试数据访问层"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from app.core.db import get_mysql_pool


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _date_text(value: Any) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M") if value else None


async def list_exams_for_employee(tenant_code: str, employee_id: int) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT e.id, e.title, e.question_count, e.duration_minutes, e.pass_score, "
                "e.max_attempts, e.start_at, e.end_at, e.status, a.assigned_at, "
                "(SELECT at.id FROM exam_attempts at WHERE at.exam_id = e.id AND at.employee_id = %s "
                " ORDER BY at.id DESC LIMIT 1) AS attempt_id, "
                "(SELECT at.status FROM exam_attempts at WHERE at.exam_id = e.id AND at.employee_id = %s "
                " ORDER BY at.id DESC LIMIT 1) AS attempt_status, "
                "(SELECT at.score FROM exam_attempts at WHERE at.exam_id = e.id AND at.employee_id = %s "
                " ORDER BY at.id DESC LIMIT 1) AS score, "
                "(SELECT at.passed FROM exam_attempts at WHERE at.exam_id = e.id AND at.employee_id = %s "
                " ORDER BY at.id DESC LIMIT 1) AS passed, "
                "(SELECT at.submitted_at FROM exam_attempts at WHERE at.exam_id = e.id AND at.employee_id = %s "
                " ORDER BY at.id DESC LIMIT 1) AS submitted_at, "
                "(SELECT COUNT(*) FROM exam_attempts at WHERE at.exam_id = e.id AND at.employee_id = %s "
                " AND at.status = 'submitted') AS attempt_count "
                "FROM exam_assignments a JOIN exams e ON a.exam_id = e.id "
                "WHERE a.employee_id = %s AND e.tenant_code = %s "
                "AND e.status IN ('published', 'closed') "
                "AND EXISTS (SELECT 1 FROM exam_questions q WHERE q.exam_id = e.id) "
                "ORDER BY a.assigned_at DESC, e.id DESC",
                (
                    employee_id,
                    employee_id,
                    employee_id,
                    employee_id,
                    employee_id,
                    employee_id,
                    employee_id,
                    tenant_code,
                ),
            )
            rows = await cur.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "question_count": row[2],
            "duration_minutes": row[3],
            "pass_score": row[4],
            "max_attempts": row[5],
            "start_at": _date_text(row[6]),
            "end_at": _date_text(row[7]),
            "status": row[8],
            "assigned_at": _datetime_text(row[9]),
            "attempt_id": row[10],
            "attempt_status": row[11],
            "score": float(row[12]) if row[12] is not None else None,
            "passed": bool(row[13]) if row[13] is not None else None,
            "submitted_at": _datetime_text(row[14]) or None,
            "attempt_count": int(row[15] or 0),
        }
        for row in rows
    ]


async def get_assignment(tenant_code: str, exam_id: int, employee_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT a.assigned_at, e.id, e.title, e.status, e.duration_minutes, "
                "e.start_at, e.end_at, e.pass_score, e.max_attempts "
                "FROM exam_assignments a JOIN exams e ON a.exam_id = e.id "
                "WHERE a.exam_id = %s AND a.employee_id = %s AND e.tenant_code = %s",
                (exam_id, employee_id, tenant_code),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return {
                "assigned_at": _datetime_text(row[0]),
                "exam_id": row[1],
                "title": row[2],
                "status": row[3],
                "duration_minutes": row[4],
                "start_at": row[5],
                "end_at": row[6],
                "pass_score": row[7],
                "max_attempts": row[8],
            }


async def get_in_progress_attempt(
    tenant_code: str,
    exam_id: int,
    employee_id: int,
) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT at.id, at.exam_id, at.employee_id, at.attempt_no, at.status, at.score, "
                "at.passed, at.started_at, at.submitted_at, at.duration_seconds, at.expires_at, "
                "at.answers_json, e.tenant_code, e.title, e.pass_score "
                "FROM exam_attempts at JOIN exams e ON at.exam_id = e.id "
                "WHERE at.exam_id = %s AND at.employee_id = %s AND e.tenant_code = %s "
                "AND at.status = 'in_progress' ORDER BY at.id DESC LIMIT 1",
                (exam_id, employee_id, tenant_code),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            data = _to_attempt(row)
            data["tenant_code"] = row[12]
            data["title"] = row[13]
            data["pass_score"] = row[14]
            return data


async def count_submitted_attempts(
    tenant_code: str,
    exam_id: int,
    employee_id: int,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM exam_attempts at "
                "JOIN exams e ON at.exam_id = e.id "
                "WHERE e.tenant_code = %s AND at.exam_id = %s AND at.employee_id = %s "
                "AND at.status = 'submitted'",
                (tenant_code, exam_id, employee_id),
            )
            row = await cur.fetchone()
            return int(row[0]) if row else 0


async def create_attempt(
    exam_id: int,
    employee_id: int,
    attempt_no: int,
    expires_at: Any,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法开始考试")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO exam_attempts "
                "(exam_id, employee_id, attempt_no, status, started_at, expires_at) "
                "VALUES (%s, %s, %s, 'in_progress', NOW(), %s)",
                (exam_id, employee_id, attempt_no, expires_at),
            )
            return int(cur.lastrowid)


async def get_attempt(
    tenant_code: str,
    attempt_id: int,
    employee_id: int,
) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT at.id, at.exam_id, at.employee_id, at.attempt_no, at.status, at.score, "
                "at.passed, at.started_at, at.submitted_at, at.duration_seconds, at.expires_at, "
                "at.answers_json, e.title, e.pass_score, e.tenant_code "
                "FROM exam_attempts at JOIN exams e ON at.exam_id = e.id "
                "WHERE at.id = %s AND at.employee_id = %s AND e.tenant_code = %s",
                (attempt_id, employee_id, tenant_code),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            data = _to_attempt(row)
            data["title"] = row[12]
            data["pass_score"] = row[13]
            data["tenant_code"] = row[14]
            return data


async def save_answers(attempt_id: int, answers_json: str) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE exam_attempts SET answers_json = %s WHERE id = %s",
                (answers_json, attempt_id),
            )


async def submit_attempt(
    attempt_id: int,
    score: float,
    passed: bool,
    answers_json: str,
    duration_seconds: int,
) -> bool:
    pool = get_mysql_pool()
    if pool is None:
        return False

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE exam_attempts SET status = 'submitted', score = %s, passed = %s, "
                "answers_json = %s, submitted_at = NOW(), duration_seconds = %s "
                "WHERE id = %s AND status = 'in_progress'",
                (score, int(passed), answers_json, duration_seconds, attempt_id),
            )
            return int(cur.rowcount) == 1


async def get_paper_questions(exam_id: int) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT question_id, snapshot_json, sort, score FROM exam_questions "
                "WHERE exam_id = %s ORDER BY sort ASC, id ASC",
                (exam_id,),
            )
            rows = await cur.fetchall()

    result = []
    for row in rows:
        snapshot = row[1]
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        result.append(
            {
                "question_id": row[0],
                "snapshot": snapshot,
                "sort": row[2],
                "score": float(row[3]),
            }
        )
    return result


def _to_attempt(row: tuple) -> dict:
    answers = row[11]
    if isinstance(answers, str):
        try:
            answers = json.loads(answers)
        except ValueError:
            answers = []
    return {
        "id": row[0],
        "exam_id": row[1],
        "employee_id": row[2],
        "attempt_no": row[3],
        "status": row[4],
        "score": float(row[5]) if row[5] is not None else None,
        "passed": bool(row[6]) if row[6] is not None else None,
        "started_at": _datetime_text(row[7]),
        "submitted_at": _datetime_text(row[8]) or None,
        "duration_seconds": row[9],
        "expires_at": _datetime_text(row[10]),
        "expires_at_dt": row[10] if isinstance(row[10], datetime) else None,
        "answers": answers or [],
    }
