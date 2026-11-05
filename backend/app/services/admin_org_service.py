"""组织与员工服务"""

from __future__ import annotations

import csv
import io

import structlog

from app.core.exceptions import AdminOrgError
from app.models.admin_org import (
    EmployeeCreateRequest,
    EmployeeImportResponse,
    EmployeeItem,
    EmployeeListResponse,
    OrgUnitCreateRequest,
    OrgUnitItem,
    OrgUnitListResponse,
    OrgUnitUpdateRequest,
)
from app.repositories import admin_org_repository

logger = structlog.get_logger()

EXPECTED_HEADERS = ["工号", "姓名", "部门路径", "角色"]


def _to_org_item(org: dict) -> OrgUnitItem:
    return OrgUnitItem(**org)


def _to_employee_item(employee: dict) -> EmployeeItem:
    return EmployeeItem(**employee)


async def _ensure_org_path(tenant_code: str, dept_path: str) -> int | None:
    parts = [part.strip() for part in dept_path.replace("\\", "/").split("/") if part.strip()]
    parent_id: int | None = None
    current_path = ""

    for part in parts:
        current_path = f"{current_path}/{part}" if current_path else part
        org = await admin_org_repository.find_org_by_path(tenant_code, current_path)
        if org is None:
            org_id = await admin_org_repository.create_org(
                tenant_code=tenant_code,
                parent_id=parent_id,
                name=part,
                path=current_path,
            )
            parent_id = org_id
        else:
            parent_id = org["id"]

    return parent_id


async def list_org_units(tenant_code: str) -> OrgUnitListResponse:
    rows = await admin_org_repository.list_org_units(tenant_code)
    return OrgUnitListResponse(items=[_to_org_item(row) for row in rows])


async def create_org_unit(tenant_code: str, req: OrgUnitCreateRequest) -> OrgUnitItem:
    name = req.name.strip()
    if not name:
        raise AdminOrgError("部门名称不能为空")

    if req.parent_id is not None:
        parent = await admin_org_repository.get_org(tenant_code, req.parent_id)
        if parent is None:
            raise AdminOrgError("上级部门不存在")
        path = f"{parent['path']}/{name}"
    else:
        path = name

    existing = await admin_org_repository.find_org_by_path(tenant_code, path)
    if existing is not None:
        raise AdminOrgError("部门已存在")

    org_id = await admin_org_repository.create_org(
        tenant_code=tenant_code,
        parent_id=req.parent_id,
        name=name,
        path=path,
    )
    org = await admin_org_repository.get_org(tenant_code, org_id)
    if org is None:
        raise AdminOrgError("创建部门失败")
    return _to_org_item(org)


async def update_org_unit(
    tenant_code: str, org_id: int, req: OrgUnitUpdateRequest
) -> OrgUnitItem:
    org = await admin_org_repository.get_org(tenant_code, org_id)
    if org is None:
        raise AdminOrgError("部门不存在")

    name = req.name.strip()
    if not name:
        raise AdminOrgError("部门名称不能为空")

    parent_path = ""
    if req.parent_id is not None:
        if req.parent_id == org_id:
            raise AdminOrgError("不能把部门设置为自己的上级")
        parent = await admin_org_repository.get_org(tenant_code, req.parent_id)
        if parent is None:
            raise AdminOrgError("上级部门不存在")
        if parent["path"] == org["path"] or parent["path"].startswith(
            f"{org['path']}/"
        ):
            raise AdminOrgError("不能移动到自己的下级部门")
        parent_path = parent["path"]

    old_path = org["path"]
    new_path = f"{parent_path}/{name}" if parent_path else name
    if new_path != old_path:
        existing = await admin_org_repository.find_org_by_path(tenant_code, new_path)
        if existing is not None and existing["id"] != org_id:
            raise AdminOrgError("同级下已存在同名部门")

    updated = await admin_org_repository.update_org(
        tenant_code=tenant_code,
        org_id=org_id,
        name=name,
        parent_id=req.parent_id,
        path=new_path,
    )
    if updated == 0:
        raise AdminOrgError("部门不存在")

    if new_path != old_path:
        await admin_org_repository.rewrite_descendant_paths(
            tenant_code, old_path, new_path
        )

    refreshed = await admin_org_repository.get_org(tenant_code, org_id)
    if refreshed is None:
        raise AdminOrgError("更新部门失败")
    return _to_org_item(refreshed)


