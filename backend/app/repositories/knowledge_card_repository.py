"""知识卡数据访问层"""

from __future__ import annotations

import json
from typing import Any, Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()

CARD_SELECT = """
SELECT id, tenant_code, doc_id, doc_name, title, excerpt, source_ref, status,
       view_rate, created_by, published_at, created_at, updated_at, content_json
FROM knowledge_cards
"""


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _json_value(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return None
    return value


def _to_card(row: tuple) -> dict:
    return {
        "id": row[0],
        "tenant_code": row[1],
        "doc_id": row[2],
        "doc_name": row[3],
        "title": row[4],
        "excerpt": row[5],
        "source": row[6],
        "status": row[7],
        "view_rate": row[8],
        "created_by": row[9],
        "published_at": _datetime_text(row[10]) or None,
        "created_at": _datetime_text(row[11]),
        "updated_at": _datetime_text(row[12]),
        "content_json": _json_value(row[13]),
    }


async def list_cards(
    tenant_code: str,
    status: str,
    keyword: str,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    pool = get_mysql_pool()
    if pool is None:
        return [], 0

    clauses = ["tenant_code = %s"]
    params: list[Any] = [tenant_code]

    if status != "all":
        clauses.append("status = %s")
        params.append(status)

    normalized = keyword.strip()
    if normalized:
        like = f"%{normalized}%"
        clauses.append("(title LIKE %s OR excerpt LIKE %s OR doc_name LIKE %s)")
        params.extend([like, like, like])

    where = " AND ".join(clauses)
    offset = (page - 1) * page_size

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(f"SELECT COUNT(*) FROM knowledge_cards WHERE {where}", tuple(params))
            total_row = await cur.fetchone()
            total = int(total_row[0]) if total_row else 0

            await cur.execute(
                f"{CARD_SELECT} WHERE {where} ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
                tuple([*params, page_size, offset]),
            )
            rows = await cur.fetchall()

    return [_to_card(row) for row in rows], total


async def get_card(tenant_code: str, card_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{CARD_SELECT} WHERE tenant_code = %s AND id = %s",
                (tenant_code, card_id),
            )
            row = await cur.fetchone()
            return _to_card(row) if row else None


async def create_card(
    tenant_code: str,
    doc_name: str,
    title: str,
    excerpt: str,
    source: str,
    status: str,
    view_rate: int,
    created_by: Optional[str],
    doc_id: int | None = None,
    content_json: str | None = None,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法创建知识卡")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO knowledge_cards "
                "(tenant_code, doc_id, doc_name, title, excerpt, source_ref, status, view_rate, "
                "created_by, content_json) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    tenant_code,
                    doc_id,
                    doc_name,
                    title,
                    excerpt,
                    source,
                    status,
                    view_rate,
                    created_by,
                    content_json,
                ),
            )
            return int(cur.lastrowid)


async def update_status(tenant_code: str, card_id: int, status: str) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新知识卡状态")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE knowledge_cards SET status = %s, "
                "published_at = CASE WHEN %s = 'published' THEN NOW() ELSE published_at END "
                "WHERE tenant_code = %s AND id = %s",
                (status, status, tenant_code, card_id),
            )
            return int(cur.rowcount)


async def update_card(
    tenant_code: str,
    card_id: int,
    title: str,
    excerpt: str,
    content_json: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法更新知识卡")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE knowledge_cards SET title = %s, excerpt = %s, content_json = %s "
                "WHERE tenant_code = %s AND id = %s",
                (title, excerpt, content_json, tenant_code, card_id),
            )
            return int(cur.rowcount)


async def count_cards(tenant_code: str) -> int:
    pool = get_mysql_pool()
    if pool is None:
        return 0

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM knowledge_cards WHERE tenant_code = %s",
                (tenant_code,),
            )
            row = await cur.fetchone()
            return int(row[0]) if row else 0


# ---- 考试与知识卡关联 ----


async def list_cards_by_exam(
    tenant_code: str,
    exam_id: int,
    published_only: bool = False,
) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    status_clause = " AND kc.status = 'published'" if published_only else ""
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT kc.id, kc.tenant_code, kc.doc_id, kc.doc_name, kc.title, kc.excerpt, "
                "kc.source_ref, kc.status, kc.view_rate, kc.created_by, kc.published_at, "
                "kc.created_at, kc.updated_at, kc.content_json "
                "FROM exam_knowledge_cards ekc "
                "JOIN knowledge_cards kc ON ekc.card_id = kc.id "
                "WHERE ekc.tenant_code = %s AND ekc.exam_id = %s"
                f"{status_clause} "
                "ORDER BY ekc.sort ASC, kc.id ASC",
                (tenant_code, exam_id),
            )
            rows = await cur.fetchall()
    return [_to_card(row) for row in rows]


async def list_published_card_ids(tenant_code: str, card_ids: list[int]) -> list[int]:
    if not card_ids:
        return []

    pool = get_mysql_pool()
    if pool is None:
        return []

    placeholders = ", ".join(["%s"] * len(card_ids))
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id FROM knowledge_cards "
                f"WHERE tenant_code = %s AND status = 'published' AND id IN ({placeholders})",
                tuple([tenant_code, *card_ids]),
            )
            return [int(row[0]) for row in await cur.fetchall()]


async def set_exam_cards(tenant_code: str, exam_id: int, card_ids: list[int]) -> None:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法关联知识卡")

    async with pool.acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM exam_knowledge_cards WHERE tenant_code = %s AND exam_id = %s",
                    (tenant_code, exam_id),
                )
                for index, card_id in enumerate(card_ids, start=1):
                    await cur.execute(
                        "INSERT INTO exam_knowledge_cards "
                        "(tenant_code, exam_id, card_id, sort) VALUES (%s, %s, %s, %s)",
                        (tenant_code, exam_id, card_id, index),
                    )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise


# ---- 阅读记录 ----


async def upsert_view(tenant_code: str, employee_id: int, card_id: int) -> None:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法记录知识卡阅读")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO knowledge_card_views (tenant_code, employee_id, card_id) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE last_viewed_at = NOW(), view_count = view_count + 1",
                (tenant_code, employee_id, card_id),
            )


async def list_views_for_employee(
    tenant_code: str,
    employee_id: int,
    card_ids: list[int],
) -> dict[int, int]:
    if not card_ids:
        return {}

    pool = get_mysql_pool()
    if pool is None:
        return {}

    placeholders = ", ".join(["%s"] * len(card_ids))
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT card_id, view_count FROM knowledge_card_views "
                f"WHERE tenant_code = %s AND employee_id = %s AND card_id IN ({placeholders})",
                tuple([tenant_code, employee_id, *card_ids]),
            )
            return {int(row[0]): int(row[1]) for row in await cur.fetchall()}


async def is_card_visible_to_employee(
    tenant_code: str,
    employee_id: int,
    card_id: int,
) -> bool:
    pool = get_mysql_pool()
    if pool is None:
        return False

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM knowledge_cards kc "
                "JOIN exam_knowledge_cards ekc ON ekc.card_id = kc.id "
                "JOIN exams e ON ekc.exam_id = e.id "
                "JOIN exam_assignments ea ON ea.exam_id = ekc.exam_id "
                "WHERE kc.id = %s AND kc.tenant_code = %s AND kc.status = 'published' "
                "AND e.status IN ('published', 'closed') AND ea.employee_id = %s LIMIT 1",
                (card_id, tenant_code, employee_id),
            )
            return await cur.fetchone() is not None
