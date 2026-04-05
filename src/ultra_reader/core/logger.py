"""
日志模块

使用 loguru 提供简洁的日志接口
"""

import sys
from typing import Optional

from loguru import logger

logger.remove()

DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logger(
    level: str = "INFO",
    format: Optional[str] = None,
    colorize: bool = True,
    show_module: bool = True,
) -> None:
    if format is None:
        format = DEFAULT_FORMAT if show_module else "<level>{level: <8}</level> | {message}"

    logger.add(
        sys.stderr,
        format=format,
        level=level,
        colorize=colorize,
        backtrace=True,
        diagnose=True,
    )


def get_logger(name: Optional[str] = None):
    if name:
        return logger.bind(name=name)
    return logger


setup_logger()
