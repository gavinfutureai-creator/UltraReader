"""YAML 格式写入器"""

from pathlib import Path
from datetime import datetime

from ultra_reader.core.types import Book, Ontology
from ultra_reader.writers.base import BaseWriter


class YAMLWriter(BaseWriter):
    """YAML 格式写入器"""

    def __init__(self, output_dir: str | Path = "output"):
        super().__init__(output_dir)

    def write(self, book: Book, ontology: Ontology) -> Path:
        """写入 YAML 文件"""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        safe_title = self._sanitize_filename(book.title)
        yaml_path = self.output_dir / f"{safe_title}.yaml"

        data = self._build_yaml_data(book, ontology)

        import yaml
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, width=120)

        return yaml_path

    def _build_yaml_data(self, book: Book, ontology: Ontology) -> dict:
        """构建 YAML 数据结构"""
        def clean_dict(d: dict) -> dict:
            return {k: v for k, v in d.items() if v is not None and v != []}

        entities = [
            clean_dict({
                "name": e.name,
                "type": e.entity_type,
                "description": e.description,
                "aliases": e.aliases if e.aliases else None,
                "source_chapter": e.source_chapter + 1 if e.source_chapter is not None else None,
            })
            for e in ontology.entities
        ]

        relations = [
            clean_dict({
                "source": r.source,
                "target": r.target,
                "type": r.relation_type,
                "description": r.description,
                "source_chapter": r.source_chapter + 1 if r.source_chapter is not None else None,
            })
            for r in ontology.relations
        ]

        events = [
            clean_dict({
                "title": e.title,
                "description": e.description,
                "participants": e.participants if e.participants else None,
                "chapter": e.chapter + 1 if e.chapter is not None else None,
            })
            for e in ontology.events
        ]

        return {
            "book": {
                "title": book.title,
                "author": book.author,
                "format": book.format.value,
                "total_chapters": len(book.chapters),
                "total_chars": book.total_chars,
            },
            "entities": entities,
            "relations": relations,
            "events": events,
            "concepts": ontology.concepts if ontology.concepts else None,
        }
