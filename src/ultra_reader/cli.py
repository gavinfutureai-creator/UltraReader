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
from ultra_reader.llm.ollama import OllamaLLM
from ultra_reader.pipeline.runner import PipelineRunner


console = Console()
setup_logger()


@click.group()
@click.version_option(version=__version__)
def cli():
    """UltraReader - LLM-First 电子书拆书工具"""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output")
@click.option("-m", "--model")
def process(input_file, output, model):
    """处理电子书文件"""
    async def _run():
        config = Config.load()
        if model:
            config.llm.model = model

        console.print(f"[bold blue]UltraReader v{__version__}[/bold blue]")
        console.print("[yellow]检查 LLM 连接...[/yellow]")

        # 增加超时时间以支持大型模型
        llm = OllamaLLM(base_url=config.llm.base_url, model=config.llm.model, timeout=600)

        if not await llm.check_connection():
            console.print("[red]错误: 无法连接到 Ollama 服务[/red]")
            console.print(f"[yellow]请确保 Ollama 运行于 {config.llm.base_url}[/yellow]")
            return 1

        console.print(f"[green]✓[/green] 已连接: {llm.model}")

        if output:
            config.output.output_dir = output

        runner = PipelineRunner(llm=llm, config=config)

        console.print(f"[yellow]处理: {Path(input_file).name}[/yellow]")

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
                console.print(f"  章节: {result.chapters_processed}")
                console.print(f"  实体: {len(result.ontology.entities)}")
                console.print(f"  关系: {len(result.ontology.relations)}")
                console.print(f"  路径: {result.wiki_path}")
            else:
                console.print(f"[red]✗ 失败: {result.error_message}[/red]")
                return 1

        await llm.close()
        return 0

    exit_code = asyncio.run(_run())
    sys.exit(exit_code)


@cli.command()
@click.option("-m", "--model")
@click.option("--url")
def check(model, url):
    """检查 LLM 连接"""
    async def _run():
        config = Config.load()
        if model:
            config.llm.model = model
        if url:
            config.llm.base_url = url

        console.print("[yellow]检查连接...[/yellow]")
        llm = OllamaLLM(base_url=config.llm.base_url, model=config.llm.model)

        if await llm.check_connection():
            console.print(f"[green]✓[/green] {llm.base_url}")
            console.print(f"  模型: {llm.model}")
            models = await llm.list_models()
            if models:
                console.print("  可用模型:")
                for m in models[:5]:
                    console.print(f"    - {m.get('name', 'unknown')}")
        else:
            console.print("[red]✗ 无法连接[/red]")
            return 1

        await llm.close()
        return 0

    exit_code = asyncio.run(_run())
    sys.exit(exit_code)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()
