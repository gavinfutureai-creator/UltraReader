"""
电子书读取器

支持 EPUB 格式的电子书读取
"""

import re
from pathlib import Path
from typing import Optional

from ultra_reader.core.exceptions import EbookFormatError, EbookParseError
from ultra_reader.core.types import Book, BookFormat, Chapter


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
        # 新版本 ebooklib 0.20+ 使用 namespace 和 name 参数
        # 旧版本使用 book.get_metadata() 返回字典
        namespace = "http://purl.org/dc/elements/1.1/"
        
        try:
            # 尝试新 API
            meta = book.get_metadata(namespace, key)
            for item in meta:
                if item and item[0]:
                    return item[0]
        except (TypeError, AttributeError):
            pass
        
        # 尝试旧 API（兼容）
        try:
            meta = book.get_metadata()
            for item in meta.get(key, []):
                if item and item[0]:
                    return item[0]
        except Exception:
            pass
        
        return None

    def _extract_chapters(self, book) -> list[Chapter]:
        """提取章节"""
        chapters = []
        items = list(book.get_items())
        html_items = [item for item in items if item.get_type() == 9]

        for idx, item in enumerate(html_items):
            content = item.get_content()
            text = self._html_to_text(content)

            if not text or len(text.strip()) < 50:
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
