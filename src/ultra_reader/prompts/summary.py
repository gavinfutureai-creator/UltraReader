"""
摘要生成 Prompt 模板
"""


class SummaryPrompts:
    """
    摘要生成 Prompt 模板

    用于生成书籍或章节的摘要
    """

    SYSTEM = """你是一个知识摘要专家，负责从书籍内容中提炼核心信息。

你的任务：
1. 提炼核心主题
2. 概括主要内容
3. 识别关键信息
4. 保持语言的简洁和准确"""

    @classmethod
    def book_summary(
        cls,
        book_title: str,
        entities: list[str],
        relations: list[str],
        events: list[str],
        concepts: list[str],
    ) -> str:
        """
        生成书籍摘要 Prompt

        Args:
            book_title: 书名
            entities: 核心实体列表
            relations: 核心关系列表
            events: 核心事件列表
            concepts: 核心概念列表

        Returns:
            书籍摘要 Prompt
        """
        entities_str = "\n".join(f"- {e}" for e in entities[:20])
        relations_str = "\n".join(f"- {r}" for r in relations[:15])
        events_str = "\n".join(f"- {e}" for e in events[:10])
        concepts_str = "\n".join(f"- {c}" for c in concepts[:10])

        return f"""## 书名: {book_title}

请根据以下提取的知识，生成书籍摘要：

### 核心实体:
{entities_str}

### 核心关系:
{relations_str}

### 重要事件:
{events_str}

### 核心概念:
{concepts_str}

### 你的任务

请用 200-500 字概括这本书的核心内容，包括：
1. 主题是什么
2. 有哪些核心人物/实体
3. 主要讲述了什么故事/观点
4. 有什么重要意义

请用简洁、准确的中文回答。"""

    @classmethod
    def chapter_summary(
        cls,
        chapter_index: int,
        chapter_title: str,
        chapter_content: str,
    ) -> str:
        """
        生成章节摘要 Prompt

        Args:
            chapter_index: 章节索引
            chapter_title: 章节标题
            chapter_content: 章节内容（摘要版）

        Returns:
            章节摘要 Prompt
        """
        # 限制内容长度
        content = chapter_content[:3000] if len(chapter_content) > 3000 else chapter_content

        return f"""## 第 {chapter_index} 章: {chapter_title}

请用 50-150 字概括这一章的内容：

{content}

请用简洁的中文回答。"""
