"""初始化演示知识卡。

用法：
    cd backend
    python scripts/seed_knowledge_cards.py
    python scripts/seed_knowledge_cards.py --force
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import close_mysql_pool, get_mysql_pool, init_mysql  # noqa: E402

TENANT_CODE = "demo"

CARDS = [
    {
        "doc_name": "食品安全操作规范.docx",
        "title": "冷藏温度三原则",
        "excerpt": "0–4℃ 冷藏、每 4 小时记录、异常立即隔离并上报。",
        "source": "食品安全操作规范 P12",
        "status": "published",
        "view_rate": 72,
    },
    {
        "doc_name": "门店SOP手册-v3.pdf",
        "title": "开闭店五步法",
        "excerpt": "门锁、设备、温度、陈列、现金，五项逐项确认。",
        "source": "门店SOP手册 v3 P8",
        "status": "draft",
        "view_rate": 0,
    },
    {
        "doc_name": "客诉处理指引.pdf",
        "title": "客诉处理四步",
        "excerpt": "先倾听、再道歉、后解决、必回访。",
        "source": "客诉处理指引 P3",
        "status": "published",
        "view_rate": 64,
    },
    {
        "doc_name": "消防应急预案.pdf",
        "title": "消防器材月检",
        "excerpt": "压力表、保险销、摆放位置三项必查。",
        "source": "消防应急预案 P6",
        "status": "offline",
        "view_rate": 38,
    },
    {
        "doc_name": "收银SOP.pdf",
        "title": "收银差异上报",
        "excerpt": "单笔差异超过 10 元，立即上报店长并填写记录。",
        "source": "收银SOP P4",
        "status": "draft",
        "view_rate": 0,
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
                "SELECT COUNT(*) FROM knowledge_cards WHERE tenant_code = %s",
                (TENANT_CODE,),
            )
            row = await cur.fetchone()
            existing = int(row[0]) if row else 0

            if existing and not force:
                print(f"知识卡已有 {existing} 张，跳过。需要重刷请加 --force")
                return

            if force:
                await cur.execute(
                    "DELETE FROM knowledge_cards WHERE tenant_code = %s",
                    (TENANT_CODE,),
                )
                print("已清空 demo 知识卡")

            for card in CARDS:
                published_at = datetime.now() if card["status"] == "published" else None
                await cur.execute(
                    "INSERT INTO knowledge_cards "
                    "(tenant_code, doc_name, title, excerpt, source_ref, status, view_rate, "
                    "created_by, published_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        TENANT_CODE,
                        card["doc_name"],
                        card["title"],
                        card["excerpt"],
                        card["source"],
                        card["status"],
                        card["view_rate"],
                        "admin",
                        published_at,
                    ),
                )

            await cur.execute(
                "SELECT COUNT(*) FROM knowledge_cards WHERE tenant_code = %s",
                (TENANT_CODE,),
            )
            total = (await cur.fetchone())[0]
            print(f"已写入 {total} 张知识卡")

    await close_mysql_pool()


if __name__ == "__main__":
    asyncio.run(seed("--force" in sys.argv))
