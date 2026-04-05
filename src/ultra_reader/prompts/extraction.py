"""
知识提取 Prompt 模板

基于本体论的知识提取 Prompt
"""

from typing import Optional


class ExtractionPrompts:
    """
    知识提取 Prompt 模板

    基于本体论的设计原则：
    - 存在论视角：发现任何存在的事物
    - 关系论视角：用自然语言描述关系
    - 概念论视角：提炼核心概念
    """

    # System Prompt
    SYSTEM = """你是一个本体论知识工程师，负责从书籍章节中构建知识本体。

你的思维方式：

1. 存在论视角
   - "这个章节描绘了什么样的世界？"
   - "什么存在于此章节中？"
   - 不要只关注"人物"，而是关注"任何存在的事物"

2. 关系论视角
   - "这些存在之间有什么关系？"
   - "如何用一句话描述 A 和 B 的关系？"
   - 不要使用预定义的关系类型，而是用书中的自然语言

3. 概念论视角
   - "这个章节在讨论什么核心概念？"
   - "这些概念如何相互关联？"
   - 概念是理解世界的维度，而非预设的分类

重要原则：

✓ 实体类型由你根据书的实际情况发现，而非预设
✓ 关系类型由你根据书的情境命名，而非硬编码
✓ 每条信息都要标注来源章节
✓ 保持输出的可读性和连贯性
✓ 敢于创造性地发现非显而易见的实体和关系"""

    @classmethod
    def user(
        cls,
        book_title: str,
        author: str,
        chapter_index: int,
        chapter_title: str,
        history_context: str,
        chapter_content: str,
    ) -> str:
        """
        生成用户 Prompt

        Args:
            book_title: 书名
            author: 作者
            chapter_index: 章节索引 (从 1 开始)
            chapter_title: 章节标题
            history_context: 历史本体上下文
            chapter_content: 章节内容

        Returns:
            格式化的用户 Prompt
        """
        return f"""## 书名: {book_title}
## 作者: {author}
## 当前处理: 第 {chapter_index} 章 / {chapter_title}

## 历史本体（从之前章节构建的本体）:
{history_context}

## 当前章节内容:
{chapter_content}

## 你的任务

请以本体论视角分析这个章节，输出以下格式（全部使用中文）：

### 一、存在的事物

列出这个章节中出现的**任何重要存在**，使用 [[双向链接]] 格式，例如：[[杨玉环]]。

包括但不限于：
- 人物
- 地点/空间
- 组织/团体
- 物品/道具
- 概念/思想
- 事件/行动
- 时间/时期

### 二、关系网络

描述这些存在之间的**具体关系**，用自然语言描述：

格式：[[实体A]] --[关系描述]--> [[实体B]]

注意：关系描述要具体，不要泛泛而谈

### 三、重要事件

列出这个章节中的**重要事件**：
- 事件名称
- 参与者
- 事件意义

### 四、核心概念

列出这个章节讨论的**核心概念**，以及它们之间的关系。

### 五、章节摘要

用简洁的语言概括这一章的内容。"""

    @classmethod
    def system_simple(cls) -> str:
        """简化版 System Prompt"""
        return """你是一个知识提取专家，负责从书籍章节中提取关键信息。

请提取：
1. 重要实体（人物、地点、概念等）
2. 实体之间的关系
3. 重要事件
4. 核心概念

使用 [[双向链接]] 格式标注实体。"""

    @classmethod
    def user_simple(
        cls,
        chapter_title: str,
        chapter_content: str,
    ) -> str:
        """
        简化版用户 Prompt

        Args:
            chapter_title: 章节标题
            chapter_content: 章节内容

        Returns:
            简化版用户 Prompt
        """
        return f"""## 章节: {chapter_title}

请分析以下内容，提取关键信息：

{chapter_content}

请用简洁的中文回答，包括：
1. 主要实体（使用 [[]] 标注）
2. 实体关系
3. 重要事件
4. 核心概念"""
