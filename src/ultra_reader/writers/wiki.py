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
        book_dir = self.output_dir / self._sanitize_filename(book.title)
        book_dir.mkdir(parents=True, exist_ok=True)

        self._write_index(book, ontology, book_dir)
        self._write_entities(book, ontology, book_dir)
        self._write_relations(book, ontology, book_dir)
        self._write_events(book, ontology, book_dir)
        self._write_concepts(book, ontology, book_dir)

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

        index_path = entities_dir / "index.md"
        content = f"""---
type: entities-index
book: {book.title}
---

# 实体索引

> 共 {len(ontology.entities)} 个实体

"""
        by_type: dict[str, list] = {}
        for entity in ontology.entities:
            entity_type = entity.entity_type or "未分类"
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(entity)

        for entity_type, entities in by_type.items():
            content += f"### {entity_type}\n\n"
            for entity in entities:
                chapter_info = f" (首次出现: 第{entity.source_chapter + 1}章)" if entity.source_chapter is not None else ""
                content += f"- [[{entity.name}]]{chapter_info}\n"
            content += "\n"

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
            content += f"### {i}. {event.title}\n\n- **章节**: {chapter_info}\n\n---\n\n"

        content += "\n*返回: [[index|书籍首页]]*\n"
        events_path.write_text(content, encoding="utf-8")

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
