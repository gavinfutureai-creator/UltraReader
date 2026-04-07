"""Obsidian Wiki 格式写入器"""

from datetime import datetime
from pathlib import Path

from ultra_reader.core.types import Book, Ontology
from ultra_reader.writers.base import BaseWriter


class WikiWriter(BaseWriter):
    """Obsidian Wiki 格式写入器"""

    def __init__(self, output_dir: str | Path = "wiki"):
        super().__init__(output_dir)

    def write(self, book: Book, ontology: Ontology) -> Path:
        """写入 Wiki 文件"""
        output_path = Path(self.output_dir)
        book_dir = output_path / self._sanitize_filename(book.title)
        book_dir.mkdir(parents=True, exist_ok=True)

        self._write_index(book, ontology, book_dir)
        self._write_entities(book, ontology, book_dir)
        self._write_relations(book, ontology, book_dir)
        self._write_events(book, ontology, book_dir)
        self._write_concepts(book, ontology, book_dir)
        self._write_themes(book, ontology, book_dir)

        return book_dir

    def _write_index(self, book: Book, ontology: Ontology, book_dir: Path) -> None:
        """写入索引页面"""
        index_path = book_dir / "index.md"

        entity_links = []
        for entity in ontology.entities[:20]:
            link = f"- [[{entity.name}]]"
            if entity.entity_type:
                link += f" ({entity.entity_type})"
            entity_links.append(link)

        relation_links = []
        for relation in ontology.relations[:15]:
            link = f"- [[{relation.source}]] --[{relation.relation_type or '关联'}]--> [[{relation.target}]]"
            relation_links.append(link)

        event_links = []
        for event in ontology.events[:10]:
            link = f"- [[{event.title}]]"
            if event.chapter is not None:
                link += f" (第{event.chapter + 1}章)"
            event_links.append(link)

        content = f"""---
type: book
title: {book.title}
author: {book.author or '未知'}
processed_at: {datetime.now().isoformat()}
entity_count: {len(ontology.entities)}
relation_count: {len(ontology.relations)}
event_count: {len(ontology.events)}
---

# {book.title}

> 作者: {book.author or '未知'}
> 处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 书籍信息

- 格式: {book.format.value.upper()}
- 章节数: {len(book.chapters)}
- 总字数: {book.total_chars:,}

## 概述

{ontology.summary or '（暂无概述）'}

## 核心实体

{chr(10).join(entity_links) if entity_links else '（暂无实体）'}

## 核心关系

{chr(10).join(relation_links) if relation_links else '（暂无关系）'}

## 重要事件

{chr(10).join(event_links) if event_links else '（暂无事件）'}

## 核心概念

{', '.join(f'[[{c}]]' for c in ontology.concepts[:10]) if ontology.concepts else '（暂无概念）'}

---

*由 UltraReader 自动生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        index_path.write_text(content, encoding="utf-8")

    def _write_entities(self, book: Book, ontology: Ontology, book_dir: Path) -> None:
        """写入实体索引"""
        entities_dir = book_dir / "entities"
        entities_dir.mkdir(exist_ok=True)

        # 按类型分组实体
        type_groups: dict[str, list] = {}
        untyped_entities: list = []

        for entity in ontology.entities:
            if entity.entity_type:
                if entity.entity_type not in type_groups:
                    type_groups[entity.entity_type] = []
                type_groups[entity.entity_type].append(entity)
            else:
                untyped_entities.append(entity)

        # 定义的类型顺序
        TYPE_ORDER = ["人物", "地点", "组织", "物品", "概念", "时间", "未分类"]
        sorted_types = sorted(type_groups.keys(), key=lambda t: TYPE_ORDER.index(t) if t in TYPE_ORDER else 999)

        content = f"""---
type: entities-index
book: {book.title}
---

# 实体索引

> 共 {len(ontology.entities)} 个实体

"""
        # 输出有类型的实体
        for entity_type in sorted_types:
            if entity_type == "未分类":
                continue
            entities = type_groups.get(entity_type, [])
            if entities:
                content += f"## {entity_type}\n\n"
                for entity in entities:
                    chapter_info = f" (首次出现: 第{entity.source_chapter + 1}章)" if entity.source_chapter is not None else ""
                    content += f"- [[{entity.name}]]{chapter_info}\n"
                content += "\n"

        # 输出未分类实体
        if untyped_entities:
            content += "## 未分类\n\n"
            for entity in untyped_entities:
                chapter_info = f" (首次出现: 第{entity.source_chapter + 1}章)" if entity.source_chapter is not None else ""
                content += f"- [[{entity.name}]]{chapter_info}\n"
            content += "\n"

        # 输出按类型统计
        content += "---\n\n## 统计\n\n"
        content += "| 类型 | 数量 |\n|---------|---------|\n"
        for entity_type in sorted_types:
            if entity_type == "未分类":
                continue
            count = len(type_groups.get(entity_type, []))
            if count > 0:
                content += f"| {entity_type} | {count} |\n"
        if untyped_entities:
            content += f"| 未分类 | {len(untyped_entities)} |\n"

        index_path = entities_dir / "index.md"
        index_path.write_text(content, encoding="utf-8")

    def _write_relations(self, book: Book, ontology: Ontology, book_dir: Path) -> None:
        """写入关系索引"""
        relations_path = book_dir / "relations.md"

        content = f"""---
