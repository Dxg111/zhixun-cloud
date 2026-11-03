"""知识卡服务测试"""

import pytest
from langchain_core.documents import Document

from app.core.exceptions import KnowledgeCardError
from app.llm import knowledge_card_chain
from app.models.knowledge_card import (
    KnowledgeCardBatchOutput,
    KnowledgeCardDraft,
    KnowledgeCardGenerateRequest,
    KnowledgeCardPoint,
)
from app.repositories import admin_document_repository, knowledge_card_repository
from app.services import document_loader_service, knowledge_card_service


def _card(card_id: int = 1, status: str = "draft") -> dict:
    return {
        "id": card_id,
        "tenant_code": "demo",
        "doc_id": 1,
        "doc_name": "食品安全操作规范.docx",
        "title": "冷藏温度三原则",
        "excerpt": "0–4℃ 冷藏、每 4 小时记录、异常立即上报。",
        "source": "食品安全操作规范 P12",
        "status": status,
        "view_rate": 72,
        "created_by": "admin",
        "published_at": None,
        "created_at": "2026-11-02 20:56:00",
        "updated_at": "2026-11-02 20:56:00",
        "content_json": {"points": [{"heading": "冷藏", "body": "0–4℃"}]},
    }


def _document() -> dict:
    return {
        "id": 1,
        "tenant_code": "demo",
        "file_name": "食品安全操作规范.txt",
        "file_type": "txt",
        "status": "ready",
        "file_path": "C:/tmp/food.txt",
    }


def _batch() -> KnowledgeCardBatchOutput:
    return KnowledgeCardBatchOutput(
        cards=[
            KnowledgeCardDraft(
                title=f"知识卡 {index}",
                points=[KnowledgeCardPoint(heading="要点", body="正文内容")],
                source_ref="食品安全操作规范 · 第 1 段",
            )
            for index in range(1, 4)
        ]
    )


@pytest.mark.asyncio
async def test_list_cards(monkeypatch):
    async def fake_list(tenant_code: str, status: str, keyword: str, page: int, page_size: int):
        return [_card()], 1

    monkeypatch.setattr(knowledge_card_repository, "list_cards", fake_list)

    result = await knowledge_card_service.list_cards("demo", "all", "", 1, 50)

    assert result.total == 1
    assert result.items[0].title == "冷藏温度三原则"


@pytest.mark.asyncio
async def test_generate_cards(monkeypatch, tmp_path):
    counter = {"id": 0}
    file_path = tmp_path / "food.txt"
    file_path.write_text("食品安全培训资料", encoding="utf-8")

    async def fake_document(tenant_code: str, doc_id: int):
        doc = _document()
        doc["file_path"] = str(file_path)
        return doc

    def fake_load(file_path: str, file_type: str):
        return [Document(page_content="食品安全培训资料：冷藏食品应保持在 0–4 摄氏度。")]

    async def fake_generate(content: str, card_count: int, style: str):
        return _batch()

    async def fake_create(
        tenant_code: str,
        doc_name: str,
        title: str,
        excerpt: str,
        source: str,
        status: str,
        view_rate: int,
        created_by,
        doc_id=None,
        content_json=None,
    ):
        counter["id"] += 1
        return counter["id"]

    async def fake_get(tenant_code: str, card_id: int):
        return _card(card_id)

    monkeypatch.setattr(admin_document_repository, "get_document", fake_document)
    monkeypatch.setattr(document_loader_service, "load_and_split", fake_load)
    monkeypatch.setattr(knowledge_card_chain, "generate_knowledge_cards", fake_generate)
    monkeypatch.setattr(knowledge_card_repository, "create_card", fake_create)
    monkeypatch.setattr(knowledge_card_repository, "get_card", fake_get)

    result = await knowledge_card_service.generate_cards(
        "demo",
        KnowledgeCardGenerateRequest(
            doc_id=1, doc_name="食品安全操作规范.txt", count=3, style="操作要点"
        ),
        "admin",
    )

    assert result.total == 3
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_generate_cards_requires_document(monkeypatch):
    async def fake_document(tenant_code: str, doc_id: int):
        return None

    monkeypatch.setattr(admin_document_repository, "get_document", fake_document)

    with pytest.raises(KnowledgeCardError, match="文档不存在"):
        await knowledge_card_service.generate_cards(
            "demo",
            KnowledgeCardGenerateRequest(doc_id=999, count=3),
            "admin",
        )


@pytest.mark.asyncio
async def test_generate_cards_requires_doc_id():
    with pytest.raises(KnowledgeCardError, match="请选择来源文档"):
        await knowledge_card_service.generate_cards(
            "demo",
            KnowledgeCardGenerateRequest(count=3),
            "admin",
        )


@pytest.mark.asyncio
async def test_publish_card(monkeypatch):
    state = {"status": "draft"}

    async def fake_get(tenant_code: str, card_id: int):
        return _card(card_id, state["status"])

    async def fake_update(tenant_code: str, card_id: int, status: str):
        state["status"] = status
        return 1

    monkeypatch.setattr(knowledge_card_repository, "get_card", fake_get)
    monkeypatch.setattr(knowledge_card_repository, "update_status", fake_update)

    result = await knowledge_card_service.update_card_status("demo", 1, "published")

    assert result.status == "published"


@pytest.mark.asyncio
async def test_update_missing_card(monkeypatch):
    async def fake_get(tenant_code: str, card_id: int):
        return None

    monkeypatch.setattr(knowledge_card_repository, "get_card", fake_get)

    with pytest.raises(KnowledgeCardError, match="不存在"):
        await knowledge_card_service.update_card_status("demo", 999, "published")
