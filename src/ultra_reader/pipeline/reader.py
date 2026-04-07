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

            # 跳过元数据页、版权页等非正文内容
            if self._is_metadata_page(text, item):
                continue

            if not text or len(text.strip()) < 100:
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
        这些页面不应作为正文内容处理
        """
        if not text:
            return False

        text_lower = text.lower()
        item_name = item.get_name().lower() if item else ""

        # 元数据关键词列表
        metadata_keywords = [
            # 版权/出版信息
            "版权", "copyright", "reserved", "著作权", "授权",
            "出版", "出版社", "publisher", "publication",
            "发行", "发行者", "distributor",
            "isbn", "isbn-", "issn", "书号", "版号",
            "cip", "中国图书",
            # 元数据描述
            "出版日期", "出版时间", "印次", "印数", "字数", "开本", "印张",
            "定价", "定价:", "售价",
            # 版权声明常用语
            "版权所有", "未经许可", "不得翻印", "不得转让",
            "all rights reserved", "rights reserved",
            # 封面/扉页信息
            "封面设计", "插图", "摄影", "校对", "装帧",
            # 目录页（如果不需要可以过滤）
            "目录", "contents", "table of contents",
            # 出版商/发行商常见名称
            "浙江出版", "数字化", "电子书", "digital", "ebook",
            "bookdna", "敬告读者", "免责声明",
        ]

        # 检查文件名是否暗示元数据页
        metadata_filenames = [
            "copyright", "colophon", "imprint", "titlepage",
            "toc", "contents", "index",
            "版权", "目录", "出版", "epub",
        ]

        # 检查文件名
        for pattern in metadata_filenames:
            if pattern in item_name:
                # 进一步检查内容长度，太短的可能只是标题
                if len(text.strip()) < 500:
                    return True

        # 检查内容是否包含大量元数据关键词
        keyword_count = sum(1 for kw in metadata_keywords if kw in text_lower)

        # 如果命中多个元数据关键词，且内容较短，大概率是版权页
        if keyword_count >= 3 and len(text.strip()) < 2000:
            return True

        # 检查是否是纯版权声明格式（多行短句）
        lines = text.strip().split('\n')
        copyright_indicators = ['©', 'copyright', '版权', 'reserved', '许可']
        if len(lines) > 5:
            copyright_lines = sum(1 for line in lines if any(ind in line.lower() for ind in copyright_indicators))
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
