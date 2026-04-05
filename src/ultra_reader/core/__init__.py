"""Core module for UltraReader."""

from ultra_reader.core.types import (
    Book, Chapter, Entity, Relation, Event, Ontology, BookFormat, ProcessingResult
)
from ultra_reader.core.config import Config
from ultra_reader.core.exceptions import (
    UltraReaderError,
    LLMError,
    LLMConnectionError,
    LLMTimeoutError,
    LLMResponseError,
    EbookError,
    EbookFormatError,
    EbookParseError,
    ConfigError,
    ProcessingError,
)
from ultra_reader.core.logger import setup_logger, get_logger

__all__ = [
    "Book",
    "Chapter",
    "Entity",
    "Relation",
    "Event",
    "Ontology",
    "BookFormat",
    "ProcessingResult",
    "Config",
    "UltraReaderError",
    "LLMError",
    "LLMConnectionError",
    "LLMTimeoutError",
    "LLMResponseError",
    "EbookError",
    "EbookFormatError",
    "EbookParseError",
    "ConfigError",
    "ProcessingError",
    "setup_logger",
    "get_logger",
]
