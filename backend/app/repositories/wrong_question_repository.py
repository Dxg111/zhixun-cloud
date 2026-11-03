"""个人错题数据访问层"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.core.db import get_mysql_pool

WRONG_SELECT = """
SELECT id, tenant_code, employee_id, question_id, question_snapshot_json,
       source_type, source_id, wrong_count, correct_streak, last_wrong_at,
       mastered_at, created_at
FROM wrong_questions
"""


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return {}
    return value or {}


def _to_wrong(row: tuple) -> dict:
    return {
        "id": row[0],
        "tenant_code": row[1],
        "employee_id": row[2],
        "question_id": row[3],
        "snapshot": _json_value(row[4]),
        "source_type": row[5],
        "source_id": row[6],
        "wrong_count": row[7],
        "correct_streak": row[8],
        "last_wrong_at": _datetime_text(row[9]),
        "mastered_at": _datetime_text(row[10]) or None,
        "created_at": _datetime_text(row[11]),
    }


async def upsert_from_exam(
    tenant_code: str,
    employee_id: int,
    attempt_id: int,
    wrong_items: list[dict],
) -> None:
    if not wrong_items:
        return

    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法写入错题")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for snapshot in wrong_items:
                question_id = int(snapshot.get("id", 0)) or None
                await cur.execute(
                    "INSERT INTO wrong_questions "
                    "(tenant_code, employee_id, question_id, question_snapshot_json, "
                    "source_type, source_id, wrong_count, correct_streak, last_wrong_at) "
                    "VALUES (%s, %s, %s, %s, 'exam', %s, 1, 0, NOW()) "
                    "ON DUPLICATE KEY UPDATE "
                    "wrong_count = wrong_count + 1, "
                    "correct_streak = 0, "
                    "mastered_at = NULL, "
                    "last_wrong_at = NOW(), "
                    "question_snapshot_json = VALUES(question_snapshot_json), "
                    "source_id = VALUES(source_id)",
                    (
                        tenant_code,
                        employee_id,
                        question_id,
                        json.dumps(snapshot, ensure_ascii=False),
                        str(attempt_id),
                    ),
                )


async def list_wrong_questions(
    tenant_code: str,
    employee_id: int,
    mastered: Optional[bool],
) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    clauses = ["tenant_code = %s", "employee_id = %s"]
    params: list[Any] = [tenant_code, employee_id]
    if mastered is True:
        clauses.append("mastered_at IS NOT NULL")
    elif mastered is False:
        clauses.append("mastered_at IS NULL")

    where = " AND ".join(clauses)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{WRONG_SELECT} WHERE {where} ORDER BY last_wrong_at DESC, id DESC",
                tuple(params),
            )
            rows = await cur.fetchall()
    return [_to_wrong(row) for row in rows]


async def get_wrong_question(
    tenant_code: str,
    employee_id: int,
    wrong_id: int,
) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{WRONG_SELECT} WHERE tenant_code = %s AND employee_id = %s AND id = %s",
                (tenant_code, employee_id, wrong_id),
            )
            row = await cur.fetchone()
            return _to_wrong(row) if row else None


async def mark_correct(
    tenant_code: str,
    employee_id: int,
    wrong_id: int,
    correct_streak: int,
    mastered: bool,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新错题")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE wrong_questions SET correct_streak = %s, "
                "mastered_at = CASE WHEN %s THEN COALESCE(mastered_at, NOW()) ELSE NULL END "
                "WHERE tenant_code = %s AND employee_id = %s AND id = %s",
                (correct_streak, int(mastered), tenant_code, employee_id, wrong_id),
            )


async def mark_wrong(
    tenant_code: str,
    employee_id: int,
    wrong_id: int,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新错题")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE wrong_questions SET wrong_count = wrong_count + 1, "
                "correct_streak = 0, mastered_at = NULL, last_wrong_at = NOW() "
                "WHERE tenant_code = %s AND employee_id = %s AND id = %s",
                (tenant_code, employee_id, wrong_id),
            )


async def set_mastered(
    tenant_code: str,
    employee_id: int,
    wrong_id: int,
    mastered: bool,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新错题")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE wrong_questions SET "
                "mastered_at = CASE WHEN %s THEN NOW() ELSE NULL END, "
                "correct_streak = CASE WHEN %s THEN correct_streak ELSE 0 END "
                "WHERE tenant_code = %s AND employee_id = %s AND id = %s",
                (int(mastered), int(mastered), tenant_code, employee_id, wrong_id),
            )
