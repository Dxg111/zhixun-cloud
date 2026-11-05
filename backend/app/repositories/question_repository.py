"""题库审核数据访问层"""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()

QUESTION_SELECT = """
SELECT
  q.id, q.tenant_code, q.bank_id, b.name AS bank_name, q.type, q.stem,
  q.options_json, q.answer_json, q.explanation, q.knowledge_point,
  q.difficulty, q.source_ref, q.status, q.ai_meta, q.review_note,
  q.reviewed_by, q.reviewed_at, q.created_at, q.updated_at
FROM questions q
JOIN question_banks b ON q.bank_id = b.id
"""


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _to_question(row: tuple) -> dict:
    return {
        "id": row[0],
        "tenant_code": row[1],
        "bank_id": row[2],
        "bank_name": row[3],
        "type": row[4],
        "stem": row[5],
        "options": _json_value(row[6]),
        "answer": _json_value(row[7]),
        "explanation": row[8],
        "knowledge_point": row[9],
        "difficulty": row[10],
        "source": row[11],
        "status": row[12],
        "ai_meta": row[13],
        "review_note": row[14],
        "reviewed_by": row[15],
        "reviewed_at": _datetime_text(row[16]) or None,
        "created_at": _datetime_text(row[17]),
        "updated_at": _datetime_text(row[18]),
    }


def _build_filters(
    tenant_code: str,
    status: str,
    keyword: str,
    include_status: bool,
    bank_id: int | None = None,
) -> tuple[str, list[Any]]:
    clauses = ["q.tenant_code = %s", "q.deleted_at IS NULL"]
    params: list[Any] = [tenant_code]

    if include_status and status != "all":
        clauses.append("q.status = %s")
        params.append(status)

    if bank_id is not None:
        clauses.append("q.bank_id = %s")
        params.append(bank_id)

    normalized = keyword.strip()
    if normalized:
        like = f"%{normalized}%"
        clauses.append("(q.stem LIKE %s OR q.knowledge_point LIKE %s)")
        params.extend([like, like])

    return " AND ".join(clauses), params


async def list_questions(
    tenant_code: str,
    status: str,
    keyword: str,
    page: int,
    page_size: int,
    bank_id: int | None = None,
) -> tuple[list[dict], int, dict]:
    pool = get_mysql_pool()
    empty_counts = {"all": 0, "draft": 0, "approved": 0, "rejected": 0}
    if pool is None:
        return [], 0, empty_counts

    list_where, list_params = _build_filters(
        tenant_code, status, keyword, True, bank_id
    )
    count_where, count_params = _build_filters(
        tenant_code, "all", keyword, False, bank_id
    )
    offset = (page - 1) * page_size

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) FROM questions q WHERE {list_where}",
                tuple(list_params),
            )
            total_row = await cur.fetchone()
            total = int(total_row[0]) if total_row else 0

            await cur.execute(
                f"SELECT q.status, COUNT(*) FROM questions q "
                f"WHERE {count_where} GROUP BY q.status",
                tuple(count_params),
            )
            counts = dict(empty_counts)
            for row in await cur.fetchall():
                if row[0] in counts:
                    counts[row[0]] = int(row[1])
            counts["all"] = counts["draft"] + counts["approved"] + counts["rejected"]

            await cur.execute(
                f"{QUESTION_SELECT} WHERE {list_where} "
                "ORDER BY q.created_at DESC, q.id DESC LIMIT %s OFFSET %s",
                tuple([*list_params, page_size, offset]),
            )
            rows = await cur.fetchall()

    return [_to_question(row) for row in rows], total, counts


async def get_or_create_bank(
    tenant_code: str,
    name: str,
    description: str = "",
) -> dict:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法创建题库")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, name FROM question_banks WHERE tenant_code = %s AND name = %s",
                (tenant_code, name),
            )
            row = await cur.fetchone()
            if row is None:
                await cur.execute(
                    "INSERT INTO question_banks (tenant_code, name, description, status) "
                    "VALUES (%s, %s, %s, 'active')",
                    (tenant_code, name, description),
                )
                bank_id = int(cur.lastrowid)
            else:
                bank_id = int(row[0])

    return {"id": bank_id, "name": name}


