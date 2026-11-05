"""验证题目编辑 / 删除接口

插入一条临时题目，走真实 HTTP 接口编辑、删除，结束后物理清理。
运行：python scripts/verify_question_edit.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.auth import create_admin_token  # noqa: E402
from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402

BASE = "http://127.0.0.1:8000/api/v1"
TENANT = "demo"


async def _create_temp_question() -> int:
    pool = get_mysql_pool()
    assert pool is not None
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO questions "
                "(tenant_code, bank_id, type, stem, options_json, answer_json, "
                "explanation, knowledge_point, difficulty, source_ref, status) "
                "VALUES (%s, 6, 'multiple', %s, %s, %s, %s, %s, 'medium', '自检', 'approved')",
                (
                    TENANT,
                    "临时题目：原始题干",
                    json.dumps(
                        [
                            {"key": "A", "text": "选项 A"},
                            {"key": "B", "text": "选项 B"},
                        ],
                        ensure_ascii=False,
                    ),
                    json.dumps(["A"]),
                    "原始解析",
                    "自检知识点",
                ),
            )
            return int(cur.lastrowid)


async def _cleanup(question_id: int) -> None:
    pool = get_mysql_pool()
    if pool is None:
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM questions WHERE id = %s", (question_id,))


async def main() -> int:
    await init_mysql()
    question_id = await _create_temp_question()
    admin_token = create_admin_token("admin", "tenant_admin", TENANT, "测试管理员")
    headers = {"Authorization": f"Bearer {admin_token}"}
    failed = False

    try:
        async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
            resp = await client.put(
                f"/admin/questions/{question_id}",
                headers=headers,
                json={
                    "stem": "临时题目：编辑后的题干",
                    "options": [
                        {"key": "A", "text": "新选项 A"},
                        {"key": "B", "text": "新选项 B"},
                        {"key": "C", "text": "新选项 C"},
                    ],
                    "answer": ["A", "C"],
                    "explanation": "编辑后的解析",
                    "knowledge_point": "编辑后知识点",
                    "difficulty": "hard",
                },
            )
            body = resp.json()
            data = body.get("data") or {}
            ok = (
                resp.status_code == 200
                and body.get("code") == 0
                and data.get("status") == "draft"
                and data.get("stem") == "临时题目：编辑后的题干"
            )
            print(f"[{'PASS' if ok else 'FAIL'}] 编辑题目 -> 状态 {data.get('status')}")
            failed = failed or not ok

            resp = await client.delete(
                f"/admin/questions/{question_id}", headers=headers
            )
            ok = resp.json().get("code") == 0
            print(f"[{'PASS' if ok else 'FAIL'}] 删除题目")
            failed = failed or not ok

            resp = await client.get(
                "/admin/questions?status=all&keyword=临时题目",
                headers=headers,
            )
            items = (resp.json().get("data") or {}).get("items") or []
            ok = all(item["id"] != question_id for item in items)
            print(f"[{'PASS' if ok else 'FAIL'}] 已删除题目不再出现在列表")
            failed = failed or not ok
    finally:
        await _cleanup(question_id)
        await close_mysql_pool()

    print("RESULT:", "failed" if failed else "passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
