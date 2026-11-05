"""微信订阅消息

一次性订阅：用户每次授权只增加一次发送额度，发送成功后扣减。
模板字段需与小程序后台申请的模板一致；若模板字段不同，调整 TEMPLATE_BUILDERS。
所有失败都静默降级为站内通知，不影响业务主流程。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
import structlog

from app.core.config import get_settings
from app.repositories import wechat_subscription_repository

logger = structlog.get_logger()

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send"

_token_cache: dict[str, Any] = {"token": "", "expires_at": 0.0}
_token_lock = asyncio.Lock()


def _clip(value: Any, length: int = 20) -> str:
    text = str(value or "").strip().replace("\n", " ")
    return text if len(text) <= length else f"{text[: length - 1]}…"


def _date_text(value: Any) -> str:
    text = str(value or "").strip()
    # 微信 date 类型要求 yyyy-MM-dd 或 yyyy年MM月dd日
    return text[:10] if len(text) >= 10 else "未设置"


def get_template_map() -> dict[str, str]:
    settings = get_settings()
    return {
        key: value
        for key, value in {
            "exam_assigned": settings.wechat_subscribe_exam_assigned,
            "result_ready": settings.wechat_subscribe_result_ready,
            "exam_deadline": settings.wechat_subscribe_deadline,
        }.items()
        if value
    }


def build_template_payload(
    notice_type: str, data: dict | None
) -> tuple[str, dict] | None:
    """按通知类型生成 (template_id, data)。字段名按常见模板约定，可按实际模板调整。"""
    templates = get_template_map()
    template_id = templates.get(notice_type)
    if not template_id:
        return None

    ctx = data or {}
    if notice_type == "exam_assigned":
        return template_id, {
            "thing1": {"value": _clip(ctx.get("title", "新考试"))},
            "date2": {"value": _date_text(ctx.get("end_at"))},
            "thing3": {"value": "请进入企业培训完成考试"},
        }
    if notice_type == "result_ready":
        return template_id, {
            "thing1": {"value": _clip(ctx.get("title", "考试成绩"))},
            "number2": {"value": str(ctx.get("score", 0))},
            "thing3": {"value": "已通过" if ctx.get("passed") else "未通过"},
        }
    if notice_type == "exam_deadline":
        return template_id, {
            "thing1": {"value": _clip(ctx.get("title", "考试提醒"))},
            "date2": {"value": _date_text(ctx.get("end_at"))},
            "thing3": {"value": "请尽快完成考试"},
        }
    return None


async def _get_access_token() -> str:
    settings = get_settings()
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        return ""

    now = time.time()
    if _token_cache["token"] and _token_cache["expires_at"] > now:
        return _token_cache["token"]

    async with _token_lock:
        if _token_cache["token"] and _token_cache["expires_at"] > now:
            return _token_cache["token"]
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    TOKEN_URL,
                    params={
                        "grant_type": "client_credential",
                        "appid": settings.wechat_app_id,
                        "secret": settings.wechat_app_secret,
                    },
                )
                body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("wechat_token_failed", error=str(exc))
            return ""

        token = body.get("access_token")
        if not token:
            logger.warning(
                "wechat_token_rejected",
                errcode=body.get("errcode"),
                errmsg=body.get("errmsg"),
            )
            return ""

        _token_cache["token"] = token
        _token_cache["expires_at"] = now + max(int(body.get("expires_in", 7200)) - 300, 60)
        return token


async def send_message(openid: str, template_id: str, data: dict, page: str) -> bool:
    token = await _get_access_token()
    if not token:
        return False

    payload = {
        "touser": openid,
        "template_id": template_id,
        "page": page.lstrip("/"),
        "data": data,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                SEND_URL, params={"access_token": token}, json=payload
            )
            body = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("wechat_send_failed", template_id=template_id, error=str(exc))
        return False

    if body.get("errcode") == 0:
        return True

    # token 失效时清缓存，下次重新获取
    if body.get("errcode") in (40001, 42001):
        _token_cache["token"] = ""
        _token_cache["expires_at"] = 0.0

    logger.info(
        "wechat_send_rejected",
        template_id=template_id,
        errcode=body.get("errcode"),
        errmsg=body.get("errmsg"),
    )
    return False


async def send_for_employee(
    employee_id: int, notice_type: str, data: dict | None
) -> bool:
    """尝试给员工发送订阅消息；未授权、无额度或发送失败返回 False。"""
    settings = get_settings()
    if not settings.enable_wechat_subscribe:
        return False

    payload = build_template_payload(notice_type, data)
    if payload is None:
        return False
    template_id, template_data = payload

    contact = await wechat_subscription_repository.find_employee_contact(employee_id)
    if contact is None or not contact.get("openid"):
        return False

    quota = await wechat_subscription_repository.get_quota(contact["user_id"])
    if quota.get(template_id, 0) <= 0:
        return False

    page = PAGE_BY_TYPE.get(notice_type, "pages/employee-exams/index")
    sent = await send_message(
        contact["openid"], template_id, template_data, page
    )
    if sent:
        await wechat_subscription_repository.consume(
            contact["user_id"], template_id
        )
    return sent


PAGE_BY_TYPE = {
    "exam_assigned": "pages/employee-exams/index",
    "result_ready": "pages/employee-result/index",
    "exam_deadline": "pages/employee-exams/index",
}


async def record_subscriptions(user_id: int, template_ids: list[str]) -> int:
    """记录用户授权。只接受当前已配置的模板，返回记录成功的模板数。"""
    allowed = set(get_template_map().values())
    accepted = {item for item in template_ids if item in allowed}
    for template_id in accepted:
        await wechat_subscription_repository.add_quota(user_id, template_id, 1)
    return len(accepted)
