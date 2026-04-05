"""
JSON 格式写入器

将知识本体输出为结构化的 JSON 格式
"""

import json
from pathlib import Path
from datetime import datetime

from ultra_reader.core.types import Book, Ontology
from ultra_reader.writers.base import BaseWriter


class JSONWriter(BaseWriter):
    """
    JSON 格式写入器

    将知识本体输出为结构化的 JSON 格式，便于程序处理和 API 调用。
    """

    def __init__(self, output_dir: str | Path = "output"):
        super().__init__(output_dir)

    def write(self, book: Book, ontology: Ontology) -> Path:
        """
        写入 JSON 文件

        Args:
            book: 书籍对象
            ontology: 知识本体

        Returns:
            JSON 文件路径
        """
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        safe_title = self._sanitize_filename(book.title)
        json_path = self.output_dir / f"{safe_title}.json"

        # 构建 JSON 数据
        data = self._build_json_data(book, ontology)

        # 写入文件
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
                default=str,
            )

        return json_path

    def _build_json_data(self, book: Book, ontology: Ontology) -> dict:
        """构建 JSON 数据结构"""
        return {
            "meta": {
                "book_id": book.id,
                "title": book.title,
                "author": book.author,
                "processed_at": datetime.now().isoformat(),
                "ultra_reader_version": "0.1.0",
            },
            "book": {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "format": book.format.value,
                "total_chapters": len(book.chapters),
                "total_chars": book.total_chars,
                "total_words": book.total_words,
            },
            "entities": [
                {
                    "name": e.name,
                    "type": e.entity_type,
                    "description": e.description,
                    "aliases": e.aliases,
                    "first_chapter": e.first_chapter,
                    "source_chapter": e.source_chapter + 1 if e.source_chapter is not None else None,
                    "properties": e.properties,
                }
                for e in ontology.entities
            ],
            "relations": [
                {
                    "source": r.source,
                    "target": r.target,
                    "type": r.relation_type,
                    "description": r.description,
                    "source_chapter": r.source_chapter + 1 if r.source_chapter is not None else None,
                    "bidirectional": r.bidirectional,
                }
                for r in ontology.relations
            ],
            "events": [
                {
                    "title": e.title,
                    "description": e.description,
                    "participants": e.participants,
                    "chapter": e.chapter + 1 if e.chapter is not None else None,
                    "significance": e.significance,
                    "location": e.location,
                }
                for e in ontology.events
            ],
            "concepts": ontology.concepts,
            "themes": ontology.themes,
            "summary": ontology.summary,
        }
