"""
配置管理

支持 YAML 配置文件和环境变量
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# 加载 .env 文件
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")


class LLMConfig(BaseModel):
    """LLM 配置"""
    # 主模型配置（首选）
    primary_provider: str = "minimax"
    primary_model: str = "minimax-2.7"
    primary_base_url: str = "https://api.minimaxi.com/anthropic"
    primary_api_key: str = ""
    
    # 备用模型配置
    fallback_provider: str = "ollama"
    fallback_model: str = "qwen3.5:9b"
    fallback_base_url: str = "http://localhost:11434"
    fallback_api_key: str = ""
    
    timeout: int = 300
    temperature: float = 0.7
    max_retries: int = 3
    
    @property
    def provider(self) -> str:
        """兼容性别名，返回当前使用的 provider"""
        return self.primary_provider
    
    @property
    def model(self) -> str:
        """兼容性别名，返回当前使用的 model"""
        return self.primary_model
    
    @property
    def base_url(self) -> str:
        """兼容性别名，返回当前使用的 base_url"""
        return self.primary_base_url
    
    @property
    def api_key(self) -> str:
        """兼容性别名，返回当前使用的 api_key"""
        return self.primary_api_key


class PipelineConfig(BaseModel):
    """处理流程配置"""
    chunk_size: int = 50000
    overlap: int = 1000
    preserve_history: bool = True
    context_window_warning: int = 200000


class OutputConfig(BaseModel):
    """输出配置"""
    wiki_dir: str = "wiki"
    output_dir: str = "output"
    wiki_template: str = "obsidian"
    include_raw_text: bool = False


class ProcessingConfig(BaseModel):
    """处理配置"""
    max_retries: int = 3
    retry_delay: int = 5


class Config(BaseModel):
    """UltraReader 配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Config":
        path = Path(path)
        if not path.exists():
            return cls()

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    @classmethod
    def from_env(cls) -> "Config":
        data = {}
        if llm_model := os.getenv("ULTRAREADER_LLM_MODEL"):
            data.setdefault("llm", {})["primary_model"] = llm_model
        if llm_url := os.getenv("ULTRAREADER_LLM_BASE_URL"):
            data.setdefault("llm", {})["primary_base_url"] = llm_url
        if api_key := os.getenv("ANTHROPIC_API_KEY"):
            data.setdefault("llm", {})["primary_api_key"] = api_key
        if output_dir := os.getenv("ULTRAREADER_OUTPUT_DIR"):
            data.setdefault("output", {})["output_dir"] = output_dir
        return cls(**data) if data else cls()

    def use_fallback(self) -> None:
        """切换到备用模型配置"""
        self.llm.primary_provider = self.llm.fallback_provider
        self.llm.primary_model = self.llm.fallback_model
        self.llm.primary_base_url = self.llm.fallback_base_url
        self.llm.primary_api_key = self.llm.fallback_api_key

    @classmethod
    def load(
        cls,
        config_path: Optional[Path | str] = None,
        project_root: Optional[Path] = None,
    ) -> "Config":
        if project_root is None:
            project_root = Path.cwd()

        if config_path is None:
            config_path = project_root / "configs" / "default.yaml"

        config_path = Path(config_path)
        config = cls.from_yaml(config_path)

        env_config = cls.from_env()

        if env_config.llm.primary_model:
            config.llm.primary_model = env_config.llm.primary_model
        if env_config.llm.primary_base_url:
            config.llm.primary_base_url = env_config.llm.primary_base_url
        if env_config.llm.primary_api_key:
            config.llm.primary_api_key = env_config.llm.primary_api_key
        if env_config.output.output_dir:
            config.output.output_dir = env_config.output.output_dir

        return config
