"""
核心数据类型定义

基于本体论的数据模型：
- Entity: 任何存在的事物
- Relation: 实体之间的关系
- Event: 重要事件
- Ontology: 完整的知识本体
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class BookFormat(str, Enum):
    """支持的电子书格式"""

    EPUB = "epub"
    PDF = "pdf"
    TXT = "txt"
    MOBI = "mobi"


class Book(BaseModel):
    """书籍数据模型"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    title: str
    author: Optional[str] = None
    format: BookFormat
    chapters: list["Chapter"] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    @property
    def total_chars(self) -> int:
        """总字符数"""
        return sum(len(ch.content) for ch in self.chapters)

    @property
    def total_words(self) -> int:
        """总词数（估算）"""
        return sum(ch.word_count for ch in self.chapters)


class Chapter(BaseModel):
    """章节数据模型"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    index: int
    title: Optional[str] = None
    content: str = ""
    char_count: int = 0
    word_count: int = 0

    def __init__(self, **data):
        """自动计算字符数和词数"""
        super().__init__(**data)
        if self.content:
            if self.char_count == 0:
                self.char_count = len(self.content)
            if self.word_count == 0:
                self.word_count = len(self.content) // 2


class Entity(BaseModel):
    """实体数据模型"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    entity_type: Optional[str] = None
    description: Optional[str] = None
    aliases: list[str] = Field(default_factory=list)
    first_chapter: Optional[int] = None
    properties: dict = Field(default_factory=dict)
    source_chapter: Optional[int] = None

    def to_wiki_link(self) -> str:
        """转换为 Obsidian 双向链接格式"""
        return f"[[{self.name}]]"


class Relation(BaseModel):
    """关系数据模型"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    source: str
    target: str
    relation_type: Optional[str] = None
    description: Optional[str] = None
    source_chapter: Optional[int] = None
    bidirectional: bool = False

    def to_wiki_format(self) -> str:
        """转换为 Obsidian 格式"""
        rel_desc = self.relation_type or "关联"
        base = f"[[{self.source}]] --[{rel_desc}]--> [[{self.target}]]"
        if self.bidirectional:
            return f"{base} (双向)"
        return base


class Event(BaseModel):
    """事件数据模型"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    title: str
    description: Optional[str] = None
    participants: list[str] = Field(default_factory=list)
    chapter: Optional[int] = None
    significance: Optional[str] = None
    location: Optional[str] = None

    def to_wiki_format(self) -> str:
        """转换为 Wiki 格式"""
        parts = ", ".join(f"[[{p}]]" for p in self.participants)
        loc = f"，发生于[[{self.location}]]" if self.location else ""
        return f"- **{self.title}**（{parts}]{loc}"


class Ontology(BaseModel):
    """知识本体模型"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    book_id: str
    book_title: str
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def add_entity(self, entity: Entity) -> None:
        """添加实体（去重）"""
        if not any(e.name == entity.name for e in self.entities):
            self.entities.append(entity)
            self.updated_at = datetime.now()

    def add_relation(self, relation: Relation) -> None:
        """添加关系"""
        self.relations.append(relation)
        self.updated_at = datetime.now()

    def add_event(self, event: Event) -> None:
        """添加事件"""
        self.events.append(event)
        self.updated_at = datetime.now()

    def merge(self, other: "Ontology") -> None:
        """合并另一个本体"""
        for entity in other.entities:
            self.add_entity(entity)
        for relation in other.relations:
            self.add_relation(relation)
        for event in other.events:
            if not any(e.title == event.title for e in self.events):
                self.add_event(event)
        for concept in other.concepts:
            if concept not in self.concepts:
                self.concepts.append(concept)
        for theme in other.themes:
            if theme not in self.themes:
                self.themes.append(theme)
        self.updated_at = datetime.now()

    def to_history_context(self) -> str:
        """转换为历史上下文字符串"""
        lines = []
        if self.entities:
            lines.append("### 已知实体:")
            for e in self.entities[-10:]:
                lines.append(f"- [[{e.name}]] ({e.entity_type or '未知'})")
        if self.relations:
            lines.append("\n### 已知关系:")
            for r in self.relations[-10:]:
                lines.append(f"- [[{r.source}]] --[{r.relation_type or '关联'}]--> [[{r.target}]]")
        if self.events:
            lines.append("\n### 已知事件:")
            for e in self.events[-5:]:
                lines.append(f"- {e.title}")
        return "\n".join(lines) if lines else "暂无历史信息"


class ProcessingResult(BaseModel):
    """处理结果模型"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    book_id: str
    book_title: str
    ontology: Ontology
    wiki_path: Optional[str] = None
    yaml_path: Optional[str] = None
    processing_time: float = 0.0
    chapters_processed: int = 0
    success: bool = True
    error_message: Optional[str] = None
