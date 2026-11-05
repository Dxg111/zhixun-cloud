"""企业加入申请、审核与成员身份服务"""

from __future__ import annotations

import structlog
from pymysql.err import IntegrityError

from app.core.auth import create_employee_token
from app.core.exceptions import AuthenticationError
from app.models.employee_exam import EmployeeInfo
from app.models.employee_join import (
    EmployeeMembershipResponse,
    JoinRequestApproveRequest,
    JoinRequestCreate,
    JoinRequestItem,
    JoinRequestListResponse,
    JoinRequestRejectRequest,
)
from app.repositories import (
    admin_org_repository,
    employee_join_repository,
    settings_repository,
)
from app.services import notification_service

logger = structlog.get_logger()


class EmployeeJoinError(Exception):
    """加入企业业务异常。"""


def _to_item(row: dict) -> JoinRequestItem:
    return JoinRequestItem(**row)


def _employee_info(employee: dict) -> EmployeeInfo:
    return EmployeeInfo(
        id=employee["id"],
        tenant_code=employee["tenant_code"],
        employee_no=employee["employee_no"],
        name=employee["name"],
        org_path=employee["org_path"],
    )


async def _tenant_name(tenant_code: str) -> str:
    settings = await settings_repository.get_settings(tenant_code)
    return settings["tenant_name"] if settings else tenant_code


async def get_membership(user_id: int) -> EmployeeMembershipResponse:
    employee = await admin_org_repository.find_employee_by_user(user_id)
    if employee is not None:
        tenant_name = await _tenant_name(employee["tenant_code"])
        if employee["status"] == "active":
            return EmployeeMembershipResponse(
                status="approved",
                tenant_code=employee["tenant_code"],
                tenant_name=tenant_name,
                employee=_employee_info(employee),
                message="已加入企业",
            )
        return EmployeeMembershipResponse(
            status="disabled",
            tenant_code=employee["tenant_code"],
            tenant_name=tenant_name,
            employee=_employee_info(employee),
            message="员工账号已停用，请联系企业管理员",
        )

    latest = await employee_join_repository.get_latest_request_for_user(user_id)
    if latest is not None and latest["status"] in {"pending", "rejected"}:
        return EmployeeMembershipResponse(
            status=latest["status"],
            tenant_code=latest["tenant_code"],
            tenant_name=latest["tenant_name"],
            request=_to_item(latest),
            message="加入申请审核中" if latest["status"] == "pending" else "加入申请未通过",
        )

    return EmployeeMembershipResponse(status="none", message="尚未加入企业")


async def submit_join_request(
    user_id: int,
    req: JoinRequestCreate,
) -> JoinRequestItem:
    tenant_code = req.tenant_code.strip()
    name = req.name.strip()
    employee_no = req.employee_no.strip()
    if not tenant_code or not name or not employee_no:
        raise EmployeeJoinError("企业编码、姓名和工号不能为空")

    employee = await admin_org_repository.find_employee_by_user(user_id)
    if employee is not None:
        raise EmployeeJoinError("该微信账号已加入企业，不能重复加入")

    pending = await employee_join_repository.get_pending_request_for_user(user_id)
    if pending is not None:
        raise EmployeeJoinError("已有待审核的加入申请，请等待管理员处理")

    settings = await settings_repository.get_settings(tenant_code)
    if settings is None:
        raise EmployeeJoinError("企业编码不存在，请向企业管理员确认")

    existing = await admin_org_repository.find_employee_by_no(tenant_code, employee_no)
    if existing is not None and existing["user_id"] is not None:
        raise EmployeeJoinError("该工号已绑定其他微信账号，请联系企业管理员")

    request_id = await employee_join_repository.create_request(
        tenant_code=tenant_code,
        user_id=user_id,
        name=name,
        employee_no=employee_no,
        remark=(req.remark or "").strip() or None,
    )
    row = await employee_join_repository.get_request(tenant_code, request_id)
    if row is None:
        raise EmployeeJoinError("加入申请提交失败，请稍后重试")
    return _to_item(row)


async def list_my_requests(user_id: int) -> JoinRequestListResponse:
    latest = await employee_join_repository.get_latest_request_for_user(user_id)
    items = [_to_item(latest)] if latest else []
    return JoinRequestListResponse(items=items, total=len(items), page=1, page_size=20)


