"""
UltraReader - LLM-First 电子书拆书工具

基于 Karpathy 的 LLM-first 理念 + 本体论理论构建知识库
"""

__version__ = "0.1.0"
__author__ = "UltraReader Team"

from ultra_reader.core.types import Book, Chapter, Entity, Relation, Event, Ontology, ProcessingResult
from ultra_reader.core.config import Config
from ultra_reader.llm.ollama import OllamaLLM
from ultra_reader.pipeline.runner import PipelineRunner

__all__ = [
    "Book",
    "Chapter",
    "Entity",
    "Relation",
    "Event",
    "Ontology",
    "ProcessingResult",
    "Config",
    "OllamaLLM",
    "PipelineRunner",
]
