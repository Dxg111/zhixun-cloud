"""P0 缺口补齐的单元测试：审计、成绩分析、题目/部门编辑、出题去重、限流、配额"""

import pytest

from app.core.exceptions import AdminOrgError, AuthenticationError, QuestionError
from app.models.admin_org import OrgUnitUpdateRequest
from app.models.question_bank import QuestionUpdateRequest
from app.models.quiz import QuestionOption
from app.repositories import (
    admin_document_repository,
    admin_exam_repository,
    admin_org_repository,
    question_repository,
)
from app.services import (
    admin_auth_service,
    admin_document_service,
    admin_org_service,
    admin_question_generation_service,
    exam_service,
    question_service,
)


# ---------- 题目编辑校验 ----------


def _question_update():
    return QuestionUpdateRequest(
        stem="更新后的题干",
        options=[QuestionOption(key="A", text="选项 A"), QuestionOption(key="B", text="选项 B")],
        answer=["A"],
        explanation="解析",
        knowledge_point="食品安全",
        difficulty="medium",
    )


@pytest.mark.asyncio
async def test_update_question_sends_to_draft(monkeypatch):
    captured: dict = {}

    async def get_question(tenant_code, question_id):
        return {"id": question_id, "type": "single", "status": "approved"}

    async def update(tenant_code, question_id, **kwargs):
        captured.update(kwargs)
        return 1

    async def refreshed(tenant_code, question_id):
        return {
            "id": question_id,
            "tenant_code": "demo",
            "bank_id": 1,
            "bank_name": "题库",
            "type": "single",
            "stem": captured["stem"],
            "options": captured["options"],
            "answer": captured["answer"],
            "explanation": captured["explanation"],
            "knowledge_point": captured["knowledge_point"],
            "difficulty": captured["difficulty"],
            "source": "",
            "status": "draft",
            "ai_meta": "",
            "review_note": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "created_at": "2026-11-05 10:00:00",
            "updated_at": "2026-11-05 10:00:00",
        }

    monkeypatch.setattr(question_repository, "get_question", get_question)
    monkeypatch.setattr(question_repository, "update_question", update)
    monkeypatch.setattr(question_repository, "get_question", get_question)
    monkeypatch.setattr(question_repository, "get_question", get_question)
    # 第二次 get_question 返回刷新后的数据
    calls = {"count": 0}

    async def get_question_seq(tenant_code, question_id):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"id": question_id, "type": "single", "status": "approved"}
        return await refreshed(tenant_code, question_id)

    monkeypatch.setattr(question_repository, "get_question", get_question_seq)

    result = await question_service.update_question("demo", 5, _question_update())

    assert result.status == "draft"
    assert captured["stem"] == "更新后的题干"
    assert captured["answer"] == ["A"]


@pytest.mark.asyncio
async def test_update_question_rejects_bad_answer(monkeypatch):
    async def get_question(tenant_code, question_id):
        return {"id": question_id, "type": "single", "status": "approved"}

    monkeypatch.setattr(question_repository, "get_question", get_question)

    req = QuestionUpdateRequest(
        stem="题干",
        options=[QuestionOption(key="A", text="A"), QuestionOption(key="B", text="B")],
        answer=["C"],
    )

    with pytest.raises(QuestionError):
        await question_service.update_question("demo", 5, req)


@pytest.mark.asyncio
async def test_delete_question_soft_deletes(monkeypatch):
    called: dict = {}

    async def get_question(tenant_code, question_id):
        return {"id": question_id, "type": "single"}

    async def soft_delete(tenant_code, question_id):
        called["id"] = question_id
        return 1

    monkeypatch.setattr(question_repository, "get_question", get_question)
    monkeypatch.setattr(question_repository, "soft_delete_question", soft_delete)

    await question_service.delete_question("demo", 9)

    assert called["id"] == 9


# ---------- 部门编辑与删除 ----------


@pytest.mark.asyncio
async def test_update_org_rejects_move_into_child(monkeypatch):
    async def get_org(tenant_code, org_id):
        return {
            "id": org_id,
            "parent_id": None,
            "name": "华东区",
            "path": "华东区",
        }

    monkeypatch.setattr(admin_org_repository, "get_org", get_org)

    with pytest.raises(AdminOrgError):
        await admin_org_service.update_org_unit(
            "demo", 1, OrgUnitUpdateRequest(name="华东区", parent_id=1)
        )


@pytest.mark.asyncio
async def test_update_org_rewrites_descendant_paths(monkeypatch):
    rewritten: dict = {}

    async def get_org(tenant_code, org_id):
        return {
            "id": org_id,
            "parent_id": None,
            "name": "旧名",
            "path": "旧名",
            "sort": 0,
            "employee_count": 0,
        }

    async def find_by_path(tenant_code, path):
        return None

    async def update(tenant_code, org_id, name, parent_id, path):
        return 1

    async def rewrite(tenant_code, old_path, new_path):
        rewritten["args"] = (old_path, new_path)
        return 2

    monkeypatch.setattr(admin_org_repository, "get_org", get_org)
    monkeypatch.setattr(admin_org_repository, "find_org_by_path", find_by_path)
    monkeypatch.setattr(admin_org_repository, "update_org", update)
    monkeypatch.setattr(admin_org_repository, "rewrite_descendant_paths", rewrite)

    await admin_org_service.update_org_unit(
        "demo", 1, OrgUnitUpdateRequest(name="新名", parent_id=None)
    )

    assert rewritten["args"] == ("旧名", "新名")


