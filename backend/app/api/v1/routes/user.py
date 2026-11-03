"""用户路由"""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.models.common import ApiResponse
from app.models.user import LoginRequest, UpdateProfileRequest
from app.repositories import user_repository
from app.services import user_service, history_service

router = APIRouter(prefix="/user", tags=["user"])

AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_AVATAR_BYTES = 2 * 1024 * 1024


@router.post("/login", response_model=ApiResponse)
async def login(req: LoginRequest):
    result = await user_service.handle_login(req.code)
    return ApiResponse.success(data=result.model_dump())


@router.get("/profile", response_model=ApiResponse)
async def get_profile(user_id: int = Depends(get_current_user)):
    result = await user_service.get_profile(user_id)
    return ApiResponse.success(data=result.model_dump())


@router.put("/profile", response_model=ApiResponse)
async def update_profile(
    req: UpdateProfileRequest,
    user_id: int = Depends(get_current_user),
):
    await user_service.update_profile(user_id, req.nickname, req.avatar_url)
    return ApiResponse.success()


@router.post("/avatar", response_model=ApiResponse)
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user),
):
    """接收小程序选择的临时头像文件，持久化后返回可访问地址。"""
    content_type = (file.content_type or "").lower()
    ext = AVATAR_CONTENT_TYPES.get(content_type)
    if ext is None:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            ext = ".jpg" if suffix == ".jpeg" else suffix
    if ext is None:
        return ApiResponse.error(code=4000, message="仅支持 JPG、PNG 或 WebP 图片")

    content = await file.read()
    if not content:
        return ApiResponse.error(code=4000, message="图片内容为空")
    if len(content) > MAX_AVATAR_BYTES:
        return ApiResponse.error(code=4000, message="头像不能超过 2MB")

    avatar_dir = Path(get_settings().avatar_upload_dir).resolve()
    avatar_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{user_id}_{uuid4().hex}{ext}"
    (avatar_dir / filename).write_bytes(content)

    base_url = str(request.base_url).rstrip("/")
    avatar_url = f"{base_url}/media/avatars/{filename}"
    await user_repository.update_user_profile(user_id, None, avatar_url)
    return ApiResponse.success(data={"avatar_url": avatar_url})


@router.get("/quizzes", response_model=ApiResponse)
async def get_quiz_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    user_id: int = Depends(get_current_user),
):
    result = await history_service.get_quiz_history(user_id, page, page_size)
    return ApiResponse.success(data=result.model_dump())


@router.get("/quizzes/{quiz_id}", response_model=ApiResponse)
async def get_quiz_detail(
    quiz_id: str,
    user_id: int = Depends(get_current_user),
):
    result = await history_service.get_quiz_detail(quiz_id, user_id)
    if result is None:
        return ApiResponse.error(code=4004, message="闯关记录不存在")
    return ApiResponse.success(data=result.model_dump())
