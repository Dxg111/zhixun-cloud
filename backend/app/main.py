"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.routes import (
    admin_accounts,
    admin_documents,
    admin_exams,
    admin_join_requests,
    admin_knowledge_cards,
    admin_org,
    admin_questions,
    admin_search,
    admin_settings,
    auth,
    employee,
    employee_notifications,
    health,
    knowledge,
    quiz,
    report,
    user,
)
from app.core.config import get_settings
from app.core.db import close_mysql_pool, init_mysql
from app.core.exceptions import (
    AdminExamError,
    AdminOrgError,
    AdminUserError,
    AuthenticationError,
    ContentFilterError,
    KnowledgeBaseError,
    KnowledgeCardError,
    QuestionError,
    QuizGenerationError,
    ReportGenerationError,
)
from app.models.common import ApiResponse
from app.services.employee_join_service import EmployeeJoinError

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("app_starting", host=settings.app_host, port=settings.app_port)
    if settings.mysql_auto_init:
        await init_mysql()
    yield
    await close_mysql_pool()
    logger.info("app_shutting_down")



app = FastAPI(
    title="智训云",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 用户头像静态目录
_avatar_dir = Path(get_settings().avatar_upload_dir).resolve()
_avatar_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media/avatars", StaticFiles(directory=str(_avatar_dir)), name="avatars")

# 注册路由
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(admin_accounts.router, prefix="/api/v1")
app.include_router(admin_questions.router, prefix="/api/v1")
app.include_router(admin_search.router, prefix="/api/v1")
app.include_router(admin_knowledge_cards.router, prefix="/api/v1")
app.include_router(admin_org.router, prefix="/api/v1")
app.include_router(admin_documents.router, prefix="/api/v1")
app.include_router(admin_settings.router, prefix="/api/v1")
app.include_router(admin_exams.router, prefix="/api/v1")
app.include_router(admin_join_requests.router, prefix="/api/v1")
app.include_router(employee.router, prefix="/api/v1")
app.include_router(employee_notifications.router, prefix="/api/v1")
app.include_router(quiz.router, prefix="/api/v1")
app.include_router(report.router, prefix="/api/v1")
app.include_router(user.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")


# 全局异常处理
@app.exception_handler(AuthenticationError)
async def auth_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content=ApiResponse.error(code=4010, message=str(exc)).model_dump(),
    )


@app.exception_handler(ContentFilterError)
async def content_filter_handler(request: Request, exc: ContentFilterError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4000, message=str(exc)).model_dump(),
    )


@app.exception_handler(QuizGenerationError)
async def quiz_error_handler(request: Request, exc: QuizGenerationError):
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5001, message=str(exc)).model_dump(),
    )


@app.exception_handler(ReportGenerationError)
async def report_error_handler(request: Request, exc: ReportGenerationError):
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5002, message=str(exc)).model_dump(),
    )


@app.exception_handler(KnowledgeBaseError)
async def knowledge_base_error_handler(request: Request, exc: KnowledgeBaseError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4001, message=str(exc)).model_dump(),
    )


@app.exception_handler(AdminUserError)
async def admin_user_error_handler(request: Request, exc: AdminUserError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4002, message=str(exc)).model_dump(),
    )


@app.exception_handler(QuestionError)
async def question_error_handler(request: Request, exc: QuestionError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4003, message=str(exc)).model_dump(),
    )


@app.exception_handler(KnowledgeCardError)
async def knowledge_card_error_handler(request: Request, exc: KnowledgeCardError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4004, message=str(exc)).model_dump(),
    )


@app.exception_handler(AdminOrgError)
async def admin_org_error_handler(request: Request, exc: AdminOrgError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4005, message=str(exc)).model_dump(),
    )


@app.exception_handler(AdminExamError)
async def admin_exam_error_handler(request: Request, exc: AdminExamError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4006, message=str(exc)).model_dump(),
    )


@app.exception_handler(EmployeeJoinError)
async def employee_join_error_handler(request: Request, exc: EmployeeJoinError):
    return JSONResponse(
        status_code=400,
        content=ApiResponse.error(code=4007, message=str(exc)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """兜底异常处理：避免直接暴露裸的 "Internal Server Error"，并记录完整堆栈便于排查。"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content=ApiResponse.error(code=5000, message="服务器内部错误，请稍后重试").model_dump(),
    )


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