type: relations-index
book: {book.title}
---

# 关系网络

> 共 {len(ontology.relations)} 条关系

"""
        for i, relation in enumerate(ontology.relations, 1):
            chapter_info = f" (来源: 第{relation.source_chapter + 1}章)" if relation.source_chapter is not None else ""
            content += f"{i}. [[{relation.source}]] --[{relation.relation_type or '关联'}]--> [[{relation.target}]]{chapter_info}\n"

        content += "\n---\n\n*返回: [[index|书籍首页]]*\n"
        relations_path.write_text(content, encoding="utf-8")

    def _write_events(self, book: Book, ontology: Ontology, book_dir: Path) -> None:
        """写入事件时间线"""
        events_path = book_dir / "events.md"

        sorted_events = sorted(ontology.events, key=lambda e: e.chapter or 0)

        content = f"""---
type: events-index
book: {book.title}
---

# 事件时间线

> 共 {len(ontology.events)} 个重要事件

"""

        for i, event in enumerate(sorted_events, 1):
            chapter_info = f"第{event.chapter + 1}章" if event.chapter is not None else "未知"

            # 事件基本信息
            content += f"### {i}. {event.title}\n\n"
            content += f"- **章节**: {chapter_info}\n"

            if event.location:
                content += f"- **地点**: {event.location}\n"

            # 人物格式: [[人物1、人物2、人物3]]
            if event.participants:
                participants_str = "、".join(event.participants)
                content += f"- **人物**: [[{participants_str}]]\n"

            # 事件格式: 切分 description 为多个 [[子事件]]
            if event.description:
                sub_events = self._split_into_sub_events(event.description)
                if sub_events:
                    events_str = "]], [[".join(sub_events) if len(sub_events) > 1 else sub_events[0]
                    if len(sub_events) > 1:
                        content += f"- **事件**: [[{events_str}]]\n"
                    else:
                        content += f"- **事件**: [[{events_str}]]\n"

            content += "\n---\n\n"

        content += "*返回: [[index|书籍首页]]*\n"
        events_path.write_text(content, encoding="utf-8")

    def _split_into_sub_events(self, description: str) -> list[str]:
        """将事件描述切分为多个子事件
        
        切分策略：
        1. 按句号、逗号等标点切分
        2. 过滤过短的片段（<5字符）
        3. 过滤纯空白片段
        4. 返回非空片段列表
        """
        # 移除多余空白
        desc = description.strip()
        if not desc:
            return []

        # 按常见分隔符切分：句号、逗号、分号
        # 使用正则匹配句子结束标记
        import re
        # 按句子分隔（。！？）或明显的逗号分隔（，）
        # 先按句子切分
        sentences = re.split(r'[。！？；]', desc)
        
        sub_events = []
        for sentence in sentences:
            sentence = sentence.strip()
            # 过滤过短或无意义的片段
            if len(sentence) >= 5 and not self._is_meaningless(sentence):
                sub_events.append(sentence)
        
        # 如果按句子切分后片段太少（只有1个），尝试按逗号再切分
        if len(sub_events) <= 1 and len(sentences) > 1:
            # 按逗号切分（但保留较长的片段）
            parts = re.split(r'[，,]', desc)
            sub_events = []
            for part in parts:
                part = part.strip()
                if len(part) >= 8 and not self._is_meaningless(part):
                    sub_events.append(part)
        
        return sub_events

    def _is_meaningless(self, text: str) -> bool:
        """检查文本是否无意义（纯停用词等）"""
        meaningless_patterns = [
            r'^[,，.。;；:：\s]+$',  # 只有标点或空白
            r'^的$', r'^了$', r'^是$', r'^在$',  # 单独的字
            r'^无$', r'^未知$',  # 无意义的词
        ]
        import re
        for pattern in meaningless_patterns:
            if re.match(pattern, text):
                return True
        return False

    def _write_concepts(self, book: Book, ontology: Ontology, book_dir: Path) -> None:
        """写入概念分析"""
        concepts_path = book_dir / "concepts.md"

        content = f"""---
type: concepts-index
book: {book.title}
---

# 核心概念

> 共 {len(ontology.concepts)} 个核心概念

"""
        for concept in ontology.concepts:
            content += f"- [[{concept}]]\n"

        content += "\n---\n\n*返回: [[index|书籍首页]]*\n"
        concepts_path.write_text(content, encoding="utf-8")

    def _write_themes(self, book: Book, ontology: Ontology, book_dir: Path) -> None:
        """写入主题分析"""
        themes_path = book_dir / "themes.md"

        content = f"""---
type: themes-index
book: {book.title}
---

# 主题分析

> 共 {len(ontology.themes)} 个核心主题

"""

        for theme in ontology.themes:
            content += f"- [[{theme}]]\n"

        if not ontology.themes:
            content += "（暂无主题信息）\n"

        content += "\n---\n\n*返回: [[index|书籍首页]]*\n"""
        themes_path.write_text(content, encoding="utf-8")
