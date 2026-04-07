"""
UltraReader 测试脚本

测试 EPUB 读取和处理功能，特别是前 30 页的内容。
"""

import asyncio
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ultra_reader.pipeline.reader import EPUBReader
from ultra_reader.core.types import Book, Chapter


def test_epub_reader(epub_path: str, max_chapters: int = 30):
    """测试 EPUB 读取器，读取指定数量的章节"""
    print(f"=" * 80)
    print(f"测试 EPUB 读取器")
    print(f"=" * 80)
    print(f"文件: {epub_path}")
    print(f"最大章节数: {max_chapters}")
    print()
    
    reader = EPUBReader()
    
    # 检查文件支持
    if not reader.supports(epub_path):
        print(f"❌ 错误: 不支持的文件格式")
        return None
    
    # 读取书籍
    try:
        book = reader.read(epub_path)
        print(f"✓ 成功读取 EPUB")
        print()
        
        # 显示书籍信息
        print(f"📖 书籍信息:")
        print(f"   标题: {book.title}")
        print(f"   作者: {book.author or '未知'}")
        print(f"   格式: {book.format.value}")
        print(f"   总章节数: {len(book.chapters)}")
        print(f"   总字符数: {book.total_chars:,}")
        print()
        
        # 显示前 N 个章节
        display_chapters = min(max_chapters, len(book.chapters))
        print(f"📑 前 {display_chapters} 个章节:")
        print("-" * 80)
        
        for i, chapter in enumerate(book.chapters[:display_chapters]):
            print()
            print(f"【章节 {chapter.index + 1}】{chapter.title}")
            print(f"   字符数: {len(chapter.content):,}")
            print()
            
            # 显示章节内容的前 500 字符作为预览
            preview = chapter.content[:500].replace('\n', ' ')
            if len(chapter.content) > 500:
                preview += "..."
            print(f"   预览: {preview}")
            print()
        
        return book
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_chapter_extraction(book: Book, chapter_indices: list[int] = None):
    """测试章节内容提取"""
    print()
    print("=" * 80)
    print("测试章节内容提取")
    print("=" * 80)
    
    if chapter_indices is None:
        chapter_indices = [0, 1, 2, 14, 29]  # 默认测试章节 1, 2, 3, 15, 30
    
    for idx in chapter_indices:
        if idx >= len(book.chapters):
            print(f"⚠️ 章节 {idx + 1} 不存在 (总共 {len(book.chapters)} 章节)")
            continue
            
        chapter = book.chapters[idx]
        print()
        print(f"【章节 {idx + 1}】{chapter.title}")
        print("-" * 40)
        
        # 分析内容
        lines = chapter.content.split('\n')
        non_empty_lines = [l for l in lines if l.strip()]
        
        print(f"   总行数: {len(lines)}")
        print(f"   非空行数: {len(non_empty_lines)}")
        print(f"   字符数: {len(chapter.content):,}")
        
        # 显示更多内容预览
        preview_lines = non_empty_lines[:10] if non_empty_lines else []
        if preview_lines:
            print()
            print("   内容预览 (前10行):")
            for line in preview_lines:
                truncated = line[:100] + "..." if len(line) > 100 else line
                print(f"      {truncated}")


def analyze_epub_structure(epub_path: str):
    """分析 EPUB 文件结构"""
    print()
    print("=" * 80)
    print("EPUB 结构分析")
    print("=" * 80)
    
    try:
        from ebooklib import epub
        
        book_epub = epub.read_epub(epub_path)
        
        # 获取所有项目
        items = list(book_epub.get_items())
        
        print()
        print(f"总项目数: {len(items)}")
        
        # 按类型分类
        item_types = {}
        for item in items:
            item_type = str(item.get_type())
            if item_type not in item_types:
                item_types[item_type] = []
            item_types[item_type].append(item)
        
        print()
        print("项目类型分布:")
        for item_type, type_items in item_types.items():
            print(f"   类型 {item_type}: {len(type_items)} 项")
        
        # 显示 HTML 项目（章节）
        html_items = [item for item in items if item.get_type() == 9]
        print()
        print(f"HTML 章节数: {len(html_items)}")
        
        # 显示前 30 个 HTML 项的基本信息
        display_count = min(30, len(html_items))
        print()
        print(f"前 {display_count} 个 HTML 章节:")
        for i, item in enumerate(html_items[:display_count]):
            content = item.get_content()
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            # 尝试提取标题
            title = None
            import re
            title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
            if title_match:
                title = title_match.group(1)
            
            h1_match = re.search(r'<h1[^>]*>([^<]+)</h1>', content, re.IGNORECASE)
            if h1_match:
                title = h1_match.group(1)
            
            h2_match = re.search(r'<h2[^>]*>([^<]+)</h2>', content, re.IGNORECASE)
            if h2_match:
                title = h2_match.group(1)
            
            print(f"   [{i+1:2d}] {title or '(无标题)':<30} | {len(content):,} 字节")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="UltraReader 测试脚本")
    parser.add_argument("epub_file", help="EPUB 文件路径")
    parser.add_argument("-n", "--num-chapters", type=int, default=30, help="显示的章节数量 (默认: 30)")
    parser.add_argument("--analyze-only", action="store_true", help="仅分析 EPUB 结构，不读取内容")
    parser.add_argument("--test-chapters", type=int, nargs="+", help="指定测试的章节索引 (从 1 开始)")
    
    args = parser.parse_args()
    
    epub_path = Path(args.epub_file)
    if not epub_path.exists():
        print(f"❌ 文件不存在: {epub_path}")
        return 1
    
    # 分析 EPUB 结构
    analyze_epub_structure(str(epub_path))
    
    if not args.analyze_only:
        # 读取并显示内容
        book = test_epub_reader(str(epub_path), args.num_chapters)
        
        if book:
            # 测试章节提取
            if args.test_chapters:
                # 转换为 0 索引
                indices = [i - 1 for i in args.test_chapters]
                test_chapter_extraction(book, indices)
            else:
                # 默认测试章节 1, 2, 3, 15, 30
                test_chapter_extraction(book)
    
    print()
    print("=" * 80)
    print("测试完成")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
