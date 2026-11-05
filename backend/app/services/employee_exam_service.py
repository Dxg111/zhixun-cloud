"""员工登录与答题服务"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import structlog

from app.core.exceptions import AdminExamError, AuthenticationError
from app.models.employee_exam import (
    EmployeeAnswerInput,
    EmployeeExamItem,
    EmployeeExamListResponse,
    EmployeePaperResponse,
    EmployeeResultDetail,
    EmployeeResultResponse,
    PaperQuestion,
    SavedAnswer,
)
from app.repositories import (
    admin_org_repository,
    employee_exam_repository,
    wrong_question_repository,
)
from app.services import notification_service, settings_service

logger = structlog.get_logger()


async def list_exams(tenant_code: str, employee_id: int) -> EmployeeExamListResponse:
    rows = await employee_exam_repository.list_exams_for_employee(tenant_code, employee_id)

    refreshed = False
    for row in rows:
        if row.get("attempt_status") == "in_progress" and row.get("attempt_id"):
            attempt = await employee_exam_repository.get_attempt(
                tenant_code, row["attempt_id"], employee_id
            )
            if attempt is not None and _is_expired(attempt):
                await _auto_submit_if_expired(tenant_code, employee_id, attempt)
                refreshed = True

    if refreshed:
        rows = await employee_exam_repository.list_exams_for_employee(
            tenant_code, employee_id
        )

    return EmployeeExamListResponse(
        items=[
            EmployeeExamItem(
                id=row["id"],
                title=row["title"],
                question_count=row["question_count"],
                duration_minutes=row["duration_minutes"],
                pass_score=row["pass_score"],
                max_attempts=row["max_attempts"],
                start_at=row["start_at"],
                end_at=row["end_at"],
                status=row["status"],
                assigned_at=row["assigned_at"],
                attempt_id=row["attempt_id"],
                attempt_status=row["attempt_status"],
                attempt_count=row.get("attempt_count", 0),
                score=row["score"],
                passed=row["passed"],
                submitted_at=row["submitted_at"],
                computed_state=row.get("computed_state", "pending"),
            )
            for row in rows
        ]
    )


async def _load_paper(exam_id: int) -> list[dict]:
    questions = await employee_exam_repository.get_paper_questions(exam_id)
    if not questions:
        raise AdminExamError("考试未配置题目，请管理员重新发布")
    return questions


def _paper_question(item: dict) -> PaperQuestion:
    snapshot = item["snapshot"]
    return PaperQuestion(
        id=int(snapshot["id"]),
        type=snapshot["type"],
        stem=snapshot["stem"],
        options=snapshot["options"],
        score=item["score"],
    )


def _stored_answers(attempt: dict) -> list[EmployeeAnswerInput]:
    try:
        return [EmployeeAnswerInput(**item) for item in attempt.get("answers", [])]
    except (TypeError, ValueError):
        return []


def _is_expired(attempt: dict) -> bool:
    expires_at = attempt.get("expires_at_dt")
    return bool(expires_at and datetime.now() >= expires_at)


def _paper_response(
    attempt: dict,
    title: str,
    duration_minutes: int,
    questions: list[dict],
) -> EmployeePaperResponse:
    return EmployeePaperResponse(
        attempt_id=attempt["id"],
        exam_id=attempt["exam_id"],
        title=title,
        duration_minutes=duration_minutes,
        expires_at=attempt["expires_at"],
        questions=[_paper_question(item) for item in questions],
        saved_answers=[SavedAnswer(**answer) for answer in attempt.get("answers", [])],
    )


def _result_from_attempt(
    attempt: dict,
    question_rows: list[dict],
    answers: list[EmployeeAnswerInput],
) -> EmployeeResultResponse:
    answer_map = {answer.question_id: answer.selected for answer in answers}
    details: list[EmployeeResultDetail] = []
    correct_count = 0

    for item in question_rows:
        snapshot = item["snapshot"]
        question_id = int(snapshot["id"])
        selected = answer_map.get(question_id, [])
        correct_answer = snapshot["answer"]
        is_correct = set(selected) == set(correct_answer)
        if is_correct:
            correct_count += 1
        details.append(
            EmployeeResultDetail(
                question_id=question_id,
                type=snapshot["type"],
                stem=snapshot["stem"],
                selected=selected,
                answer=correct_answer,
                is_correct=is_correct,
                explanation=snapshot["explanation"],
                score=item["score"],
            )
        )

    total = len(question_rows)
    score = round(correct_count / total * 100, 2) if total else 0.0
    pass_score = float(attempt.get("pass_score") or 60)
    return EmployeeResultResponse(
        attempt_id=attempt["id"],
        exam_id=attempt["exam_id"],
        title=attempt.get("title", ""),
        score=score,
        passed=score >= pass_score,
        correct_count=correct_count,
        total_count=total,
        submitted_at=attempt.get("submitted_at") or "",
        details=details,
    )


async def _collect_wrong_questions(
    tenant_code: str,
    employee_id: int,
    attempt: dict,
    question_rows: list[dict],
    result: EmployeeResultResponse,
) -> None:
    correct_ids = {detail.question_id for detail in result.details if detail.is_correct}
    wrong_snapshots = [
        item["snapshot"]
        for item in question_rows
        if int(item["snapshot"]["id"]) not in correct_ids
    ]
    if not wrong_snapshots:
        return

    await wrong_question_repository.upsert_from_exam(
        tenant_code=tenant_code,
        employee_id=employee_id,
        attempt_id=attempt["id"],
        wrong_items=wrong_snapshots,
    )


async def _finalize_submission(
    tenant_code: str,
    employee_id: int,
    attempt: dict,
    question_rows: list[dict],
    answers: list[EmployeeAnswerInput],
) -> tuple[EmployeeResultResponse, bool]:
    result = _result_from_attempt(attempt, question_rows, answers)
    duration_seconds = sum(answer.duration_ms for answer in answers) // 1000
    updated = await employee_exam_repository.submit_attempt(
        attempt_id=attempt["id"],
        score=result.score,
        passed=result.passed,
        answers_json=json.dumps(
            [answer.model_dump() for answer in answers],
            ensure_ascii=False,
        ),
        duration_seconds=duration_seconds,
    )
    if updated:
        await _collect_wrong_questions(
            tenant_code=tenant_code,
            employee_id=employee_id,
            attempt=attempt,
            question_rows=question_rows,
            result=result,
        )
        await _notify_result_ready(tenant_code, employee_id, attempt, result)
    return result, updated


async def _notify_result_ready(
    tenant_code: str,
    employee_id: int,
    attempt: dict,
    result: EmployeeResultResponse,
) -> None:
    """成绩生成后通知员工；通知失败不影响判分。"""
    try:
        settings = await settings_service.get_settings(tenant_code)
        if not settings.notify_result:
            return
        assignment = await employee_exam_repository.get_assignment(
            tenant_code, attempt["exam_id"], employee_id
        )
        exam_title = (assignment or {}).get("title") or "考试"
        await notification_service.notify_result_ready(
            tenant_code,
            attempt["exam_id"],
            exam_title,
            employee_id,
            attempt["id"],
            result.score,
            result.passed,
        )
    except Exception as exc:
        logger.error(
            "result_notify_failed",
            tenant_code=tenant_code,
            employee_id=employee_id,
            attempt_id=attempt.get("id"),
            error=str(exc),
            exc_info=True,
        )


async def _auto_submit_if_expired(
    tenant_code: str,
    employee_id: int,
    attempt: dict,
) -> dict:
    if attempt.get("status") != "in_progress" or not _is_expired(attempt):
        return attempt

    question_rows = await _load_paper(attempt["exam_id"])
    stored = _stored_answers(attempt)
    await _finalize_submission(
        tenant_code=tenant_code,
        employee_id=employee_id,
        attempt=attempt,
        question_rows=question_rows,
        answers=stored,
    )
    refreshed = await employee_exam_repository.get_attempt(
        tenant_code, attempt["id"], employee_id
    )
    return refreshed or attempt


async def start_exam(
    tenant_code: str,
    employee_id: int,
    exam_id: int,
) -> EmployeePaperResponse:
    assignment = await employee_exam_repository.get_assignment(
        tenant_code, exam_id, employee_id
    )
    if assignment is None:
        raise AdminExamError("没有分配该考试")

    employee = await admin_org_repository.get_employee(tenant_code, employee_id)
    if employee is None or employee["status"] != "active":
        raise AuthenticationError("员工已停用，无法参加考试")

    questions = await _load_paper(exam_id)

    attempt = await employee_exam_repository.get_in_progress_attempt(
        tenant_code, exam_id, employee_id
    )
    if attempt is not None:
        attempt = await _auto_submit_if_expired(tenant_code, employee_id, attempt)
        if attempt.get("status") == "in_progress":
            return _paper_response(
                attempt,
                assignment["title"],
                assignment["duration_minutes"],
                questions,
            )

    if assignment["status"] != "published":
        raise AdminExamError("考试已结束，不能重新开始")

    now = datetime.now()
    if assignment["start_at"] and now < assignment["start_at"]:
        raise AdminExamError("考试尚未开始")
    if assignment["end_at"] and now > assignment["end_at"]:
        raise AdminExamError("考试已结束")

    submitted = await employee_exam_repository.count_submitted_attempts(
        tenant_code, exam_id, employee_id
    )
    if submitted >= assignment["max_attempts"]:
        raise AdminExamError("已用完重考次数")

    expires_at = now + timedelta(minutes=assignment["duration_minutes"])
    if assignment["end_at"] and assignment["end_at"] < expires_at:
        expires_at = assignment["end_at"]

    attempt_id = await employee_exam_repository.create_attempt(
        exam_id=exam_id,
        employee_id=employee_id,
        attempt_no=submitted + 1,
        expires_at=expires_at,
    )
    attempt = await employee_exam_repository.get_attempt(
        tenant_code, attempt_id, employee_id
    )
    if attempt is None:
        raise AdminExamError("开始考试失败")

    return _paper_response(
        attempt,
        assignment["title"],
        assignment["duration_minutes"],
        questions,
    )


async def save_answers(
    tenant_code: str,
    employee_id: int,
    attempt_id: int,
    answers: list[EmployeeAnswerInput],
) -> None:
    attempt = await employee_exam_repository.get_attempt(
        tenant_code, attempt_id, employee_id
    )
    if attempt is None:
        raise AdminExamError("答题记录不存在")
    if attempt["status"] != "in_progress":
        raise AdminExamError("考试已提交，不能继续修改")

    if _is_expired(attempt):
        await _auto_submit_if_expired(tenant_code, employee_id, attempt)
        raise AdminExamError("考试已超时，系统已自动交卷")

    await employee_exam_repository.save_answers(
        attempt_id,
        json.dumps(
            [answer.model_dump() for answer in answers],
            ensure_ascii=False,
        ),
    )


async def submit_exam(
    tenant_code: str,
    employee_id: int,
    attempt_id: int,
    answers: list[EmployeeAnswerInput],
) -> EmployeeResultResponse:
    attempt = await employee_exam_repository.get_attempt(
        tenant_code, attempt_id, employee_id
    )
    if attempt is None:
        raise AdminExamError("答题记录不存在")

    question_rows = await _load_paper(attempt["exam_id"])

    if attempt["status"] == "submitted":
        return _result_from_attempt(attempt, question_rows, _stored_answers(attempt))

    if attempt["status"] != "in_progress":
        raise AdminExamError("当前答题状态不能提交")

    if _is_expired(attempt):
        effective_answers = _stored_answers(attempt)
    else:
        effective_answers = answers or _stored_answers(attempt)

    result, updated = await _finalize_submission(
        tenant_code=tenant_code,
        employee_id=employee_id,
        attempt=attempt,
        question_rows=question_rows,
        answers=effective_answers,
    )

    refreshed = await employee_exam_repository.get_attempt(
        tenant_code, attempt_id, employee_id
    )
    if refreshed is not None and refreshed["status"] == "submitted":
        if updated:
            result.submitted_at = refreshed.get("submitted_at") or result.submitted_at
        else:
            result = _result_from_attempt(
                refreshed, question_rows, _stored_answers(refreshed)
            )
    return result


async def get_result(
    tenant_code: str,
    employee_id: int,
    attempt_id: int,
) -> EmployeeResultResponse:
    attempt = await employee_exam_repository.get_attempt(
        tenant_code, attempt_id, employee_id
    )
    if attempt is None:
        raise AdminExamError("答题记录不存在")

    if attempt["status"] == "in_progress" and _is_expired(attempt):
        attempt = await _auto_submit_if_expired(tenant_code, employee_id, attempt)

    if attempt["status"] != "submitted":
        raise AdminExamError("考试尚未提交")

    question_rows = await _load_paper(attempt["exam_id"])
    return _result_from_attempt(attempt, question_rows, _stored_answers(attempt))
