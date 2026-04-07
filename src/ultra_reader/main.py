"""
UltraReader 主入口
"""

from ultra_reader.core.config import Config
from ultra_reader.core.exceptions import LLMConnectionError, LLMTimeoutError, LLMResponseError
from ultra_reader.llm.minimax import MinimaxLLM
from ultra_reader.llm.ollama import OllamaLLM
from ultra_reader.pipeline.runner import PipelineRunner

__all__ = ["run", "main"]


def create_llm_client(config: Config) -> tuple[MinimaxLLM | OllamaLLM, str]:
    """创建 LLM 客户端，根据 provider 自动选择"""
    if config.llm.provider == "minimax":
        return MinimaxLLM(
            base_url=config.llm.base_url,
            model=config.llm.model,
            api_key=config.llm.api_key,
            timeout=config.llm.timeout,
            max_retries=config.llm.max_retries,
        ), "minimax"
    else:
        return OllamaLLM(
            base_url=config.llm.base_url,
            model=config.llm.model,
            timeout=config.llm.timeout,
        ), "ollama"


async def _run_with_fallback(
    input_file: str,
    output_dir: str | None,
    config: Config,
) -> dict:
    """运行处理流程，支持主模型失败时切换到备用模型"""
    # 尝试主模型
    llm, provider_name = create_llm_client(config)
    
    try:
        runner = PipelineRunner(llm=llm, config=config)
        result = await runner.process(input_file, output_dir)
        await llm.close()

        return {
            "success": result.success,
            "book_title": result.book_title,
            "wiki_path": result.wiki_path,
            "processing_time": result.processing_time,
            "entities": len(result.ontology.entities),
            "relations": len(result.ontology.relations),
            "provider": provider_name,
            "error": result.error_message,
        }

    except (LLMConnectionError, LLMTimeoutError, LLMResponseError) as e:
        await llm.close()
        
        # 检查是否已经是备用模型
        if config.llm.provider == config.llm.fallback_provider:
            return {
                "success": False,
                "book_title": "",
                "wiki_path": "",
                "processing_time": 0,
                "entities": 0,
                "relations": 0,
                "provider": provider_name,
                "error": f"备用模型 ({provider_name}) 也失败: {str(e)}",
            }
        
        # 切换到备用模型
        print(f"⚠️ 主模型失败: {str(e)}")
        print(f"🔄 切换到备用模型: {config.llm.fallback_provider} ({config.llm.fallback_model})")
        config.use_fallback()
        
        fallback_llm, fallback_name = create_llm_client(config)
        try:
            runner = PipelineRunner(llm=fallback_llm, config=config)
            result = await runner.process(input_file, output_dir)
            await fallback_llm.close()

            return {
                "success": result.success,
                "book_title": result.book_title,
                "wiki_path": result.wiki_path,
                "processing_time": result.processing_time,
                "entities": len(result.ontology.entities),
                "relations": len(result.ontology.relations),
                "provider": fallback_name,
                "error": result.error_message,
            }
        except Exception as fallback_error:
            await fallback_llm.close()
            return {
                "success": False,
                "book_title": "",
                "wiki_path": "",
                "processing_time": 0,
                "entities": 0,
                "relations": 0,
                "provider": fallback_name,
                "error": f"备用模型 ({fallback_name}) 也失败: {str(fallback_error)}",
            }


def run(input_file: str, output_dir: str | None = None, model: str | None = None) -> dict:
    """运行处理流程"""
    import asyncio

    async def _run_async():
        config = Config.load()
        if model:
            config.llm.primary_model = model
        if output_dir:
            config.output.output_dir = output_dir

        return await _run_with_fallback(input_file, output_dir, config)

    return asyncio.run(_run_async())


def main():
    """CLI 主入口"""
    from ultra_reader.cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
