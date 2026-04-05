"""
Minimax LLM 实现

连接 Minimax API（兼容 Anthropic 格式）
"""

import os
from typing import AsyncIterator

import httpx

from ultra_reader.core.exceptions import LLMConnectionError, LLMTimeoutError, LLMResponseError
from ultra_reader.llm.base import BaseLLM


class MinimaxLLM(BaseLLM):
    """Minimax API LLM 实现（兼容 Anthropic 格式）"""

    def __init__(
        self,
        base_url: str = "https://api.minimaxi.com/anthropic",
        model: str = "minimax-2.7",
        api_key: str | None = None,
        timeout: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def provider(self) -> str:
        return "minimax"

    @property
    def name(self) -> str:
        return self.model

    @property
    def max_context(self) -> int:
        return 256_000 * 2

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
        **kwargs,
    ) -> str:
        """调用 Minimax API"""
        if not self.api_key:
            raise LLMConnectionError(
                "ANTHROPIC_API_KEY 未设置，请设置环境变量 ANTHROPIC_API_KEY"
            )

        try:
            response = await self.client.post(
                f"{self.base_url}/v1/messages",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 8192,
                    "temperature": temperature,
                    **kwargs,
                },
            )
            response.raise_for_status()
            data = response.json()

            if "content" not in data:
                raise LLMResponseError(f"Invalid response: {data}")

            # 提取文本内容，跳过 thinking 类型的 content block
            for block in data["content"]:
                if block.get("type") == "text":
                    return block["text"]

            raise LLMResponseError(f"No text content in response: {data}")

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"无法连接到 Minimax API {self.base_url}，请检查网络连接"
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"LLM 请求超时: {e}") from e
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            raise LLMResponseError(f"LLM HTTP 错误 ({e.response.status_code}): {error_detail}") from e

    async def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式调用 Minimax API"""
        if not self.api_key:
            raise LLMConnectionError(
                "ANTHROPIC_API_KEY 未设置，请设置环境变量 ANTHROPIC_API_KEY"
            )

        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/v1/messages",
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 8192,
                    "temperature": temperature,
                    "stream": True,
                    **kwargs,
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break
                        try:
                            import json

                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        yield text
                        except (json.JSONDecodeError, KeyError):
                            continue

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"无法连接到 Minimax API {self.base_url}，请检查网络连接"
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"LLM 流式请求超时: {e}") from e

    async def check_connection(self) -> bool:
        """检查 Minimax API 连接状态"""
        if not self.api_key:
            return False
        try:
            # 发送一个最小请求来测试连接
            response = await self.client.post(
                f"{self.base_url}/v1/messages",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                },
            )
            return response.status_code == 200
        except Exception:
            return False
