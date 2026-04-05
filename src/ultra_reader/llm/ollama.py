"""
Ollama LLM 实现

连接本地 Ollama 服务
"""

import json
from typing import AsyncIterator

import httpx

from ultra_reader.core.exceptions import LLMConnectionError, LLMTimeoutError, LLMResponseError
from ultra_reader.llm.base import BaseLLM


class OllamaLLM(BaseLLM):
    """Ollama 本地 LLM 实现"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3.5:9b",
        timeout: int = 300,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    @property
    def provider(self) -> str:
        return "ollama"

    @property
    def name(self) -> str:
        return self.model

    @property
    def max_context(self) -> int:
        return 256_000 * 2

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
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
        """调用 Ollama /api/chat"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        **kwargs,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            if "message" not in data:
                raise LLMResponseError(f"Invalid response: {data}")

            return data["message"]["content"]

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"无法连接到 Ollama 服务 {self.base_url}，请确保 Ollama 正在运行"
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"LLM 请求超时: {e}") from e
        except httpx.HTTPStatusError as e:
            raise LLMResponseError(f"LLM HTTP 错误: {e.response.text}") from e

    async def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.7,
        **kwargs,
    ) -> AsyncIterator[str]:
        """流式调用 Ollama"""
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": temperature,
                        **kwargs,
                    },
                },
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data:
                                content = data["message"]["content"]
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"无法连接到 Ollama 服务 {self.base_url}，请确保 Ollama 正在运行"
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"LLM 流式请求超时: {e}") from e

    async def check_connection(self) -> bool:
        """检查 Ollama 连接状态"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[dict]:
        """列出可用的模型"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception:
            return []
