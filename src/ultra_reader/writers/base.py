"""Writer 抽象基类"""

from abc import ABC, abstractmethod
from pathlib import Path

from ultra_reader.core.types import Book, Ontology


class BaseWriter(ABC):
    """Writer 抽象基类"""

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)

    @abstractmethod
    def write(self, book: Book, ontology: Ontology) -> Path:
        """写入输出文件"""
        pass

    def _sanitize_filename(self, name: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")
        if len(name) > 100:
            name = name[:100]
        return name.strip()