async def delete_org_unit(tenant_code: str, org_id: int) -> None:
    org = await admin_org_repository.get_org(tenant_code, org_id)
    if org is None:
        raise AdminOrgError("部门不存在")

    children = await admin_org_repository.count_org_children(tenant_code, org_id)
    if children > 0:
        raise AdminOrgError("请先删除或转移下级部门")

    employees = await admin_org_repository.count_org_employees(tenant_code, org_id)
    if employees > 0:
        raise AdminOrgError("请先把该部门员工转移到其他部门")

    await admin_org_repository.delete_org(tenant_code, org_id)


async def list_employees(
    tenant_code: str,
    org_id: int | None,
    keyword: str,
    page: int,
    page_size: int,
) -> EmployeeListResponse:
    items, total = await admin_org_repository.list_employees(
        tenant_code=tenant_code,
        org_id=org_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return EmployeeListResponse(
        items=[_to_employee_item(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


async def create_employee(
    tenant_code: str,
    req: EmployeeCreateRequest,
) -> EmployeeItem:
    employee_no = req.employee_no.strip()
    name = req.name.strip()
    role = req.role.strip() or "员工"
    if not employee_no or not name:
        raise AdminOrgError("工号和姓名不能为空")

    existing = await admin_org_repository.find_employee_by_no(tenant_code, employee_no)
    if existing is not None:
        raise AdminOrgError(f"工号 {employee_no} 已存在")

    if req.org_id is not None:
        org = await admin_org_repository.get_org(tenant_code, req.org_id)
        if org is None:
            raise AdminOrgError("部门不存在")

    employee_id = await admin_org_repository.create_employee(
        tenant_code=tenant_code,
        org_id=req.org_id,
        employee_no=employee_no,
        name=name,
        role=role,
    )
    employee = await admin_org_repository.get_employee(tenant_code, employee_id)
    if employee is None:
        raise AdminOrgError("创建员工失败")
    return _to_employee_item(employee)


def _read_import_rows(filename: str, content: bytes) -> list[dict]:
    lower = filename.lower()
    if lower.endswith(".csv"):
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
    elif lower.endswith(".xlsx"):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise AdminOrgError("服务端缺少 openpyxl，无法解析 Excel") from exc

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.active
        values = list(sheet.iter_rows(values_only=True))
        if not values:
            return []
        headers = [str(cell).strip() if cell is not None else "" for cell in values[0]]
        rows = [
            {headers[index]: row[index] if index < len(row) else None for index in range(len(headers))}
            for row in values[1:]
        ]
    else:
        raise AdminOrgError("仅支持 .xlsx 或 .csv 文件")

    normalized: list[dict] = []
    for row in rows:
        if not any(value not in (None, "") for value in row.values()):
            continue
        normalized.append(
            {
                "employee_no": str(row.get("工号") or "").strip(),
                "name": str(row.get("姓名") or "").strip(),
                "dept_path": str(row.get("部门路径") or "").strip(),
                "role": str(row.get("角色") or "员工").strip() or "员工",
            }
        )
    return normalized


async def import_employees(
    tenant_code: str,
    filename: str,
    content: bytes,
) -> EmployeeImportResponse:
    if len(content) > 10 * 1024 * 1024:
        raise AdminOrgError("导入文件不能超过 10MB")

    rows = _read_import_rows(filename, content)
    imported = 0
    skipped = 0
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        if not row["employee_no"] or not row["name"] or not row["dept_path"]:
            skipped += 1
            errors.append(f"第 {index} 行：工号、姓名、部门路径不能为空")
            continue

        existing = await admin_org_repository.find_employee_by_no(tenant_code, row["employee_no"])
        if existing is not None:
            skipped += 1
            errors.append(f"第 {index} 行：工号 {row['employee_no']} 已存在")
            continue

        try:
            org_id = await _ensure_org_path(tenant_code, row["dept_path"])
            await admin_org_repository.create_employee(
                tenant_code=tenant_code,
                org_id=org_id,
                employee_no=row["employee_no"],
                name=row["name"],
                role=row["role"],
            )
            imported += 1
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            errors.append(f"第 {index} 行：{exc}")

    logger.info(
        "employees_imported",
        tenant_code=tenant_code,
        imported=imported,
        skipped=skipped,
        total=len(rows),
    )
    return EmployeeImportResponse(
        imported=imported,
        skipped=skipped,
        errors=errors[:20],
    )


async def update_employee_status(
    tenant_code: str,
    employee_id: int,
    status: str,
) -> EmployeeItem:
    target = await admin_org_repository.get_employee(tenant_code, employee_id)
    if target is None:
        raise AdminOrgError("员工不存在")

    if target["status"] != status:
        await admin_org_repository.update_employee_status(tenant_code, employee_id, status)
        target = await admin_org_repository.get_employee(tenant_code, employee_id)

    if target is None:
        raise AdminOrgError("员工不存在")
    return _to_employee_item(target)


