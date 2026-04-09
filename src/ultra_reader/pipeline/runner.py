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

        # 生成书籍摘要
        summary = await self._generate_book_summary(book, ontology)
        ontology.summary = summary

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
✓ 敢于创造性地发现非显而易见的实体和关系
✓ 只提取**小说正文**中的内容，不要提取出版信息、版权声明、ISBN 等元数据
✓ 事件描述要详细、专业，包含时间、地点、人物、起因、经过、结果等要素

排除内容（不要提取以下信息）：
- 出版社名称、出版日期、ISBN、版权声明
- 作者简介、译者简介、序言、前言（除非是正文的一部分）
- 目录页、封面信息
- 任何与故事正文无关的元数据"""

    def _get_extraction_user_prompt(self) -> str:
        """获取提取 User Prompt 模板 - 详细版"""
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

列出这个章节中出现的**任何重要存在**，使用 [[双向链接]] 格式，并标注类型。

**格式要求**：每行一个实体，格式为 `[[实体名]] (类型)`，例如：
- [[杨玉环]] (人物)
- [[长安城]] (地点)
- [[霓裳羽衣曲]] (物品)
- [[开元之治]] (概念)

**类型分类**：
- **人物**：主角、配角、历史人物、侍女、官员等
- **地点**：宫殿、城市、山川河流、室内场景、具体建筑等
- **组织**：朝廷、军队、党派、帮派、家族等
- **物品**：重要器物、信物、服饰、武器、音乐舞蹈、食物等
- **概念**：政治理念、哲学思想、情感主题、历史事件名称、制度等
- **时间**：具体年代、季节、历史时期（如"开元二十八年"）

**示例**：
[[唐玄宗李隆基]] (人物)
[[骊山温泉宫]] (地点)
[[寿王府]] (地点)
[[霓裳羽衣曲]] (物品)
[[后宫制度]] (概念)
[[开元二十八年]] (时间)

### 二、关系网络

描述这些存在之间的**具体关系**，用自然语言描述。

格式：[[实体A]] --[关系描述]--> [[实体B]]

注意：关系描述要具体，不要泛泛而谈。例如：
- [[唐玄宗]] --[召见并宠幸]--> [[杨玉环]]
- [[杨玉环]] --[被迫离开]--> [[寿王府]]
- [[李林甫]] --[陷害]--> [[太子瑛]]

### 三、重要事件

**重要**：每个事件必须包含详细的描述性陈述，不能只是简单的名称！

格式（使用表格，必须严格按照此列顺序，共5列）：

```
| 事件名称 | 发生时间 | 发生地点 | 主要人物 | 详细描述 |
|---------|---------|---------|---------|---------|
| 事件1 | 时间1 | 地点1 | 人物1、人物2 | 描述1... |
| 事件2 | 时间2 | 地点2 | 人物3、人物4 | 描述2... |
```

**【关键】各列说明**：
- **第1列（事件名称）**：描述性短语，2-10个字，如"武则天称帝改周"、"骊山温泉宫召见"
  - ❌ 禁止只用时间词：如"开元二十八年十月"、"公元690年"
  - ✅ 必须包含动作或事件内容
- **第2列（发生时间）**：时间描述，如"开元二十八年十月"、"天宝四年七月"
  - ❌ 禁止填地点
- **第3列（发生地点）**：地点描述，如"骊山温泉宫"、"长安大明宫"
  - ❌ 禁止填人物
- **第4列（主要人物）**：人物列表，用顿号分隔，如"唐玄宗、杨玉环、高力士"
  - ❌ 禁止填事件描述
- **第5列（详细描述）**：事件详细描述，至少2-3句话

**错误示例**：
```
| 开元二十八年十月 | 骊山温泉宫 | 唐玄宗、杨玉环 | ... |  ← 错误！第1列是时间，不是事件名
```
```
| 武则天称帝 | 唐玄宗 | 长安 | 武则天废睿宗... |  ← 错误！第2列填了人物，第3列填了地点
```

**正确示例**：
```
| 武则天称帝改周 | 公元690年 | 长安 | 武则天、睿宗李旦 | 武则天废睿宗，自己即帝位，改国号为周，变年号为天授... |
```

### 四、核心概念

列出这个章节讨论的**核心概念**，以及它们之间的关系。

格式：
- [[概念名称]]：对这个概念的简要解释（1-2句话）
- [[概念A]] --[关联]--> [[概念B]]（概念之间的关系）

**要求**：
- 概念要深刻，不是简单的事物名称
- 要提炼出抽象的思想、情感、制度等
- 至少提取3-5个核心概念

### 五、主题提炼

分析这一章节的**核心主题**，提炼2-3个最重要的人文主题。

格式：
- [[主题名称]]：对这个主题的阐释（2-3句话）

**示例主题**：
- [[命运的无奈]]：个人的命运往往被权力和制度所左右
- [[爱情与权力]]：在封建社会，爱情常常成为政治的牺牲品
- [[女性的困境]]：古代女性的命运掌握在男性手中

### 六、章节摘要

用一段话（100-200字）概括这一章的核心内容，包括主要情节、人物关系变化、主题呈现等。"""

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
            elif line.startswith("### 五") or "主题提炼" in line:
                # 解析之前收集的概念
                if current_section == "concepts" and current_content:
                    self._parse_concepts(current_content, ontology, chapter_index)
                current_section = "themes"
                current_content = []
                continue
            elif line.startswith("### 六") or "章节摘要" in line:
                # 解析之前收集的主题
                if current_section == "themes" and current_content:
                    self._parse_themes(current_content, ontology, chapter_index)
                elif current_section == "concepts" and current_content:
                    self._parse_concepts(current_content, ontology, chapter_index)
                current_section = "summary"
                current_content = []
                continue

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
            # 表格格式解析 - 提取详细事件信息
            self._parse_events_table(lines, ontology, chapter_index)
        else:
            # 列表格式解析
            self._parse_events_list(lines, ontology, chapter_index)

    def _parse_events_table(self, lines: list[str], ontology: Ontology, chapter_index: int) -> None:
        """解析表格格式的事件"""
        import re

        for line in lines:
            line = line.strip()
            # 跳过空行和分隔符行
            if not line or line.startswith('|---') or line.startswith('---'):
                continue
            # 跳过表头行
            if '事件名称' in line or ('事件' in line and '主要人物' in line):
                continue
            if '|' not in line:
                continue

            parts = [p.strip() for p in line.split('|')]

            # 过滤掉空的部分和分隔符
            parts = [p for p in parts if p and p != '---' and p.strip()]

            if len(parts) < 4:
                continue

            # 表格格式（可能有4列或5列）:
            # | 事件名称 | 发生时间 | 发生地点 | 主要人物 | 详细描述(可选) |
            # 过滤后的 parts: ["事件名称", "发生时间", "发生地点", "主要人物"] 或
            #                 ["事件名称", "发生时间", "发生地点", "主要人物", "详细描述"]
            # 注意：LLM 可能只返回4列（缺详细描述）

            # 检查是否是表头
            col_headers = [p for p in parts if '事件' in p or '时间' in p or '地点' in p or '人物' in p or '描述' in p]
            if len(col_headers) >= 3:  # 3个以上的表头词说明是表头行
                continue

            # 提取各字段
            event_name = parts[0] if len(parts) > 0 else ''  # 第1列: 事件名称
            time = parts[1] if len(parts) > 1 else None      # 第2列: 发生时间
            location = parts[2] if len(parts) > 2 else None  # 第3列: 发生地点
            participants_str = parts[3] if len(parts) > 3 else ''  # 第4列: 主要人物
            description = parts[4] if len(parts) > 4 else None      # 第5列(可选): 详细描述

            # 解析主要人物（可能是逗号分隔的列表）
            participants = []
            if participants_str:
                # 分割人物列表，并提取 [[]] 中的内容
                for p in re.split(r'[,，、/]', participants_str):
                    p = p.strip()
                    # 提取 [[]] 中的内容
                    match = re.search(r'\[\[([^\]]+)\]\]', p)
                    if match:
                        participants.append(match.group(1))
                    elif p and len(p) < 20:  # 简单的人名
                        participants.append(p)

            # 清理描述中的 Markdown 格式
            if description:
                description = description.strip()
                description = re.sub(r'\*+([^*]+)\*+', r'\1', description)

            event = Event(
                title=event_name.strip(),
                time=time.strip() if time else None,
                location=location.strip() if location else None,
                participants=participants,
                description=description.strip() if description else None,
                chapter=chapter_index,
            )
            ontology.add_event(event)

    def _parse_events_list(self, lines: list[str], ontology: Ontology, chapter_index: int) -> None:
        """解析列表格式的事件"""
        import re

        for line in lines:
            line = line.strip()
            if not line or line.startswith('---') or line.startswith('**'):
                continue

            # 尝试解析包含详细信息的列表项
            # 格式: - 事件名: 描述
            # 或: - 事件名（时间/地点/人物）- 描述

            list_match = re.match(r'^[-\*\d\.]+\s*(.+)?', line)
            if list_match:
                content = list_match.group(1) or ''
                event_name = re.sub(r'\*+', '', content).strip()
                if event_name and len(event_name) > 2:
                    # 尝试提取描述（: 或 — 后面的内容）
                    desc_match = re.search(r'[:：—–-]\s*(.+)$', event_name)
                    description = None
                    clean_name = event_name

                    if desc_match:
                        description = desc_match.group(1).strip()
                        clean_name = event_name[:desc_match.start()].strip()

                    # 尝试提取时间（括号中的内容）
                    time = None
                    location = None
                    time_match = re.search(r'[(（]([^)）]+)[)）]', clean_name)
                    if time_match:
                        potential_time = time_match.group(1)
                        # 判断是否是时间
                        if any(kw in potential_time for kw in ['年', '月', '日', '时', '朝', '代', '世纪']):
                            time = potential_time
                            clean_name = clean_name[:time_match.start()] + clean_name[time_match.end():]

                    event = Event(
                        title=clean_name.strip(),
                        description=description,
                        time=time,
                        location=location,
                        chapter=chapter_index,
                    )
                    ontology.add_event(event)

    def _parse_concepts(self, lines: list[str], ontology: Ontology, chapter_index: int) -> None:
        """解析核心概念"""
        import re

        for line in lines:
            line = line.strip()
            if not line or line.startswith('---') or line.startswith('**'):
                continue

            # 尝试匹配格式: [[概念名]]：描述 或 [[概念A]] --[关联]--> [[概念B]]
            match = re.search(r'\[\[([^\]]+)\]\]', line)
            if match:
                concept_name = match.group(1)
                # 跳过关联关系（带 --> 的行）
                if '-->' in line:
                    continue
                # 提取概念名称（去掉冒号后的描述部分）
                if '：' in line or ':' in line:
                    concept_part = line.split('：')[0] if '：' in line else line.split(':')[0]
                    name_match = re.search(r'\[\[([^\]]+)\]\]', concept_part)
                    if name_match:
                        concept_name = name_match.group(1)
                
                # 添加到概念列表（去重）
                if concept_name and concept_name not in ontology.concepts:
                    ontology.concepts.append(concept_name)

    def _parse_themes(self, lines: list[str], ontology: Ontology, chapter_index: int) -> None:
        """解析主题提炼"""
        import re

        for line in lines:
            line = line.strip()
            if not line or line.startswith('---') or line.startswith('**'):
                continue

            # 尝试匹配格式: [[主题名]]：描述
            match = re.search(r'\[\[([^\]]+)\]\]', line)
            if match:
                theme_name = match.group(1)
                # 添加到主题列表（去重）
                if theme_name and theme_name not in ontology.themes:
                    ontology.themes.append(theme_name)

    async def _generate_book_summary(self, book: Book, ontology: Ontology) -> str:
        """生成书籍摘要"""
        from ultra_reader.prompts.summary import SummaryPrompts

        prompt = SummaryPrompts.book_summary(
            book_title=book.title,
            entities=[e.name for e in ontology.entities],
            relations=[r.to_wiki_format() for r in ontology.relations],
            events=[e.title for e in ontology.events],
            concepts=ontology.concepts,
        )

        messages = [
            {"role": "user", "content": prompt},
        ]

        response = await self.llm.chat(messages)
        return self._parse_summary(response)

    def _parse_summary(self, response: str) -> str:
        """从 LLM 响应中提取摘要文本"""
        lines = response.strip().split("\n")
        summary_lines = []

        for line in lines:
            line = line.strip()
            # 跳过标题行和空行
            if not line:
                continue
            if line.startswith("#") or line.startswith("##"):
                continue
            # 去掉可能的列表前缀
            line = line.lstrip("-*123456789.、 ")
            if line:
                summary_lines.append(line)

        summary = " ".join(summary_lines).strip()
        # 如果结果为空，尝试直接返回清理后的响应前500字
        if not summary:
            summary = response.strip()[:500]
        return summary
