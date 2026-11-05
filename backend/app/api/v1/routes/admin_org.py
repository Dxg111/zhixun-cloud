"""组织与员工路由"""

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.auth import get_admin_context
from app.models.admin_org import (
    EmployeeCreateRequest,
    EmployeeStatusRequest,
    OrgUnitCreateRequest,
    OrgUnitUpdateRequest,
)
from app.models.common import ApiResponse
from app.services import admin_org_service, audit_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/org-units", response_model=ApiResponse)
async def list_org_units(context: dict = Depends(get_admin_context)):
    result = await admin_org_service.list_org_units(context["tenant_code"])
    return ApiResponse.success(data=result.model_dump())


@router.post("/org-units", response_model=ApiResponse)
async def create_org_unit(
    req: OrgUnitCreateRequest,
    context: dict = Depends(get_admin_context),
):
    result = await admin_org_service.create_org_unit(context["tenant_code"], req)
    await audit_service.record(
        context["tenant_code"],
        context,
        "org.create",
        target_type="org_unit",
        target_id=result.id,
        detail={"name": result.name, "path": result.path},
    )
    return ApiResponse.success(data=result.model_dump())


@router.put("/org-units/{org_id}", response_model=ApiResponse)
async def update_org_unit(
    org_id: int,
    req: OrgUnitUpdateRequest,
    context: dict = Depends(get_admin_context),
):
    result = await admin_org_service.update_org_unit(
        context["tenant_code"], org_id, req
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "org.update",
        target_type="org_unit",
        target_id=org_id,
        detail={"name": result.name, "path": result.path},
    )
    return ApiResponse.success(data=result.model_dump())


@router.delete("/org-units/{org_id}", response_model=ApiResponse)
async def delete_org_unit(org_id: int, context: dict = Depends(get_admin_context)):
    await admin_org_service.delete_org_unit(context["tenant_code"], org_id)
    await audit_service.record(
        context["tenant_code"],
        context,
        "org.delete",
        target_type="org_unit",
        target_id=org_id,
    )
    return ApiResponse.success()


@router.get("/employees", response_model=ApiResponse)
async def list_employees(
    org_id: int | None = Query(None),
    keyword: str = Query("", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    context: dict = Depends(get_admin_context),
):
    result = await admin_org_service.list_employees(
        tenant_code=context["tenant_code"],
        org_id=org_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/employees", response_model=ApiResponse)
async def create_employee(
    req: EmployeeCreateRequest,
    context: dict = Depends(get_admin_context),
):
    result = await admin_org_service.create_employee(context["tenant_code"], req)
    await audit_service.record(
        context["tenant_code"],
        context,
        "employee.create",
        target_type="employee",
        target_id=result.id,
        detail={"employee_no": result.employee_no, "name": result.name},
    )
    return ApiResponse.success(data=result.model_dump())


@router.post("/employees/import", response_model=ApiResponse)
async def import_employees(
    file: UploadFile = File(...),
    context: dict = Depends(get_admin_context),
):
    content = await file.read()
    result = await admin_org_service.import_employees(
        tenant_code=context["tenant_code"],
        filename=file.filename or "employees.xlsx",
        content=content,
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "employee.import",
        target_type="employee",
        detail={"imported": result.imported, "skipped": result.skipped},
    )
    return ApiResponse.success(data=result.model_dump())


@router.put("/employees/{employee_id}/status", response_model=ApiResponse)
async def update_employee_status(
    employee_id: int,
    req: EmployeeStatusRequest,
    context: dict = Depends(get_admin_context),
):
    result = await admin_org_service.update_employee_status(
        tenant_code=context["tenant_code"],
        employee_id=employee_id,
        status=req.status,
    )
    await audit_service.record(
        context["tenant_code"],
        context,
        "employee.status",
        target_type="employee",
        target_id=employee_id,
        detail={"status": req.status},
    )
    return ApiResponse.success(data=result.model_dump())