async def list_admin_requests(
    tenant_code: str,
    status: str,
    page: int,
    page_size: int,
) -> JoinRequestListResponse:
    rows, total = await employee_join_repository.list_requests(
        tenant_code=tenant_code,
        status=status,
        page=page,
        page_size=page_size,
    )
    return JoinRequestListResponse(
        items=[_to_item(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


async def approve_request(
    tenant_code: str,
    request_id: int,
    admin_name: str,
    req: JoinRequestApproveRequest,
) -> JoinRequestItem:
    account = await employee_join_repository.get_request(tenant_code, request_id)
    if account is None:
        raise EmployeeJoinError("加入申请不存在")
    if account["status"] != "pending":
        raise EmployeeJoinError("该申请已处理，不能重复审核")

    if req.org_id is not None:
        org = await admin_org_repository.get_org(tenant_code, req.org_id)
        if org is None:
            raise EmployeeJoinError("部门不存在")

    employee = await admin_org_repository.find_employee_by_user(account["user_id"])
    if employee is not None:
        raise EmployeeJoinError("该微信账号已加入企业，不能重复加入")

    existing = await admin_org_repository.find_employee_by_no(
        tenant_code, account["employee_no"]
    )
    try:
        if existing is not None:
            if existing["user_id"] is not None and existing["user_id"] != account["user_id"]:
                raise EmployeeJoinError("该工号已绑定其他微信账号")
            await admin_org_repository.update_employee_assignment(
                tenant_code=tenant_code,
                employee_id=existing["id"],
                org_id=req.org_id,
                role=req.role,
            )
            await admin_org_repository.bind_employee_user(
                tenant_code, existing["id"], account["user_id"]
            )
            if existing["status"] != "active":
                await admin_org_repository.update_employee_status(
                    tenant_code, existing["id"], "active"
                )
        else:
            await admin_org_repository.create_employee(
                tenant_code=tenant_code,
                org_id=req.org_id,
                employee_no=account["employee_no"],
                name=account["name"],
                role=req.role,
                user_id=account["user_id"],
            )
    except IntegrityError as exc:
        logger.warning("join_request_bind_conflict", request_id=request_id, error=str(exc))
        raise EmployeeJoinError("该微信账号已加入其他企业，不能重复加入") from exc

    await employee_join_repository.mark_approved(
        tenant_code=tenant_code,
        request_id=request_id,
        org_id=req.org_id,
        role=req.role,
        reviewed_by=admin_name,
    )
    updated = await employee_join_repository.get_request(tenant_code, request_id)
    if updated is None:
        raise EmployeeJoinError("审核失败，请稍后重试")
    await notification_service.notify_join_result(
        tenant_code,
        account["user_id"],
        request_id,
        approved=True,
        tenant_name=account.get("tenant_name") or "",
    )
    return _to_item(updated)


async def reject_request(
    tenant_code: str,
    request_id: int,
    admin_name: str,
    req: JoinRequestRejectRequest,
) -> JoinRequestItem:
    account = await employee_join_repository.get_request(tenant_code, request_id)
    if account is None:
        raise EmployeeJoinError("加入申请不存在")
    if account["status"] != "pending":
        raise EmployeeJoinError("该申请已处理，不能重复审核")

    await employee_join_repository.mark_rejected(
        tenant_code=tenant_code,
        request_id=request_id,
        reason=req.reason.strip(),
        reviewed_by=admin_name,
    )
    updated = await employee_join_repository.get_request(tenant_code, request_id)
    if updated is None:
        raise EmployeeJoinError("审核失败，请稍后重试")
    await notification_service.notify_join_result(
        tenant_code,
        account["user_id"],
        request_id,
        approved=False,
        reject_reason=req.reason.strip(),
    )
    return _to_item(updated)


async def login_by_user(user_id: int) -> tuple[str, EmployeeInfo]:
    employee = await admin_org_repository.find_employee_by_user(user_id)
    if employee is None:
        raise AuthenticationError("尚未加入企业，请先提交加入申请")
    if employee["status"] != "active":
        raise AuthenticationError("员工账号已停用，请联系企业管理员")

    token = create_employee_token(
        employee_id=employee["id"],
        tenant_code=employee["tenant_code"],
        display_name=employee["name"],
        employee_no=employee["employee_no"],
    )
    return token, _employee_info(employee)
