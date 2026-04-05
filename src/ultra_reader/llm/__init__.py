"""LLM module for UltraReader."""

from ultra_reader.llm.base import BaseLLM
from ultra_reader.llm.minimax import MinimaxLLM
from ultra_reader.llm.ollama import OllamaLLM

__all__ = [
    "BaseLLM",
    "MinimaxLLM",
    "OllamaLLM",
]
