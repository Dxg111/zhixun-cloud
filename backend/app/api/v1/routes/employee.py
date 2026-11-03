"""员工登录、答题与学习路由"""

from fastapi import APIRouter, Depends, Query

from app.core.auth import get_employee_context
from app.models.common import ApiResponse
from app.models.employee_exam import EmployeeAnswersRequest, EmployeeLoginRequest
from app.models.employee_learning import (
    EmployeeWrongMasterRequest,
    EmployeeWrongRetryRequest,
)
from app.services import employee_exam_service, employee_learning_service

router = APIRouter(prefix="/employee", tags=["employee"])


@router.post("/login", response_model=ApiResponse)
async def employee_login(req: EmployeeLoginRequest):
    result = await employee_exam_service.login(req.tenant_code, req.invite_code)
    return ApiResponse.success(data=result.model_dump())


@router.get("/exams", response_model=ApiResponse)
async def list_employee_exams(context: dict = Depends(get_employee_context)):
    result = await employee_exam_service.list_exams(
        context["tenant_code"], context["employee_id"]
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/exams/{exam_id}/start", response_model=ApiResponse)
async def start_employee_exam(
    exam_id: int,
    context: dict = Depends(get_employee_context),
):
    result = await employee_exam_service.start_exam(
        context["tenant_code"], context["employee_id"], exam_id
    )
    return ApiResponse.success(data=result.model_dump())


@router.put("/attempts/{attempt_id}/answers", response_model=ApiResponse)
async def save_employee_answers(
    attempt_id: int,
    req: EmployeeAnswersRequest,
    context: dict = Depends(get_employee_context),
):
    await employee_exam_service.save_answers(
        context["tenant_code"],
        context["employee_id"],
        attempt_id,
        req.answers,
    )
    return ApiResponse.success()


@router.post("/attempts/{attempt_id}/submit", response_model=ApiResponse)
async def submit_employee_exam(
    attempt_id: int,
    req: EmployeeAnswersRequest,
    context: dict = Depends(get_employee_context),
):
    result = await employee_exam_service.submit_exam(
        context["tenant_code"],
        context["employee_id"],
        attempt_id,
        req.answers,
    )
    return ApiResponse.success(data=result.model_dump())


@router.get("/attempts/{attempt_id}/result", response_model=ApiResponse)
async def get_employee_result(
    attempt_id: int,
    context: dict = Depends(get_employee_context),
):
    result = await employee_exam_service.get_result(
        context["tenant_code"], context["employee_id"], attempt_id
    )
    return ApiResponse.success(data=result.model_dump())


# ---- 考前知识卡 ----


@router.get("/exams/{exam_id}/cards", response_model=ApiResponse)
async def list_exam_cards(
    exam_id: int,
    context: dict = Depends(get_employee_context),
):
    result = await employee_learning_service.list_exam_cards(
        context["tenant_code"], context["employee_id"], exam_id
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/cards/{card_id}/view", response_model=ApiResponse)
async def record_card_view(
    card_id: int,
    context: dict = Depends(get_employee_context),
):
    await employee_learning_service.record_card_view(
        context["tenant_code"], context["employee_id"], card_id
    )
    return ApiResponse.success()


# ---- 错题重练 ----


@router.get("/wrong-questions", response_model=ApiResponse)
async def list_wrong_questions(
    mastered: bool | None = Query(None),
    context: dict = Depends(get_employee_context),
):
    result = await employee_learning_service.list_wrong_questions(
        context["tenant_code"], context["employee_id"], mastered
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/wrong-questions/{wrong_id}/retry", response_model=ApiResponse)
async def retry_wrong_question(
    wrong_id: int,
    req: EmployeeWrongRetryRequest,
    context: dict = Depends(get_employee_context),
):
    result = await employee_learning_service.retry_wrong_question(
        context["tenant_code"],
        context["employee_id"],
        wrong_id,
        req.selected,
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/wrong-questions/{wrong_id}/master", response_model=ApiResponse)
async def set_wrong_question_mastered(
    wrong_id: int,
    req: EmployeeWrongMasterRequest,
    context: dict = Depends(get_employee_context),
):
    mastered = await employee_learning_service.set_wrong_question_mastered(
        context["tenant_code"],
        context["employee_id"],
        wrong_id,
        req.mastered,
    )
    return ApiResponse.success(data={"mastered": mastered})
