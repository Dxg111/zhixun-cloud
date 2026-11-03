"""管理后台文档数据访问层"""

from __future__ import annotations

from typing import Any, Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()

DOC_SELECT = """
SELECT id, tenant_code, file_name, file_type, file_size, status, chunks,
       error_message, file_path, created_at
FROM admin_documents
"""


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _to_doc(row: tuple) -> dict:
    return {
        "id": row[0],
        "tenant_code": row[1],
        "file_name": row[2],
        "file_type": row[3],
        "file_size": row[4],
        "status": row[5],
        "chunks": row[6],
        "error_message": row[7],
        "file_path": row[8],
        "created_at": _datetime_text(row[9]),
    }


async def list_documents(tenant_code: str) -> list[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return []

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{DOC_SELECT} WHERE tenant_code = %s ORDER BY created_at DESC, id DESC",
                (tenant_code,),
            )
            rows = await cur.fetchall()
            return [_to_doc(row) for row in rows]


async def get_document(tenant_code: str, doc_id: int) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return None

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                f"{DOC_SELECT} WHERE tenant_code = %s AND id = %s",
                (tenant_code, doc_id),
            )
            row = await cur.fetchone()
            return _to_doc(row) if row else None


async def create_document(
    tenant_code: str,
    file_name: str,
    file_type: str,
    file_size: int,
    file_path: str,
    created_by: str,
) -> int:
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("数据库未初始化，无法保存文档")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO admin_documents "
                "(tenant_code, file_name, file_type, file_size, status, file_path, created_by) "
                "VALUES (%s, %s, %s, %s, 'processing', %s, %s)",
                (tenant_code, file_name, file_type, file_size, file_path, created_by),
            )
            return int(cur.lastrowid)


async def update_document_status(
    tenant_code: str,
    doc_id: int,
    status: str,
    chunks: int = 0,
    error_message: Optional[str] = None,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE admin_documents SET status = %s, chunks = %s, error_message = %s "
                "WHERE tenant_code = %s AND id = %s",
                (status, chunks, error_message, tenant_code, doc_id),
            )


async def delete_document(tenant_code: str, doc_id: int) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM admin_documents WHERE tenant_code = %s AND id = %s",
                (tenant_code, doc_id),
            )
