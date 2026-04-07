"""
UltraReader 集成测试脚本

测试 EPUB 读取 + LLM 处理 + 本体提取的完整流程
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ultra_reader.pipeline.reader import EPUBReader
from ultra_reader.pipeline.runner import PipelineRunner
from ultra_reader.llm.ollama import OllamaLLM
from ultra_reader.core.config import Config
from ultra_reader.core.types import Book, Ontology, Entity, Relation, Event


class IntegrationTester:
    """集成测试器"""
    
    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.reader = EPUBReader()
        self.book: Optional[Book] = None
        
    def test_reading(self) -> bool:
        """测试 EPUB 读取"""
        print("\n" + "=" * 80)
        print("【测试 1】EPUB 读取测试")
        print("=" * 80)
        
        try:
            self.book = self.reader.read(self.epub_path)
            
            print(f"\n✓ 成功读取 EPUB")
            print(f"  标题: {self.book.title}")
            print(f"  作者: {self.book.author or '未知'}")
            print(f"  章节数: {len(self.book.chapters)}")
            print(f"  总字符数: {self.book.total_chars:,}")
            
            # 显示章节列表
            print(f"\n  章节列表:")
            for i, chapter in enumerate(self.book.chapters):
                print(f"    [{i+1:2d}] {chapter.title:<20} - {len(chapter.content):,} 字符")
            
            return True
            
        except Exception as e:
            print(f"\n✗ 读取失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_llm_extraction(self, max_chapters: int = 3) -> bool:
        """测试 LLM 本体提取（只测试前几个章节）"""
        print("\n" + "=" * 80)
        print(f"【测试 2】LLM 本体提取测试 (前 {max_chapters} 个章节)")
        print("=" * 80)
        
        if not self.book:
            print("✗ 未加载书籍")
            return False
        
        # 限制测试的章节数
        test_chapters = self.book.chapters[:max_chapters]
        
        try:
            # 创建 LLM 客户端
            print("\n  初始化 Ollama LLM...")
            llm = OllamaLLM(
                base_url="http://localhost:11434",
                model="qwen3.5:9b",
                timeout=300  # 5 分钟超时
            )
            
            # 检查连接
            print("  检查 Ollama 连接...")
            if not await llm.check_connection():
                print("✗ 无法连接到 Ollama")
                return False
            print("  ✓ Ollama 连接正常")
            
            # 创建 Pipeline Runner
            config = Config()
            runner = PipelineRunner(llm=llm, config=config)
            
            # 只处理测试章节
            print(f"\n  开始处理 {len(test_chapters)} 个章节...")
            
            # 构建本体
            ontology = Ontology(
                book_id="test",
                book_title=self.book.title
            )
            
            history_context = ""
            
            for i, chapter in enumerate(test_chapters):
                print(f"\n  处理章节 {i+1}/{len(test_chapters)}: {chapter.title}")
                
                # 准备 prompt
                system_prompt = runner._get_extraction_system_prompt()
                user_prompt = runner._get_extraction_user_prompt().format(
                    book_title=self.book.title,
                    author=self.book.author or "未知",
                    chapter_index=i + 1,
                    chapter_title=chapter.title,
                    history_context=history_context,
                    chapter_content=chapter.content[:10000]  # 限制内容长度
                )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # 调用 LLM
                print(f"    正在调用 LLM...")
                response = await llm.chat(messages)
                
                # 解析响应
                chapter_ontology = runner._parse_llm_response(response, i)
                ontology.merge(chapter_ontology)
                
                # 更新历史上下文
                history_context = ontology.to_history_context()
                
                print(f"    ✓ 提取完成: {len(chapter_ontology.entities)} 实体, {len(chapter_ontology.relations)} 关系")
                
                # 显示 LLM 输出片段
                print(f"\n    LLM 输出片段:")
                lines = response.split('\n')[:20]
                for line in lines:
                    print(f"      {line[:100]}")
                if len(response.split('\n')) > 20:
                    print(f"      ... (共 {len(response.split(chr(10)))} 行)")
            
            # 显示最终本体
            print("\n" + "-" * 80)
            print("提取的本体摘要:")
            print("-" * 80)
            print(f"\n  实体 ({len(ontology.entities)} 个):")
            for entity in ontology.entities[:10]:
                print(f"    - [[{entity.name}]] ({entity.entity_type or '未知'})")
            if len(ontology.entities) > 10:
                print(f"    ... 还有 {len(ontology.entities) - 10} 个实体")
            
            print(f"\n  关系 ({len(ontology.relations)} 个):")
            for relation in ontology.relations[:10]:
                print(f"    - [[{relation.source}]] --[{relation.relation_type or '关联'}]--> [[{relation.target}]]")
            if len(ontology.relations) > 10:
                print(f"    ... 还有 {len(ontology.relations) - 10} 个关系")
            
            print(f"\n  事件 ({len(ontology.events)} 个):")
            for event in ontology.events[:5]:
                print(f"    - {event.title}")
            if len(ontology.events) > 5:
                print(f"    ... 还有 {len(ontology.events) - 5} 个事件")
            
            await llm.close()
            
            return True
            
        except Exception as e:
            print(f"\n✗ LLM 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_full_pipeline(self) -> bool:
        """测试完整处理流程（可选）"""
        print("\n" + "=" * 80)
        print("【测试 3】完整处理流程测试")
        print("=" * 80)
        
        if not self.book:
            print("✗ 未加载书籍")
            return False
        
        try:
            llm = OllamaLLM(
                base_url="http://localhost:11434",
                model="qwen3.5:9b",
                timeout=600
            )
            
            if not await llm.check_connection():
                print("✗ 无法连接到 Ollama")
                return False
            
            config = Config()
            runner = PipelineRunner(llm=llm, config=config)
            
            print(f"\n  处理书籍: {self.book.title}")
            print(f"  章节数: {len(self.book.chapters)}")
            
            # 注意：完整处理会很慢，只显示提示
            print("\n  ⚠️ 完整处理需要较长时间，跳过执行")
            print("  如需完整处理，请使用 CLI: ultra-reader process raw/杨贵妃_副本.epub")
            
            await llm.close()
            return True
            
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            return False


async def main():
    print("=" * 80)
    print("UltraReader 集成测试")
    print("=" * 80)
    print(f"测试文件: raw/杨贵妃_副本.epub")
    
    tester = IntegrationTester("raw/杨贵妃_副本.epub")
    
    # 测试 1: 读取
    if not tester.test_reading():
        return 1
    
    # 测试 2: LLM 提取（只测试前 3 个章节以节省时间）
    if not await tester.test_llm_extraction(max_chapters=3):
        return 1
    
    # 测试 3: 完整流程（跳过）
    if not await tester.test_full_pipeline():
        return 1
    
    print("\n" + "=" * 80)
    print("✓ 所有测试通过!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
