"""
Minimax LLM 实现

连接 Minimax API（兼容 Anthropic 格式）
"""

import asyncio
import os
from typing import AsyncIterator

import httpx

from ultra_reader.core.exceptions import LLMConnectionError, LLMTimeoutError, LLMResponseError
from ultra_reader.llm.base import BaseLLM


class MinimaxLLM(BaseLLM):
    """Minimax API LLM 实现（兼容 Anthropic 格式）"""
    STANDARD_MODEL = "MiniMax-M2.7"

    def __init__(
        self,
        base_url: str = "https://api.minimaxi.com/anthropic",
        model: str = STANDARD_MODEL,
        api_key: str | None = None,
        timeout: int = 300,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = self._normalize_model_name(model)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("MINIMAX_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self._client: httpx.AsyncClient | None = None

    @staticmethod
    def _normalize_model_name(model: str) -> str:
        # 当前项目在 minimax provider 下统一固定为标准模型名
        _ = model
        return MinimaxLLM.STANDARD_MODEL

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

    def _is_retryable_error(self, error: httpx.HTTPStatusError) -> bool:
        status_code = error.response.status_code
        if status_code in {408, 409, 429, 500, 502, 503, 504}:
            return True

        response_text = error.response.text.lower()
        return "system error" in response_text or "api_error" in response_text

    @staticmethod
    async def _sleep_with_backoff(attempt: int) -> None:
        # 指数退避：0.8s, 1.6s, 3.2s...
        await asyncio.sleep(0.8 * (2 ** (attempt - 1)))

    async def _post_messages_with_retry(self, payload: dict) -> httpx.Response:
        last_http_error: httpx.HTTPStatusError | None = None

        for attempt in range(1, self.max_retries + 2):
            try:
                response = await self.client.post(f"{self.base_url}/v1/messages", json=payload)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                last_http_error = e
                if attempt > self.max_retries or not self._is_retryable_error(e):
                    raise
                await self._sleep_with_backoff(attempt)

        if last_http_error is not None:
            raise last_http_error
        raise LLMResponseError("Minimax 请求失败，未知错误")

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
            response = await self._post_messages_with_retry(
                {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": 8192,
                    "temperature": temperature,
                    **kwargs,
                }
            )
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
            for attempt in range(1, self.max_retries + 2):
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
                    break
                except httpx.HTTPStatusError as e:
                    if attempt > self.max_retries or not self._is_retryable_error(e):
                        error_detail = e.response.text
                        raise LLMResponseError(
                            f"LLM HTTP 错误 ({e.response.status_code}): {error_detail}"
                        ) from e
                    await self._sleep_with_backoff(attempt)

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
            response = await self._post_messages_with_retry(
                {
                    "model": self.model,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 1,
                }
            )
            return response.status_code == 200
        except Exception:
            return False
