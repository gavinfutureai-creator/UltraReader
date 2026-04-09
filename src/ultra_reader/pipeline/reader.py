"""
电子书读取器

支持 EPUB 格式的电子书读取
"""

import re
import warnings
from pathlib import Path
from typing import Optional

from ultra_reader.core.exceptions import EbookFormatError, EbookParseError
from ultra_reader.core.types import Book, BookFormat, Chapter

# 忽略 XML 解析警告
warnings.filterwarnings("ignore", category=RuntimeWarning)


class EPUBReader:
    """EPUB 格式读取器"""

    def supports(self, path: Path | str) -> bool:
        """检查是否支持此文件"""
        path = Path(path)
        return path.suffix.lower() == ".epub"

    def read(self, path: Path | str) -> Book:
        """读取 EPUB 文件"""
        path = Path(path)

        if not path.exists():
            raise EbookFormatError(f"文件不存在: {path}")

        if not self.supports(path):
            raise EbookFormatError(f"不支持的格式: {path.suffix}")

        try:
            from ebooklib import epub

            book_epub = epub.read_epub(str(path))

            title = self._get_metadata(book_epub, "title") or path.stem
            author = self._get_metadata(book_epub, "creator")

            chapters = self._extract_chapters(book_epub)

            import hashlib
            title_bytes = title.encode("utf-8")
            hash_obj = hashlib.md5(title_bytes)
            book_id = hash_obj.hexdigest()[:12]

            return Book(
                id=book_id,
                title=title,
                author=author,
                format=BookFormat.EPUB,
                chapters=chapters,
                metadata={
                    "file_path": str(path),
                    "file_size": path.stat().st_size,
                },
            )

        except Exception as e:
            raise EbookParseError(f"解析 EPUB 失败: {e}") from e

    def _get_metadata(self, book, key: str) -> Optional[str]:
        """获取元数据"""
        namespace = "http://purl.org/dc/elements/1.1/"

        try:
            meta = book.get_metadata(namespace, key)
            for item in meta:
                if item and item[0]:
                    return item[0]
        except (TypeError, AttributeError):
            pass

        try:
            meta = book.get_metadata()
            for item in meta.get(key, []):
                if item and item[0]:
                    return item[0]
        except Exception:
            pass

        return None

    def _extract_chapters(self, book) -> list[Chapter]:
        """
        提取章节。

        关键：按 spine 定义的顺序遍历，确保章节顺序正确。
        spine 按阅读顺序列出文档 ID，与 get_items() 的任意顺序不同。
        """
        chapters = []

        # 获取 spine 定义的阅读顺序
        spine_items = []
        try:
            # spine 是一个 (item_id, linear) 元组列表
            for item_id, linear in book.spine:
                item = book.get_item_with_id(item_id)
                if item and item.get_type() == 9:  # EPUB2 HTML type
                    spine_items.append(item)
        except Exception:
            # fallback: 降级为 get_items()
            spine_items = [item for item in book.get_items() if item.get_type() == 9]

        for item in spine_items:
            content = item.get_content()
            text = self._html_to_text(content)

            # 跳过纯元数据页（版权、出版信息）
            if self._is_metadata_page(text, item):
                continue

            # 跳过内容过少的页面（很可能是空白页或分割符页）
            if not text or len(text.strip()) < 200:
                continue

            title = self._extract_title(content) or f"第 {len(chapters) + 1} 章"

            chapters.append(
                Chapter(
                    index=len(chapters),
                    title=title,
                    content=text,
                )
            )

        return chapters

    def _is_metadata_page(self, text: str, item) -> bool:
        """
        判断是否为元数据页（版权页、出版信息页等）
        """
        if not text:
            return False

        text_lower = text.lower()
        item_name = item.get_name().lower() if item else ""

        # 元数据文件名关键词
        metadata_filenames = [
            "copyright", "colophon", "imprint", "titlepage",
            "cover", "coverpage",
        ]
        for pattern in metadata_filenames:
            if pattern in item_name:
                return True

        # 元数据内容关键词（命中多个 = 版权/出版页）
        metadata_keywords = [
            "版权", "copyright", "reserved", "著作权",
            "publisher", "publication", "发行", "发行者",
            "isbn", "书号", "版号", "cip",
            "定价", "定价:", "售价",
            "版权所有", "未经许可", "不得翻印",
            "浙江出版", "数字化", "ebook",
        ]
        keyword_count = sum(1 for kw in metadata_keywords if kw in text_lower)

        # 命中 3 个以上关键词，且内容少于 2000 字 → 版权/出版页
        if keyword_count >= 3 and len(text.strip()) < 2000:
            return True

        # 检查是否是纯版权声明
        lines = text.strip().split("\n")
        copyright_indicators = ["©", "copyright", "版权", "reserved", "许可"]
        if len(lines) > 5:
            copyright_lines = sum(
                1 for line in lines if any(ind in line.lower() for ind in copyright_indicators)
            )
            if copyright_lines >= 2 and len(text) < 1500:
                return True

        return False

    def _html_to_text(self, html: bytes | str) -> str:
        """HTML 转纯文本"""
        try:
            from bs4 import BeautifulSoup

            if isinstance(html, bytes):
                html = html.decode("utf-8", errors="ignore")

            soup = BeautifulSoup(html, "lxml")

            for tag in soup(["script", "style", "nav"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            text = re.sub(r"\n{3,}", "\n\n", text)
            return text.strip()

        except ImportError:
            if isinstance(html, bytes):
                html = html.decode("utf-8", errors="ignore")

            html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

            text = re.sub(r"<[^>]+>", "", html)
            text = re.sub(r"\s+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text)

            return text.strip()

    def _extract_title(self, html: bytes | str) -> Optional[str]:
        """从 HTML 中提取标题"""
        try:
            from bs4 import BeautifulSoup

            if isinstance(html, bytes):
                html = html.decode("utf-8", errors="ignore")

            soup = BeautifulSoup(html, "lxml")

            for tag in ["h1", "h2", "title"]:
                element = soup.find(tag)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) < 200:
                        return text

            return None

        except ImportError:
            if isinstance(html, bytes):
                html = html.decode("utf-8", errors="ignore")

            match = re.search(r"<title>([^<]+)</title>", html)
            if match:
                return match.group(1).strip()

            return None
