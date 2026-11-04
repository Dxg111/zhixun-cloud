"""管理后台全局搜索服务"""

from __future__ import annotations

import asyncio
from urllib.parse import quote

from app.models.admin_search import GlobalSearchItem, GlobalSearchResponse
from app.repositories import (
    admin_document_repository,
    admin_exam_repository,
    admin_org_repository,
    knowledge_card_repository,
    question_repository,
)


def _url(path: str, keyword: str) -> str:
    return f"{path}?keyword={quote(keyword, safe='')}"


def _clip(value: str, length: int = 80) -> str:
    text = (value or "").strip().replace("\n", " ")
    return text if len(text) <= length else f"{text[:length]}…"


async def search(tenant_code: str, keyword: str, limit: int = 5) -> GlobalSearchResponse:
    normalized = keyword.strip()
    if not normalized:
        return GlobalSearchResponse(keyword="", total=0, items=[])

    (
        employee_result,
        question_result,
        exam_result,
        card_result,
        documents,
    ) = await asyncio.gather(
        admin_org_repository.list_employees(tenant_code, None, normalized, 1, limit),
        question_repository.list_questions(tenant_code, "all", normalized, 1, limit),
        admin_exam_repository.list_exams(tenant_code, "all", normalized, 1, limit),
        knowledge_card_repository.list_cards(tenant_code, "all", normalized, 1, limit),
        admin_document_repository.list_documents(tenant_code),
    )

    employees, _ = employee_result
    questions, _, _ = question_result
    exams, _, _ = exam_result
    cards, _ = card_result

    items: list[GlobalSearchItem] = []

    for employee in employees:
        items.append(
            GlobalSearchItem(
                type="employee",
                id=employee["id"],
                title=employee["name"],
                subtitle=f"工号 {employee['employee_no']} / {employee['org_path'] or '未分配部门'}",
                status=employee["status"],
                url=_url("/org", employee["employee_no"]).replace("keyword=", "employee_no="),
            )
        )

    for question in questions:
        items.append(
            GlobalSearchItem(
                type="question",
                id=question["id"],
                title=_clip(question["stem"]),
                subtitle=" / ".join(
                    part
                    for part in (question["bank_name"], question["knowledge_point"] or "")
                    if part
                ),
                status=question["status"],
                url=_url("/questions", _clip(question["stem"], 40)),
            )
        )

    for exam in exams:
        items.append(
            GlobalSearchItem(
                type="exam",
                id=exam["id"],
                title=exam["title"],
                subtitle=" / ".join(
                    part for part in (exam["bank_name"], f"{exam['question_count']} 题") if part
                ),
                status=exam["status"],
                url=_url("/exams", exam["title"]),
            )
        )

    for card in cards:
        items.append(
            GlobalSearchItem(
                type="card",
                id=card["id"],
                title=card["title"],
                subtitle=f"来源 {card['doc_name'] or '未关联文档'}",
                status=card["status"],
                url=_url("/cards", card["title"]),
            )
        )

    lowered = normalized.lower()
    for document in documents:
        if lowered not in (document["file_name"] or "").lower():
            continue
        items.append(
            GlobalSearchItem(
                type="document",
                id=document["id"],
                title=document["file_name"],
                subtitle=f"{document['file_type'].upper()} / {document['chunks']} 个知识片段",
                status=document["status"],
                url=_url("/knowledge", document["file_name"]),
            )
        )
        if sum(1 for item in items if item.type == "document") >= limit:
            break

    return GlobalSearchResponse(keyword=normalized, total=len(items), items=items)
