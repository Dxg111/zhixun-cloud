"""知识卡生成 Prompt V1"""

KNOWLEDGE_CARD_SYSTEM_PROMPT = (
    "你是一名企业培训内容编辑。你只能输出合法 JSON，不要输出任何 JSON 之外的内容，"
    "包括 markdown、注释、说明文字。所有内容必须来自提供的培训文档，不要编造。"
)

KNOWLEDGE_CARD_HUMAN_PROMPT = """请基于以下培训文档内容，生成 {card_count} 张考前速览知识卡。

要求：
1. 输出必须是合法 JSON，不要输出任何 JSON 之外的内容。
2. 每张卡包含 2–4 个要点，每个要点有 heading（小标题）和 body（正文）。
3. 单张卡正文合计 200–400 字，确保 1 分钟内能读完。
4. 只提炼文档中的概念、流程和操作要点，不要生成考试题目或答案。
5. 每张卡给出 source_ref，格式为“文档名 · 章节/段落线索”，便于管理员核对。
6. 卡片风格：{style}。
7. title 不超过 20 字，heading 不超过 16 字。

JSON 输出结构如下（严格按此结构输出）：
{{
  "cards": [
    {{
      "title": "卡片标题",
      "points": [
        {{"heading": "小标题", "body": "要点正文"}}
      ],
      "source_ref": "文档名 · 第 3 段"
    }}
  ]
}}

培训文档内容如下：
{content}
"""
