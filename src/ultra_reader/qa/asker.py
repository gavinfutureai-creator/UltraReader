"""
Wiki 知识库加载与 Q&A 问答

实现基于 Wiki 知识库的问答功能：
1. 加载已有 Wiki 知识库
2. 编译成 LLM 可读的上下文
3. 基于上下文回答用户问题
"""

from pathlib import Path

from ultra_reader.llm.base import BaseLLM
from ultra_reader.prompts.qa import QAPrompts


class WikiLoader:
    """加载 Wiki 知识库"""

    def __init__(self, wiki_root: str | Path = "wiki"):
        self.wiki_root = Path(wiki_root)

    def list_books(self) -> list[str]:
        """列出所有已处理的书"""
        if not self.wiki_root.exists():
            return []
        return [d.name for d in self.wiki_root.iterdir() if d.is_dir()]

    def load_book(self, book_title: str) -> dict[str, str]:
        """
        加载一本书的所有 Wiki 内容

        Returns:
            dict: 文件名 -> 内容
        """
        book_dir = self.wiki_root / book_title
        if not book_dir.exists():
            raise FileNotFoundError(f"未找到书籍: {book_title}")

        content_map = {}
        for md_file in book_dir.rglob("*.md"):
            rel_path = md_file.relative_to(book_dir)
            content_map[str(rel_path)] = md_file.read_text(encoding="utf-8")

        return content_map

    def compile_context(self, book_title: str, max_chars: int = 30000) -> str:
        """
        将 Wiki 内容编译成 LLM 上下文

        Args:
            book_title: 书名
            max_chars: 最大字符数（防止上下文过长）

        Returns:
            编译后的上下文字符串
        """
        files = self.load_book(book_title)

        sections = []
        total_chars = 0

        # 按信息密度和叙事价值排序
        # events/relations 是叙事核心，优先保证进入上下文
        # entities 是列表形式，信息密度最低，排在最后
        file_order = [
            "events.md",
            "relations.md",
            "concepts.md",
            "themes.md",
            "index.md",
            "entities/index.md",
        ]

        for filename in file_order:
            if filename in files:
                content = files[filename]
                # 去掉 YAML frontmatter
                if content.startswith("---"):
                    end = content.find("\n---\n", 4)
                    if end != -1:
                        content = content[end + 5:]

                if total_chars + len(content) <= max_chars:
                    sections.append(f"### {filename}\n\n{content}")
                    total_chars += len(content)

        return "\n\n".join(sections)


class QAAsker:
    """基于 Wiki 知识库的问答"""

    def __init__(
        self,
        llm: BaseLLM,
        wiki_root: str | Path = "wiki",
    ):
        self.llm = llm
        self.loader = WikiLoader(wiki_root)

    async def ask(
        self,
        book_title: str,
        question: str,
    ) -> str:
        """
        向知识库提问

        Args:
            book_title: 书名
            question: 问题

        Returns:
            LLM 回答
        """
        context = self.loader.compile_context(book_title)

        prompt_user = QAPrompts.user(
            book_title=book_title,
            wiki_content=context,
            question=question,
        )

        messages = [
            {"role": "system", "content": QAPrompts.SYSTEM},
            {"role": "user", "content": prompt_user},
        ]

        return await self.llm.chat(messages)
