"""初始化演示题库和题目。

用法：
    cd backend
    python scripts/seed_question_bank.py
    python scripts/seed_question_bank.py --force   # 清空 demo 题库后重新写入
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402

TENANT_CODE = "demo"

BANKS = [
    ("食品安全题库", "食品安全、冷藏、过期原料等门店合规题目"),
    ("门店SOP题库", "开闭店、客诉、收银等门店操作题目"),
    ("消防安全题库", "消防器材和应急演练题目"),
    ("新人培训题库", "新人上岗基础题目"),
]

QUESTIONS = [
    {
        "bank": "食品安全题库",
        "type": "single",
        "stem": "冷藏食品的中心温度应控制在哪个范围？",
        "options": [
            {"key": "A", "text": "0–4℃"},
            {"key": "B", "text": "5–10℃"},
            {"key": "C", "text": "10–15℃"},
            {"key": "D", "text": "15–20℃"},
        ],
        "answer": ["A"],
        "explanation": "冷藏食品应保持在 0–4℃，超过 4℃ 会进入危险温度带，细菌繁殖速度明显加快。",
        "knowledge_point": "冷藏管理",
        "difficulty": "easy",
        "source": "《食品安全操作规范》P12",
        "status": "draft",
        "ai_meta": "deepseek-chat · 2026-11-02 09:14",
    },
    {
        "bank": "门店SOP题库",
        "type": "multiple",
        "stem": "以下哪些属于开闭店检查项？",
        "options": [
            {"key": "A", "text": "门锁与卷帘"},
            {"key": "B", "text": "冷藏温度"},
            {"key": "C", "text": "员工排班"},
            {"key": "D", "text": "竞品促销"},
        ],
        "answer": ["A", "B", "C"],
        "explanation": "开闭店检查覆盖安全、设备和人员安排。竞品促销不属于门店检查项。",
        "knowledge_point": "门店 SOP",
        "difficulty": "medium",
        "source": "《门店SOP手册 v3》P8",
        "status": "draft",
        "ai_meta": "deepseek-chat · 2026-11-02 09:18",
    },
    {
        "bank": "食品安全题库",
        "type": "judge",
        "stem": "发现过期原料，应先记录再继续使用。",
        "options": [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
        "answer": ["B"],
        "explanation": "过期原料必须立即隔离并按规定处理，不能继续使用。记录只是后续动作。",
        "knowledge_point": "食品安全",
        "difficulty": "easy",
        "source": "《食品安全操作规范》P21",
        "status": "approved",
        "ai_meta": "deepseek-chat · 2026-11-01 16:42",
    },
    {
        "bank": "门店SOP题库",
        "type": "single",
        "stem": "顾客投诉时，第一步应该做什么？",
        "options": [
            {"key": "A", "text": "解释公司规定"},
            {"key": "B", "text": "先道歉并倾听"},
            {"key": "C", "text": "转交同事"},
            {"key": "D", "text": "记录后离开"},
        ],
        "answer": ["B"],
        "explanation": "先道歉并倾听可以降低对抗情绪，再进入记录、解决和回访。",
        "knowledge_point": "客诉处理",
        "difficulty": "medium",
        "source": "《客诉处理指引》P3",
        "status": "approved",
        "ai_meta": "deepseek-chat · 2026-11-01 15:20",
    },
    {
        "bank": "消防安全题库",
        "type": "multiple",
        "stem": "消防器材月检应包含哪些内容？",
        "options": [
            {"key": "A", "text": "压力表读数"},
            {"key": "B", "text": "保险销状态"},
            {"key": "C", "text": "摆放位置"},
            {"key": "D", "text": "更换整套器材"},
        ],
        "answer": ["A", "B", "C"],
        "explanation": "月检关注压力、保险销和摆放位置。整套更换不是每月必做项。",
        "knowledge_point": "消防安全",
        "difficulty": "medium",
        "source": "《消防应急预案》P6",
        "status": "draft",
        "ai_meta": "deepseek-chat · 2026-11-01 11:08",
    },
    {
        "bank": "门店SOP题库",
        "type": "single",
        "stem": "收银差异超过多少需要上报店长？",
        "options": [
            {"key": "A", "text": "1 元"},
            {"key": "B", "text": "5 元"},
            {"key": "C", "text": "10 元"},
            {"key": "D", "text": "50 元"},
        ],
        "answer": ["C"],
        "explanation": "单笔收银差异超过 10 元需要立即上报店长并填写差异记录。",
        "knowledge_point": "收银管理",
        "difficulty": "easy",
        "source": "《收银SOP》P4",
        "status": "approved",
        "ai_meta": "deepseek-chat · 2026-10-31 14:30",
    },
    {
        "bank": "新人培训题库",
        "type": "judge",
        "stem": "新人上岗考核可以跳过食品安全模块。",
        "options": [{"key": "A", "text": "正确"}, {"key": "B", "text": "错误"}],
        "answer": ["B"],
        "explanation": "食品安全是上岗前置条件，不能跳过。该题与合规要求冲突，需要重写。",
        "knowledge_point": "新人培训",
        "difficulty": "easy",
        "source": "《新人入职手册》P2",
        "status": "rejected",
        "ai_meta": "deepseek-chat · 2026-10-30 10:02",
        "review_note": "与合规要求冲突，题干假设不成立。",
    },
    {
        "bank": "食品安全题库",
        "type": "single",
        "stem": "冷藏柜温度记录应该多久填写一次？",
        "options": [
            {"key": "A", "text": "每小时"},
            {"key": "B", "text": "每 2 小时"},
            {"key": "C", "text": "每 4 小时"},
            {"key": "D", "text": "每天一次"},
        ],
        "answer": ["C"],
        "explanation": "营业期间每 4 小时记录一次冷藏柜温度，异常时立即处理并上报。",
        "knowledge_point": "冷藏管理",
        "difficulty": "medium",
        "source": "《食品安全操作规范》P14",
        "status": "draft",
        "ai_meta": "deepseek-chat · 2026-10-30 09:48",
    },
    {
        "bank": "门店SOP题库",
        "type": "multiple",
        "stem": "客诉处理四步法包括哪些动作？",
        "options": [
            {"key": "A", "text": "倾听"},
            {"key": "B", "text": "道歉"},
            {"key": "C", "text": "解决"},
            {"key": "D", "text": "回访"},
        ],
        "answer": ["A", "B", "C", "D"],
        "explanation": "倾听、道歉、解决、回访构成完整闭环。",
        "knowledge_point": "客诉处理",
        "difficulty": "medium",
        "source": "《客诉处理指引》P2",
        "status": "approved",
        "ai_meta": "deepseek-chat · 2026-10-29 17:12",
    },
]


async def seed(force: bool) -> None:
    await init_mysql()
    pool = get_mysql_pool()
    if pool is None:
        raise RuntimeError("MySQL 未初始化")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM questions WHERE tenant_code = %s",
                (TENANT_CODE,),
            )
            row = await cur.fetchone()
            existing = int(row[0]) if row else 0

            if existing and not force:
                print(f"题库已有 {existing} 道题，跳过。需要重刷请加 --force")
                return

            if force:
                await cur.execute("DELETE FROM questions WHERE tenant_code = %s", (TENANT_CODE,))
                await cur.execute("DELETE FROM question_banks WHERE tenant_code = %s", (TENANT_CODE,))
                print("已清空 demo 题库")

            bank_ids: dict[str, int] = {}
            for name, description in BANKS:
                await cur.execute(
                    "INSERT INTO question_banks (tenant_code, name, description, status) "
                    "VALUES (%s, %s, %s, 'active') "
                    "ON DUPLICATE KEY UPDATE description = VALUES(description)",
                    (TENANT_CODE, name, description),
                )
                await cur.execute(
                    "SELECT id FROM question_banks WHERE tenant_code = %s AND name = %s",
                    (TENANT_CODE, name),
                )
                bank_row = await cur.fetchone()
                bank_ids[name] = int(bank_row[0])

            for question in QUESTIONS:
                reviewed = question["status"] != "draft"
                await cur.execute(
                    "INSERT INTO questions "
                    "(tenant_code, bank_id, type, stem, options_json, answer_json, explanation, "
                    "knowledge_point, difficulty, source_ref, status, ai_meta, review_note, "
                    "reviewed_by, reviewed_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        TENANT_CODE,
                        bank_ids[question["bank"]],
                        question["type"],
                        question["stem"],
                        json.dumps(question["options"], ensure_ascii=False),
                        json.dumps(question["answer"], ensure_ascii=False),
                        question["explanation"],
                        question["knowledge_point"],
                        question["difficulty"],
                        question["source"],
                        question["status"],
                        question["ai_meta"],
                        question.get("review_note"),
                        "admin" if reviewed else None,
                        datetime.now() if reviewed else None,
                    ),
                )

            await cur.execute(
                "SELECT COUNT(*) FROM questions WHERE tenant_code = %s",
                (TENANT_CODE,),
            )
            total = (await cur.fetchone())[0]
            print(f"已写入 {total} 道题，{len(BANKS)} 个题库")

    await close_mysql_pool()


if __name__ == "__main__":
    asyncio.run(seed("--force" in sys.argv))
