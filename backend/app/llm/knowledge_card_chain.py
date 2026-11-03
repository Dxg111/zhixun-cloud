"""知识卡生成 Chain"""

import json
import re

import structlog
from langchain_core.prompts import ChatPromptTemplate

from app.llm.langchain_factory import get_chat_model
from app.models.knowledge_card import KnowledgeCardBatchOutput
from app.prompts.knowledge_card_prompt import (
    KNOWLEDGE_CARD_HUMAN_PROMPT,
    KNOWLEDGE_CARD_SYSTEM_PROMPT,
)

logger = structlog.get_logger()


def _extract_json(text: str) -> dict:
    """从 LLM 输出中提取 JSON，兼容 markdown 代码块包裹。"""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    raw = match.group(1).strip() if match else text.strip()
    return json.loads(raw)


async def generate_knowledge_cards(
    content: str,
    card_count: int = 3,
    style: str = "操作要点",
) -> KnowledgeCardBatchOutput:
    llm = get_chat_model(temperature=0.3)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", KNOWLEDGE_CARD_SYSTEM_PROMPT),
            ("human", KNOWLEDGE_CARD_HUMAN_PROMPT),
        ]
    )

    result = await (prompt | llm).ainvoke(
        {
            "content": content,
            "card_count": card_count,
            "style": style,
        }
    )

    raw = result.content
    if not raw:
        raise ValueError("LLM 返回内容为空")

    data = _extract_json(raw)
    output = KnowledgeCardBatchOutput.model_validate(data)
    logger.info(
        "knowledge_cards_llm_generated",
        card_count=len(output.cards),
        style=style,
    )
    return output
