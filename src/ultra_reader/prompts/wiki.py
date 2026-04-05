"""
Wiki 整理 Prompt 模板

用于将知识本体整理成 Obsidian Wiki 格式
"""


class WikiPrompts:
    """
    Wiki 整理 Prompt 模板

    用于将提取的知识整理成 Obsidian 友好的格式
    """

    SYSTEM = """你是一个本体论 Wiki 编辑，负责将知识本体整理成 Obsidian Wiki。

你的任务：
1. 将本体转换为 Obsidian 友好的页面结构
2. 确保双向链接的正确性和完整性
3. 生成便于导航的索引页面
4. 保持本体的语义完整性

核心原则：
- 每个实体一个页面
- 每个页面包含：定义、关系、来源
- 使用双向链接建立知识网络"""

    @classmethod
    def compile_index(
        cls,
        book_title: str,
        author: str,
        entity_count: int,
        relation_count: int,
        event_count: int,
        concept_count: int,
        summary: str,
    ) -> str:
        """
        生成索引页编译 Prompt

        Args:
            book_title: 书名
            author: 作者
            entity_count: 实体数量
            relation_count: 关系数量
            event_count: 事件数量
            concept_count: 概念数量
            summary: 摘要

        Returns:
            索引页 Prompt
        """
        return f"""## 书名: {book_title}
## 作者: {author}

## 统计信息:
- 实体数量: {entity_count}
- 关系数量: {relation_count}
- 事件数量: {event_count}
- 概念数量: {concept_count}

## 摘要:
{summary}

## 你的任务

请生成 Obsidian Wiki 索引页内容，包含：
1. 书籍基本信息
2. 核心实体列表（带链接）
3. 核心关系（带链接）
4. 重要事件列表
5. 核心概念列表
6. 导航到各索引页面

请用 Markdown 格式输出。"""

    @classmethod
    def entity_page(
        cls,
        entity_name: str,
        entity_type: str,
        description: str,
        aliases: list[str],
        related_entities: list[str],
        related_events: list[str],
        source_chapter: int,
    ) -> str:
        """
        生成实体页面 Prompt

        Args:
            entity_name: 实体名称
            entity_type: 实体类型
            description: 描述
            aliases: 别名列表
            related_entities: 相关实体列表
            related_events: 相关事件列表
            source_chapter: 来源章节

        Returns:
            实体页面 Prompt
        """
        aliases_str = ", ".join(f"[[{a}]]" for a in aliases) if aliases else "无"
        related_str = "\n".join(f"- {r}" for r in related_entities) if related_entities else "（暂无）"
        events_str = "\n".join(f"- [[{e}]]" for e in related_events) if related_events else "（未参与事件）"

        return f"""## 实体: {entity_name}
## 类型: {entity_type}

### 描述:
{description}

### 别名:
{aliases_str}

### 相关实体:
{related_str}

### 参与事件:
{events_str}

### 来源:
第 {source_chapter} 章

## 你的任务

请生成完整的实体页面 Markdown 内容，包含：
1. YAML Frontmatter（type, name, category 等）
2. 实体定义
3. 关系列表
4. 参与事件
5. 来源章节

请用 Markdown 格式输出。"""
