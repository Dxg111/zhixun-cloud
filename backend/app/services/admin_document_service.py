"""管理后台文档服务"""

from __future__ import annotations

import asyncio
import os
import uuid

import structlog

from app.core.config import get_settings
from app.core.exceptions import AdminOrgError
from app.models.admin_console import DocumentItem, DocumentListResponse
from app.repositories import admin_document_repository
from app.services import document_loader_service

logger = structlog.get_logger()

SUPPORTED_EXTENSIONS = {"pdf", "docx", "md", "txt"}
MAX_FILE_SIZE = 20 * 1024 * 1024


def _to_item(doc: dict) -> DocumentItem:
    return DocumentItem(
        id=doc["id"],
        tenant_code=doc["tenant_code"],
        file_name=doc["file_name"],
        file_type=doc["file_type"],
        file_size=doc["file_size"],
        status=doc["status"],
        chunks=doc["chunks"],
        error_message=doc.get("error_message"),
        has_file=bool(doc.get("file_path")),
        created_at=doc["created_at"],
    )


async def list_documents(tenant_code: str) -> DocumentListResponse:
    rows = await admin_document_repository.list_documents(tenant_code)
    return DocumentListResponse(items=[_to_item(row) for row in rows], total=len(rows))


async def upload_document(
    tenant_code: str,
    filename: str,
    content: bytes,
    created_by: str,
) -> DocumentItem:
    extension = os.path.splitext(filename)[1].lstrip(".").lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise AdminOrgError("仅支持 PDF、Word、Markdown、TXT 文件")
    if len(content) > MAX_FILE_SIZE:
        raise AdminOrgError("文件不能超过 20MB")

    settings = get_settings()
    upload_dir = os.path.join(settings.kb_upload_dir, "admin")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{uuid.uuid4().hex}.{extension}")
    with open(file_path, "wb") as file:
        file.write(content)

    doc_id = await admin_document_repository.create_document(
        tenant_code=tenant_code,
        file_name=filename,
        file_type=extension,
        file_size=len(content),
        file_path=file_path,
        created_by=created_by,
    )

    try:
        chunks = await asyncio.to_thread(
            document_loader_service.load_and_split,
            file_path,
            extension,
        )
        if not chunks:
            raise ValueError("文档解析后未提取到内容")
        await admin_document_repository.update_document_status(
            tenant_code, doc_id, "ready", chunks=len(chunks)
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("admin_document_parse_failed", doc_id=doc_id, error=str(exc))
        await admin_document_repository.update_document_status(
            tenant_code, doc_id, "failed", error_message=str(exc)[:500]
        )

    doc = await admin_document_repository.get_document(tenant_code, doc_id)
    if doc is None:
        raise AdminOrgError("文档保存失败")
    return _to_item(doc)


async def delete_document(tenant_code: str, doc_id: int) -> None:
    doc = await admin_document_repository.get_document(tenant_code, doc_id)
    if doc is None:
        raise AdminOrgError("文档不存在")

    file_path = doc.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError as exc:
            logger.warning("admin_document_file_delete_failed", doc_id=doc_id, error=str(exc))

    await admin_document_repository.delete_document(tenant_code, doc_id)
