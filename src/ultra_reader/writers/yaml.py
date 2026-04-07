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

        # 按类型分组实体
        type_groups: dict[str, list] = {}
        untyped_entities: list = []

        for e in ontology.entities:
            entity_dict = clean_dict({
                "name": e.name,
                "type": e.entity_type,
                "description": e.description,
                "aliases": e.aliases if e.aliases else None,
                "source_chapter": e.source_chapter + 1 if e.source_chapter is not None else None,
            })
            if e.entity_type:
                if e.entity_type not in type_groups:
                    type_groups[e.entity_type] = []
                type_groups[e.entity_type].append(entity_dict)
            else:
                untyped_entities.append(entity_dict)

        # 按定义的顺序排列类型
        TYPE_ORDER = ["人物", "地点", "组织", "物品", "概念", "时间"]
        sorted_types = sorted(type_groups.keys(), key=lambda t: TYPE_ORDER.index(t) if t in TYPE_ORDER else 999)

        # 构建带分类的实体结构
        typed_entities = []
        for entity_type in sorted_types:
            if type_groups[entity_type]:
                typed_entities.append({
                    "category": entity_type,
                    "items": type_groups[entity_type]
                })
        if untyped_entities:
            typed_entities.append({
                "category": "未分类",
                "items": untyped_entities
            })

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
                "time": e.time,
                "location": e.location,
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
            "entities": {
                "total": len(ontology.entities),
                "by_category": typed_entities,
            },
            "relations": relations,
            "events": events,
            "concepts": ontology.concepts if ontology.concepts else None,
        }
