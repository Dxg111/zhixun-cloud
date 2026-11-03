"""知识卡服务：真实 LLM 生成、审核、编辑与发布"""

from __future__ import annotations

import asyncio
import json
import os

import structlog

from app.core.exceptions import KnowledgeCardError
from app.llm import knowledge_card_chain
from app.models.knowledge_card import (
    KnowledgeCardDetail,
    KnowledgeCardGenerateRequest,
    KnowledgeCardItem,
    KnowledgeCardListResponse,
    KnowledgeCardPoint,
    KnowledgeCardUpdateRequest,
)
from app.repositories import admin_document_repository, knowledge_card_repository
from app.services import document_loader_service

logger = structlog.get_logger()

MAX_CONTENT_LENGTH = 12000
MAX_SAMPLE_CHUNKS = 12


def _to_item(card: dict) -> KnowledgeCardItem:
    return KnowledgeCardItem(**card)


def _card_points(card: dict) -> list[KnowledgeCardPoint]:
    content = card.get("content_json")
    if not isinstance(content, dict):
        return []
    raw_points = content.get("points") or content.get("sections") or []
    points: list[KnowledgeCardPoint] = []
    for item in raw_points:
        if not isinstance(item, dict):
            continue
        heading = str(item.get("heading") or "").strip()
        body = str(item.get("body") or "").strip()
        if heading and body:
            points.append(KnowledgeCardPoint(heading=heading, body=body))
    return points


def _to_detail(card: dict) -> KnowledgeCardDetail:
    return KnowledgeCardDetail(**_to_item(card).model_dump(), points=_card_points(card))


def _sample_content(chunks: list) -> str:
    if not chunks:
        return ""

    if len(chunks) <= MAX_SAMPLE_CHUNKS:
        selected = chunks
    else:
        step = (len(chunks) - 1) / (MAX_SAMPLE_CHUNKS - 1)
        selected = [chunks[round(index * step)] for index in range(MAX_SAMPLE_CHUNKS)]

    content = "\n\n".join(chunk.page_content for chunk in selected)
    return content[:MAX_CONTENT_LENGTH]


async def list_cards(
    tenant_code: str,
    status: str,
    keyword: str,
    page: int,
    page_size: int,
) -> KnowledgeCardListResponse:
    items, total = await knowledge_card_repository.list_cards(
        tenant_code=tenant_code,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return KnowledgeCardListResponse(
        items=[_to_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_card_detail(tenant_code: str, card_id: int) -> KnowledgeCardDetail:
    card = await knowledge_card_repository.get_card(tenant_code, card_id)
    if card is None:
        raise KnowledgeCardError("知识卡不存在")
    return _to_detail(card)


async def generate_cards(
    tenant_code: str,
    req: KnowledgeCardGenerateRequest,
    created_by: str,
) -> KnowledgeCardListResponse:
    if not req.doc_id:
        raise KnowledgeCardError("请选择来源文档")

    doc = await admin_document_repository.get_document(tenant_code, req.doc_id)
    if doc is None:
        raise KnowledgeCardError("文档不存在")
    if doc["status"] != "ready":
        raise KnowledgeCardError("文档尚未解析完成")

    file_path = doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise KnowledgeCardError("文档文件不存在，请重新上传")

    try:
        chunks = await asyncio.to_thread(
            document_loader_service.load_and_split,
            file_path,
            doc["file_type"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("knowledge_card_load_failed", doc_id=req.doc_id, error=str(exc))
        raise KnowledgeCardError("文档内容读取失败") from exc

    content = _sample_content(chunks)
    if not content.strip():
        raise KnowledgeCardError("文档内容为空")

    batch = None
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            batch = await knowledge_card_chain.generate_knowledge_cards(
                content=content,
                card_count=req.count,
                style=req.style,
            )
            if batch.cards:
                break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.warning(
                "knowledge_card_llm_failed",
                doc_id=req.doc_id,
                attempt=attempt + 1,
                error=str(exc),
            )

    if batch is None or not batch.cards:
        raise KnowledgeCardError(f"AI 生成知识卡失败：{last_error}")

    cards = batch.cards[: req.count]
    created: list[KnowledgeCardItem] = []
    for draft in cards:
        content_json = json.dumps(
            {"points": [point.model_dump() for point in draft.points]},
            ensure_ascii=False,
        )
        excerpt = draft.points[0].body if draft.points else draft.title
        card_id = await knowledge_card_repository.create_card(
            tenant_code=tenant_code,
            doc_name=doc["file_name"],
            title=draft.title,
            excerpt=excerpt[:500],
            source=draft.source_ref or doc["file_name"],
            status="draft",
            view_rate=0,
            created_by=created_by,
            doc_id=req.doc_id,
            content_json=content_json,
        )
        card = await knowledge_card_repository.get_card(tenant_code, card_id)
        if card:
            created.append(_to_item(card))

    logger.info(
        "knowledge_cards_generated",
        tenant_code=tenant_code,
        doc_id=req.doc_id,
        count=len(created),
    )
    return KnowledgeCardListResponse(
        items=created,
        total=len(created),
        page=1,
        page_size=len(created),
    )


async def update_card(
    tenant_code: str,
    card_id: int,
    req: KnowledgeCardUpdateRequest,
) -> KnowledgeCardDetail:
    card = await knowledge_card_repository.get_card(tenant_code, card_id)
    if card is None:
        raise KnowledgeCardError("知识卡不存在")

    content_json = json.dumps(
        {"points": [point.model_dump() for point in req.points]},
        ensure_ascii=False,
    )
    await knowledge_card_repository.update_card(
        tenant_code=tenant_code,
        card_id=card_id,
        title=req.title,
        excerpt=req.excerpt,
        content_json=content_json,
    )
    return await get_card_detail(tenant_code, card_id)


async def update_card_status(
    tenant_code: str,
    card_id: int,
    status: str,
) -> KnowledgeCardItem:
    target = await knowledge_card_repository.get_card(tenant_code, card_id)
    if target is None:
        raise KnowledgeCardError("知识卡不存在")

    await knowledge_card_repository.update_status(tenant_code, card_id, status)
    updated = await knowledge_card_repository.get_card(tenant_code, card_id)
    if updated is None:
        raise KnowledgeCardError("知识卡不存在")

    logger.info(
        "knowledge_card_status_updated",
        tenant_code=tenant_code,
        card_id=card_id,
        status=status,
    )
    return _to_item(updated)
