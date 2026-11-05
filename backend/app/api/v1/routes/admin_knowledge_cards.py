"""知识卡管理路由"""

from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_admin_context
from app.models.common import ApiResponse
from app.models.knowledge_card import (
    KnowledgeCardGenerateRequest,
    KnowledgeCardStatusRequest,
    KnowledgeCardUpdateRequest,
)
from app.services import audit_service, knowledge_card_service

router = APIRouter(prefix="/admin/knowledge-cards", tags=["admin"])


@router.get("", response_model=ApiResponse)
async def list_knowledge_cards(
    status: Literal["all", "draft", "published", "offline"] = Query("all"),
    keyword: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    context: dict = Depends(get_admin_context),
):
    result = await knowledge_card_service.list_cards(
        tenant_code=context["tenant_code"],
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/generate", response_model=ApiResponse)
async def generate_knowledge_cards(
    req: KnowledgeCardGenerateRequest,
    context: dict = Depends(get_admin_context),
):
    result = await knowledge_card_service.generate_cards(
        tenant_code=context["tenant_code"],
        req=req,
        created_by=context.get("login_name", ""),
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "card.generate",
        target_type="knowledge_card",
        detail={"doc_id": req.doc_id, "card_count": getattr(result, "created", None)},
    )
    return ApiResponse.success(data=result.model_dump())


@router.get("/{card_id}", response_model=ApiResponse)
async def get_knowledge_card(
    card_id: int,
    context: dict = Depends(get_admin_context),
):
    result = await knowledge_card_service.get_card_detail(
        context["tenant_code"], card_id
    )
    return ApiResponse.success(data=result.model_dump())


@router.put("/{card_id}", response_model=ApiResponse)
async def update_knowledge_card(
    card_id: int,
    req: KnowledgeCardUpdateRequest,
    context: dict = Depends(get_admin_context),
):
    result = await knowledge_card_service.update_card(
        context["tenant_code"], card_id, req
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "card.update",
        target_type="knowledge_card",
        target_id=card_id,
        detail={"title": result.title},
    )
    return ApiResponse.success(data=result.model_dump())


@router.put("/{card_id}/status", response_model=ApiResponse)
async def update_knowledge_card_status(
    card_id: int,
    req: KnowledgeCardStatusRequest,
    context: dict = Depends(get_admin_context),
):
    result = await knowledge_card_service.update_card_status(
        tenant_code=context["tenant_code"],
        card_id=card_id,
        status=req.status,
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "card.status",
        target_type="knowledge_card",
        target_id=card_id,
        detail={"status": req.status, "title": result.title},
    )
    return ApiResponse.success(data=result.model_dump())
