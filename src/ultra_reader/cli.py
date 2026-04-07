"""
UltraReader CLI

命令行入口
"""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

from ultra_reader import __version__
from ultra_reader.core.config import Config
from ultra_reader.core.logger import setup_logger
from ultra_reader.llm.minimax import MinimaxLLM
from ultra_reader.llm.ollama import OllamaLLM
from ultra_reader.pipeline.runner import PipelineRunner


console = Console()
setup_logger()


def create_llm(config: Config, provider: str | None = None):
    """根据配置创建 LLM 实例"""
    use_provider = provider or config.llm.provider
    
    if use_provider.lower() == "minimax":
        return MinimaxLLM(
            base_url=config.llm.base_url,
            model=config.llm.model,
            api_key=config.llm.api_key,
            timeout=600,
            max_retries=config.llm.max_retries,
        )
    elif use_provider.lower() == "ollama":
        return OllamaLLM(
            base_url=config.llm.base_url,
            model=config.llm.model,
            timeout=600,
        )
    else:
        raise ValueError(f"不支持的 LLM provider: {use_provider}")


async def check_connection(config: Config, provider: str) -> tuple[bool, str]:
    """检查 LLM 连接，返回 (是否成功, 状态消息)"""
    llm = create_llm(config, provider)
    
    try:
        success = await llm.check_connection()
        if success:
            return True, f"{llm.model} 可用"
        else:
            return False, "无法连接或模型不可用"
    finally:
        await llm.close()


@click.group()
@click.version_option(version=__version__)
def cli():
    """UltraReader - LLM-First 电子书拆书工具"""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output")
@click.option("-m", "--model")
@click.option("-p", "--provider", default=None, help="LLM provider: minimax 或 ollama")
@click.option("--no-fallback", is_flag=True, help="禁用备用模型 fallback")
def process(input_file, output, model, provider, no_fallback):
    """处理电子书文件
    
    优先使用 MiniMax-M2.7 模型，当其不可用时自动切换到 ollama 备用模型。
    """
    async def _run():
        config = Config.load()
        
        if model:
            config.llm.primary_model = model
        if provider:
            config.llm.primary_provider = provider

        console.print(f"[bold blue]UltraReader v{__version__}[/bold blue]")
        console.print(f"[dim]首选: {config.llm.primary_provider} ({config.llm.primary_model})[/dim]")
        if not no_fallback:
            console.print(f"[dim]备用: {config.llm.fallback_provider} ({config.llm.fallback_model})[/dim]")

        console.print(f"\n[yellow]尝试连接主模型: {config.llm.primary_provider}...[/yellow]")
        success, message = await check_connection(config, config.llm.primary_provider)
        
        if success:
            console.print(f"[green]✓[/green] {message}")
            use_provider = config.llm.primary_provider
        elif no_fallback:
            console.print(f"[red]✗ 主模型不可用，已禁用备用模型[/red]")
            console.print(f"[yellow]错误: {message}[/yellow]")
            return 1
        else:
            console.print(f"[yellow]⚠[/yellow] {message}")
            console.print(f"[yellow]切换到备用模型: {config.llm.fallback_provider}...[/yellow]")
            config.use_fallback()
            
            success, message = await check_connection(config, config.llm.fallback_provider)
            if success:
                console.print(f"[green]✓[/green] {message}")
                use_provider = config.llm.fallback_provider
            else:
                console.print(f"[red]✗ 备用模型也不可用[/red]")
                console.print(f"[yellow]错误: {message}[/yellow]")
                return 1

        if output:
            config.output.output_dir = output

        llm = create_llm(config, use_provider)
        runner = PipelineRunner(llm=llm, config=config)

        console.print(f"\n[yellow]处理: {Path(input_file).name}[/yellow]")

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]处理中...", total=100)
                result = await runner.process(input_file)

                if result.success:
                    progress.update(task, completed=100)
                    console.print()
                    console.print("[green]✓ 处理成功![/green]")
                    console.print(f"  使用模型: {use_provider} ({config.llm.model})")
                    console.print(f"  章节: {result.chapters_processed}")
                    console.print(f"  实体: {len(result.ontology.entities)}")
                    console.print(f"  关系: {len(result.ontology.relations)}")
                    console.print(f"  路径: {result.wiki_path}")
                else:
                    console.print(f"[red]✗ 失败: {result.error_message}[/red]")
                    return 1
        finally:
            await llm.close()
        
        return 0

    exit_code = asyncio.run(_run())
    sys.exit(exit_code)


@cli.command()
@click.option("-m", "--model")
@click.option("-p", "--provider", default=None, help="LLM provider: minimax 或 ollama")
def check(model, provider):
    """检查 LLM 连接"""
    async def _run():
        config = Config.load()
        if model:
            config.llm.primary_model = model
        if provider:
            config.llm.primary_provider = provider

        console.print("[yellow]检查连接...[/yellow]")
        console.print(f"[dim]首选: {config.llm.primary_provider} ({config.llm.primary_model})[/dim]")

        success, message = await check_connection(config, config.llm.primary_provider)
        
        if success:
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(f"[red]✗ {message}[/red]")
            
            console.print(f"\n[yellow]检查备用模型: {config.llm.fallback_provider}...[/yellow]")
            success2, message2 = await check_connection(config, config.llm.fallback_provider)
            if success2:
                console.print(f"[green]✓[/green] {message2}")
            else:
                console.print(f"[red]✗ {message2}[/red]")
            
            return 1

        return 0

    exit_code = asyncio.run(_run())
    sys.exit(exit_code)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