async def create_questions(
    tenant_code: str,
    bank_id: int,
    questions: list[dict],
    source_ref: str,
    ai_meta: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法写入题目")

    created = 0
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for question in questions:
                await cur.execute(
                    "INSERT INTO questions "
                    "(tenant_code, bank_id, type, stem, options_json, answer_json, explanation, "
                    "knowledge_point, difficulty, source_ref, status, ai_meta) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft', %s)",
                    (
                        tenant_code,
                        bank_id,
                        question["type"],
                        question["stem"],
                        json.dumps(question["options"], ensure_ascii=False),
                        json.dumps(question["answer"], ensure_ascii=False),
                        question["explanation"],
                        question.get("knowledge_point", ""),
                        question.get("difficulty", "medium"),
                        source_ref,
                        ai_meta,
                    ),
                )
                created += 1

    return created


async def get_question(tenant_code: str, question_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{QUESTION_SELECT} WHERE q.tenant_code = %s AND q.id = %s "
                "AND q.deleted_at IS NULL",
                (tenant_code, question_id),
            )
            row = await cur.fetchone()
            return _to_question(row) if row else None


async def update_question(
    tenant_code: str,
    question_id: int,
    stem: str,
    options: list[dict],
    answer: list[str],
    explanation: str,
    knowledge_point: str,
    difficulty: str,
) -> int:
    """编辑题目；已通过的题目编辑后回到草稿，需要重新审核。"""
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法编辑题目")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE questions SET stem = %s, options_json = %s, answer_json = %s, "
                "explanation = %s, knowledge_point = %s, difficulty = %s, "
                "status = 'draft', reviewed_by = NULL, reviewed_at = NULL, "
                "review_note = NULL "
                "WHERE tenant_code = %s AND id = %s AND deleted_at IS NULL",
                (
                    stem,
                    json.dumps(options, ensure_ascii=False),
                    json.dumps(answer, ensure_ascii=False),
                    explanation,
                    knowledge_point,
                    difficulty,
                    tenant_code,
                    question_id,
                ),
            )
            return int(cur.rowcount)


async def soft_delete_question(tenant_code: str, question_id: int) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法删除题目")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE questions SET deleted_at = NOW() "
                "WHERE tenant_code = %s AND id = %s AND deleted_at IS NULL",
                (tenant_code, question_id),
            )
            return int(cur.rowcount)


async def review_question(
    tenant_code: str,
    question_id: int,
    status: str,
    note: Optional[str],
    reviewer: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法审核题目")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE questions SET status = %s, review_note = %s, "
                "reviewed_by = %s, reviewed_at = NOW() "
                "WHERE tenant_code = %s AND id = %s",
                (status, note, reviewer, tenant_code, question_id),
            )
            return int(cur.rowcount)


async def bulk_review(
    tenant_code: str,
    question_ids: list[int],
    status: str,
    note: Optional[str],
    reviewer: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法审核题目")

    placeholders = ", ".join(["%s"] * len(question_ids))
    params = [status, note, reviewer, tenant_code, *question_ids]
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE questions SET status = %s, review_note = %s, "
                "reviewed_by = %s, reviewed_at = NOW() "
                f"WHERE tenant_code = %s AND id IN ({placeholders})",
                tuple(params),
            )
            return int(cur.rowcount)


async def list_banks(tenant_code: str) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT b.id, b.name, b.description, "
                "(SELECT COUNT(*) FROM questions q "
                " WHERE q.bank_id = b.id AND q.status = 'approved' "
                "AND q.deleted_at IS NULL) AS approved_count, "
                "(SELECT COUNT(*) FROM questions q WHERE q.bank_id = b.id "
                "AND q.deleted_at IS NULL) AS total_count "
                "FROM question_banks b WHERE b.tenant_code = %s ORDER BY b.id ASC",
                (tenant_code,),
            )
            rows = await cur.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "approved_count": int(row[3] or 0),
            "total_count": int(row[4] or 0),
        }
        for row in rows
    ]


async def list_question_stems(tenant_code: str, bank_id: int) -> list[str]:
    """用于生成时去重的已有题干。"""
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT stem FROM questions "
                "WHERE tenant_code = %s AND bank_id = %s AND deleted_at IS NULL",
                (tenant_code, bank_id),
            )
            return [row[0] for row in await cur.fetchall()]
