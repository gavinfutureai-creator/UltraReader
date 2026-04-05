"""
处理流程编排器

核心流程：
1. 读取电子书 → Book 对象
2. 调用 LLM → Ontology 对象
3. 写入 Wiki/YAML → 文件
"""

import time
from pathlib import Path

from ultra_reader.core.config import Config
from ultra_reader.core.exceptions import ProcessingError
from ultra_reader.core.types import Book, Ontology, ProcessingResult, Entity, Relation, Event
from ultra_reader.llm.base import BaseLLM
from ultra_reader.pipeline.reader import EPUBReader
from ultra_reader.writers.wiki import WikiWriter
from ultra_reader.writers.yaml import YAMLWriter


class PipelineRunner:
    """处理流程编排器"""

    def __init__(
        self,
        llm: BaseLLM,
        config: Config | None = None,
        reader: EPUBReader | None = None,
    ):
        self.llm = llm
        self.config = config or Config()
        self.reader = reader or EPUBReader()
        self.wiki_writer = WikiWriter(output_dir=self.config.output.wiki_dir)
        self.yaml_writer = YAMLWriter(output_dir=self.config.output.output_dir)

    async def process(
        self,
        input_path: Path | str,
        output_dir: Path | str | None = None,
    ) -> ProcessingResult:
        """处理一本书"""
        start_time = time.time()
        input_path = Path(input_path)

        if output_dir:
            output_dir = Path(output_dir)
            self.wiki_writer.output_dir = str(output_dir / self.config.output.wiki_dir)
            self.yaml_writer.output_dir = str(output_dir / self.config.output.output_dir)

        try:
            book = self.reader.read(input_path)
            ontology = await self._build_ontology(book)
            wiki_path = self.wiki_writer.write(book, ontology)
            yaml_path = self.yaml_writer.write(book, ontology)

            processing_time = time.time() - start_time

            return ProcessingResult(
                book_id=book.id,
                book_title=book.title,
                ontology=ontology,
                wiki_path=str(wiki_path),
                yaml_path=str(yaml_path),
                processing_time=processing_time,
                chapters_processed=len(book.chapters),
                success=True,
            )

        except Exception as e:
            return ProcessingResult(
                book_id="",
                book_title=input_path.stem,
                ontology=Ontology(book_id="", book_title=input_path.stem),
                processing_time=time.time() - start_time,
                success=False,
                error_message=str(e),
            )

    async def _build_ontology(self, book: Book) -> Ontology:
        """构建知识本体"""
        ontology = Ontology(
            book_id=book.id,
            book_title=book.title,
        )

        prompt_system = self._get_extraction_system_prompt()
        prompt_user_template = self._get_extraction_user_prompt()

        history_context = ""

        for chapter in book.chapters:
            prompt_user = prompt_user_template.format(
                book_title=book.title,
                author=book.author or "未知",
                chapter_index=chapter.index + 1,
                chapter_title=chapter.title or f"第 {chapter.index + 1} 章",
                history_context=history_context,
                chapter_content=chapter.content[:50000],
            )

            messages = [
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user},
            ]

            response = await self.llm.chat(messages)

            chapter_ontology = self._parse_llm_response(response, chapter.index)
            ontology.merge(chapter_ontology)

            history_context = ontology.to_history_context()

        return ontology

    def _get_extraction_system_prompt(self) -> str:
        """获取提取 System Prompt"""
        return """你是一个本体论知识工程师，负责从书籍章节中构建知识本体。

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

    def _get_extraction_user_prompt(self) -> str:
        """获取提取 User Prompt 模板"""
        return """## 书名: {book_title}
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

    def _parse_llm_response(self, response: str, chapter_index: int) -> Ontology:
        """解析 LLM 响应"""
        ontology = Ontology(book_id="", book_title="")

        lines = response.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            line = line.strip()

            # 检测章节标题
            if line.startswith("### 一") or "存在的事物" in line:
                current_section = "entities"
                current_content = []
                continue
            elif line.startswith("### 二") or "关系网络" in line:
                # 解析之前收集的实体
                if current_section == "entities" and current_content:
                    self._parse_entities(current_content, ontology, chapter_index)
                current_section = "relations"
                current_content = []
                continue
            elif line.startswith("### 三") or "重要事件" in line:
                # 解析之前收集的关系
                if current_section == "relations" and current_content:
                    self._parse_relations(current_content, ontology, chapter_index)
                current_section = "events"
                current_content = []
                continue
            elif line.startswith("### 四") or "核心概念" in line:
                # 解析之前收集的事件
                if current_section == "events" and current_content:
                    self._parse_events(current_content, ontology, chapter_index)
                current_section = "concepts"
                current_content = []
                continue
            elif line.startswith("### 五") or "章节摘要" in line:
                # 解析之前收集的内容
                if current_section == "events" and current_content:
                    self._parse_events(current_content, ontology, chapter_index)
                elif current_section == "concepts" and current_content:
                    pass  # 核心概念暂不单独解析
                ontology.summary = "\n".join(current_content)
                break

            # 收集内容行
            if line and current_section:
                current_content.append(line)

        # 处理最后剩余的内容
        if current_content:
            if current_section == "entities":
                self._parse_entities(current_content, ontology, chapter_index)
            elif current_section == "relations":
                self._parse_relations(current_content, ontology, chapter_index)
            elif current_section == "events":
                self._parse_events(current_content, ontology, chapter_index)

        return ontology


    def _parse_entities(self, lines: list[str], ontology: Ontology, chapter_index: int) -> None:
        """解析实体"""
        import re

        for line in lines:
            matches = re.findall(r"\[\[([^\]]+)\]\]", line)
            for name in matches:
                entity_type = None
                if "(" in line and ")" in line:
                    type_match = re.search(r"\(([^)]+)\)", line)
                    if type_match:
                        entity_type = type_match.group(1).strip()

                entity = Entity(
                    name=name,
                    entity_type=entity_type,
                    source_chapter=chapter_index,
                )
                ontology.add_entity(entity)

    def _parse_relations(self, lines: list[str], ontology: Ontology, chapter_index: int) -> None:
        """解析关系"""
        import re

        for line in lines:
            # 去掉可能的列表前缀 (-, *, 数字., 等)
            cleaned_line = re.sub(r'^[\s\-\*\d\.]+', '', line).strip()
            
            # 支持格式: [[A]] --[关系]--> [[B]]
            match = re.search(
                r"\[\[([^\]]+)\]\]\s*--\[([^\]]+)\]-->\s*\[\[([^\]]+)\]\]",
                cleaned_line,
            )
            if match:
                source, relation_type, target = match.groups()
                relation = Relation(
                    source=source.strip(),
                    target=target.strip(),
                    relation_type=relation_type.strip(),
                    source_chapter=chapter_index,
                )
                ontology.add_relation(relation)
    def _parse_events(self, lines: list[str], ontology: Ontology, chapter_index: int) -> None:
        """解析事件 - 支持表格和列表格式"""
        import re
        
        # 检查是否是表格格式 (包含 | 符号)
        is_table = any('|' in line for line in lines)
        
        if is_table:
            # 表格格式解析
            for line in lines:
                line = line.strip()
                # 跳过空行和分隔符行
                if not line or line.startswith('|---') or line.startswith('---'):
                    continue
                # 跳过表头行
                if '事件名称' in line or '事件' in line and '参与者' in line:
                    continue
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    # 表格格式: | 事件名 | 参与者 | 意义 |
                    # parts[0] 通常是空的，parts[1] 是事件名
                    if len(parts) >= 2:
                        event_name = parts[1] if len(parts) > 1 else ''
                        if event_name and '参与者' not in event_name:
                            event = Event(
                                title=event_name,
                                chapter=chapter_index,
                            )
                            ontology.add_event(event)
        else:
            # 列表格式解析
            for line in lines:
                line = line.strip()
                if not line or line.startswith('---') or line.startswith('**'):
                    continue
                
                list_match = re.match(r'^[\-\*\d\.]+\s*(.+)?', line)
                if list_match:
                    content = list_match.group(1) or ''
                    event_name = re.sub(r'\*+', '', content).strip()
                    if event_name and len(event_name) > 2:
                        event = Event(
                            title=event_name,
                            chapter=chapter_index,
                        )
                        ontology.add_event(event)
