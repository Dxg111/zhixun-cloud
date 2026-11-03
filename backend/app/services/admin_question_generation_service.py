"""从管理后台上传文档生成题目"""

from __future__ import annotations

import asyncio
import os

import structlog

from app.core.exceptions import QuestionError
from app.llm.quiz_chain import generate_quiz
from app.models.question_bank import (
    GenerateQuestionsRequest,
    GenerateQuestionsResponse,
)
from app.repositories import admin_document_repository, question_repository
from app.services import document_loader_service

logger = structlog.get_logger()


async def generate_from_document(
    tenant_code: str,
    doc_id: int,
    req: GenerateQuestionsRequest,
) -> GenerateQuestionsResponse:
    doc = await admin_document_repository.get_document(tenant_code, doc_id)
    if doc is None:
        raise QuestionError("文档不存在")
    if doc["status"] != "ready":
        raise QuestionError("文档尚未解析完成")

    file_path = doc.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise QuestionError("文档文件不存在，请重新上传")

    try:
        chunks = await asyncio.to_thread(
            document_loader_service.load_and_split,
            file_path,
            doc["file_type"],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("question_generation_load_failed", doc_id=doc_id, error=str(exc))
        raise QuestionError("文档内容读取失败") from exc

    content = "\n\n".join(chunk.page_content for chunk in chunks)[:12000]
    if not content.strip():
        raise QuestionError("文档内容为空")

    try:
        quiz = await generate_quiz(
            user_input=f"请基于文档《{doc['file_name']}》生成一组培训闯关题，覆盖文档中的关键知识点。",
            question_count=req.question_count,
            difficulty=req.difficulty,
            search_context=content,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("question_generation_llm_failed", doc_id=doc_id, error=str(exc))
        raise QuestionError(f"AI 出题失败：{exc}") from exc

    if not quiz.questions:
        raise QuestionError("AI 未生成有效题目")

    bank = await question_repository.get_or_create_bank(
        tenant_code=tenant_code,
        name=req.bank_name,
        description=f"AI 从《{doc['file_name']}》生成",
    )
    created = await question_repository.create_questions(
        tenant_code=tenant_code,
        bank_id=bank["id"],
        questions=[question.model_dump() for question in quiz.questions],
        source_ref=doc["file_name"],
        ai_meta="deepseek-chat · 文档生成",
    )

    logger.info(
        "questions_generated_from_document",
        tenant_code=tenant_code,
        doc_id=doc_id,
        bank_id=bank["id"],
        created=created,
    )
    return GenerateQuestionsResponse(
        created=created,
        bank_id=bank["id"],
        bank_name=bank["name"],
    )
