"""管理后台文档路由"""

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.auth import get_admin_context
from app.models.common import ApiResponse
from app.models.question_bank import GenerateQuestionsRequest
from app.services import (
    admin_document_service,
    admin_question_generation_service,
    audit_service,
)

router = APIRouter(prefix="/admin/documents", tags=["admin"])


@router.get("", response_model=ApiResponse)
async def list_documents(context: dict = Depends(get_admin_context)):
    result = await admin_document_service.list_documents(context["tenant_code"])
    return ApiResponse.success(data=result.model_dump())


@router.post("", response_model=ApiResponse)
async def upload_document(
    file: UploadFile = File(...),
    context: dict = Depends(get_admin_context),
):
    content = await file.read()
    result = await admin_document_service.upload_document(
        tenant_code=context["tenant_code"],
        filename=file.filename or "document.txt",
        content=content,
        created_by=context.get("login_name", ""),
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "document.upload",
        target_type="document",
        target_id=result.id,
        detail={"file_name": result.file_name},
    )
    return ApiResponse.success(data=result.model_dump())


@router.delete("/{doc_id}", response_model=ApiResponse)
async def delete_document(doc_id: int, context: dict = Depends(get_admin_context)):
    await admin_document_service.delete_document(context["tenant_code"], doc_id)
    await audit_service.record(
        context["tenant_code"],
        context,
        "document.delete",
        target_type="document",
        target_id=doc_id,
    )
    return ApiResponse.success()


@router.post("/{doc_id}/generate-questions", response_model=ApiResponse)
async def generate_questions_from_document(
    doc_id: int,
    req: GenerateQuestionsRequest,
    context: dict = Depends(get_admin_context),
):
    result = await admin_question_generation_service.generate_from_document(
        tenant_code=context["tenant_code"],
        doc_id=doc_id,
        req=req,
    )
    return ApiResponse.success(data=result.model_dump())