@pytest.mark.asyncio
async def test_delete_org_with_employees_is_rejected(monkeypatch):
    async def get_org(tenant_code, org_id):
        return {"id": org_id, "path": "华东区"}

    async def children(tenant_code, org_id):
        return 0

    async def employees(tenant_code, org_id):
        return 3

    monkeypatch.setattr(admin_org_repository, "get_org", get_org)
    monkeypatch.setattr(admin_org_repository, "count_org_children", children)
    monkeypatch.setattr(admin_org_repository, "count_org_employees", employees)

    with pytest.raises(AdminOrgError):
        await admin_org_service.delete_org_unit("demo", 1)


# ---------- 出题去重 ----------


class _Stem:
    def __init__(self, stem: str):
        self.stem = stem


def test_filter_duplicates_removes_similar_stems():
    existing = ["冷藏食品的中心温度应控制在多少度？"]
    questions = [
        _Stem("冷藏食品的中心温度应控制在多少度？"),
        _Stem("灭火器应放置在什么位置？"),
        _Stem("灭火器应放置在什么位置"),
    ]

    kept, skipped = admin_question_generation_service._filter_duplicates(
        questions, existing
    )

    assert len(kept) == 1
    assert skipped == 2
    assert "灭火器" in kept[0].stem


# ---------- 登录限流 ----------


@pytest.mark.asyncio
async def test_admin_login_locks_after_failures(monkeypatch):
    from app.models.auth import AdminLoginRequest

    admin_auth_service._failed_attempts.clear()

    async def pool():
        return object()

    monkeypatch.setattr(admin_auth_service, "get_mysql_pool", lambda: object())

    async def find_admin(tenant_code, login_name):
        return None

    monkeypatch.setattr(
        admin_auth_service.admin_user_repository, "find_admin_by_login", find_admin
    )

    request = AdminLoginRequest(
        tenant_code="demo", login_name="locked-user", password="wrong"
    )

    for _ in range(5):
        with pytest.raises(AuthenticationError):
            await admin_auth_service.handle_admin_login(request)

    with pytest.raises(AuthenticationError) as exc:
        await admin_auth_service.handle_admin_login(request)

    assert "次数过多" in str(exc.value)
    admin_auth_service._failed_attempts.clear()


# ---------- 知识库配额 ----------


@pytest.mark.asyncio
async def test_upload_document_rejects_when_quota_exceeded(monkeypatch):
    async def usage(tenant_code):
        return {"count": 200, "bytes": 0}

    monkeypatch.setattr(admin_document_repository, "get_document_usage", usage)

    with pytest.raises(AdminOrgError) as exc:
        await admin_document_service.upload_document(
            "demo", "test.pdf", b"content", "admin"
        )

    assert "上限" in str(exc.value)


# ---------- 成绩分析 ----------


@pytest.mark.asyncio
async def test_exam_analytics_computes_accuracy(monkeypatch):
    async def get_exam(tenant_code, exam_id):
        return {"id": exam_id, "title": "考核"}

    async def snapshots(exam_id):
        return [
            {
                "question_id": 1,
                "snapshot": {
                    "stem": "题一",
                    "answer": ["A"],
                    "knowledge_point": "知识点甲",
                },
                "score": 50,
            },
            {
                "question_id": 2,
                "snapshot": {
                    "stem": "题二",
                    "answer": ["B"],
                    "knowledge_point": "知识点乙",
                },
                "score": 50,
            },
        ]

    async def attempts(tenant_code, exam_id):
        return [
            {
                "employee_id": 1,
                "score": 50,
                "passed": False,
                "answers": [
                    {"question_id": 1, "selected": ["A"]},
                    {"question_id": 2, "selected": ["A"]},
                ],
                "submitted_at": None,
            },
            {
                "employee_id": 2,
                "score": 100,
                "passed": True,
                "answers": [
                    {"question_id": 1, "selected": ["A"]},
                    {"question_id": 2, "selected": ["B"]},
                ],
                "submitted_at": None,
            },
        ]

    async def assigned(exam_id):
        return [
            {"employee_id": 1, "org_path": "华东区/门店"},
            {"employee_id": 2, "org_path": "华东区/门店"},
            {"employee_id": 3, "org_path": "华北区/门店"},
        ]

    monkeypatch.setattr(admin_exam_repository, "get_exam", get_exam)
    monkeypatch.setattr(admin_exam_repository, "list_exam_question_snapshots", snapshots)
    monkeypatch.setattr(admin_exam_repository, "list_submitted_attempts", attempts)
    monkeypatch.setattr(admin_exam_repository, "list_assigned_employee_orgs", assigned)

    result = await exam_service.get_exam_analytics("demo", 8)

    assert result["assigned_count"] == 3
    assert result["submitted_count"] == 2
    assert result["avg_score"] == 75.0

    accuracy = {item["question_id"]: item for item in result["question_accuracy"]}
    assert accuracy[1]["accuracy"] == 100
    assert accuracy[2]["accuracy"] == 50

    weak = {item["knowledge_point"]: item for item in result["weak_points"]}
    assert weak["知识点乙"]["accuracy"] == 50

    departments = {item["org_path"]: item for item in result["departments"]}
    assert departments["华东区"]["assigned"] == 2
    assert departments["华东区"]["completion_rate"] == 100
    assert departments["华北区"]["completion_rate"] == 0
