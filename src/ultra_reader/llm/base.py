"""
LLM 抽象接口

定义 LLM 交互的标准接口
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseLLM(ABC):
    """LLM 接口基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """LLM 名称/模型名"""

    @property
    def provider(self) -> str:
        """LLM 提供商"""
        return "unknown"

    @property
    def max_context(self) -> int:
        """最大上下文长度"""
        return 128_000 * 2

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """发送对话请求"""

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式对话"""

    async def close(self) -> None:
        """关闭连接"""
        pass
