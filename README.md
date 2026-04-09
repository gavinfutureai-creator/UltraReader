# UltraReader

> LLM-First 电子书拆书工具 - 基于本体论的知识库构建

**核心理念**：LLM 是主角，工程是辅助

## 核心特性

- **LLM-First 设计**：LLM 主导知识提取，工程负责辅助
- **本体论方法**：自动发现实体、关系、事件和概念
- **Obsidian 兼容**：生成双向链接的 Wiki 格式
- **多模型支持**：支持 Ollama 本地模型和云端 API
- **知识库问答**：基于已处理书籍的 Wiki 知识库进行 Q&A
- **书籍摘要**：处理完成后自动生成书籍概述

## 工作原理

```
raw/电子.epub  ──工程层──▶  LLM  ──智能层──▶  wiki/书籍/
   (读取)                      (理解)               (Obsidian)
```

**处理流程**：

1. 按 EPUB spine 顺序读取章节（可靠的阅读顺序）
2. LLM 按本体论视角分析每章，提取实体/关系/事件/概念
3. 生成书籍摘要（处理完成后调用 LLM）
4. 输出为 Obsidian 兼容的 Wiki 格式

**LLM 负责**：

- 理解书籍语义
- 决定重要实体
- 建立实体关系
- 生成自然语言描述
- 生成书籍摘要

**工程负责**：

- 读取电子书
- 调用 LLM API
- 格式化输出为 Wiki

## 安装

```bash
pip install -e ".[dev]"
```

## 配置

1. 复制配置模板：

```bash
cp .env.example .env
```

2. 配置 API Key（可选，支持 Ollama 本地运行）：

```bash
# 使用本地 Ollama（默认）
nano .env

# 或使用云端 API
# ANTHROPIC_API_KEY=your-api-key
```

## 使用

### 检查 LLM 连接

```bash
python -m ultra_reader.cli check
```

### 处理电子书

处理默认模型（自动 fallback）：

```bash
python -m ultra_reader.cli process raw/杨贵妃.epub
```

指定输出目录：

```bash
python -m ultra_reader.cli process raw/杨贵妃.epub -o output/
```

指定模型：

```bash
# 使用 ollama
python -m ultra_reader.cli process raw/杨贵妃.epub -p ollama

# 使用 minimax
python -m ultra_reader.cli process raw/杨贵妃.epub -p minimax
```

禁用 fallback（只使用主模型）：

```bash
python -m ultra_reader.cli process raw/杨贵妃.epub --no-fallback
```

### 向已处理书籍提问

先查看有哪些可查询的书籍：

```bash
python -m ultra_reader.cli ask "随便什么问题"
```

向指定书籍提问：

```bash
python -m ultra_reader.cli ask -b 杨贵妃 "杨贵妃和唐玄宗的关系是怎么演变的？"
```

参数说明：

| 参数 | 说明 |
|------|------|
| `-b <书名>` | 指定要查询的书，必须全名匹配 |
| 最后那段话 | 你的问题，用引号包起来 |
| `-p` | 指定模型（minimax 或 ollama） |
| `-m` | 指定模型名称 |

## 输出结构

处理完成后生成 Obsidian Wiki：

```
wiki/
└── <书名>/
    ├── index.md          # 书籍概览、导航、摘要
    ├── entities/
    │   └── index.md       # 实体索引（人物、地点、组织、物品、概念、时间）
    ├── relations.md       # 关系网络图
    ├── events.md          # 事件时间线
    ├── concepts.md        # 核心概念
    └── themes.md          # 主题分析
```

### 示例输出

**index.md**：

```markdown
---
type: book
title: 杨玉环
author: 关黎明
processed_at: 2026-04-07
entity_count: 42
relation_count: 18
---

# 杨玉环

## 概述

主题**：本作品以20世纪20年代的北平城为背景...

## 核心实体
- [[唐玄宗李隆基]] (人物)
- [[杨玉环]] (人物)
- [[骊山温泉宫]] (地点)

## 核心关系
- [[唐玄宗李隆基]] --[下达召见令]--> [[杨玉环]]
- [[杨玉环]] --[曾为王妃]--> [[寿王李瑁]]
```

## 命令行参数

### process

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input_file` | 电子书文件路径（支持 EPUB） | - |
| `-o, --output` | 输出目录 | output/ |
| `-p, --provider` | Provider（minimax 或 ollama） | ollama |
| `-m, --model` | 模型名称 | qwen3.5:9b |
| `--no-fallback` | 禁用备用模型 fallback | false |

### ask

| 参数 | 说明 |
|------|------|
| `question` | 你的问题 |
| `-b, --book` | 指定查询的书名 |
| `-p, --provider` | 指定模型 |
| `-m, --model` | 指定模型名称 |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `ULTRAREADER_LLM_PROVIDER` | 首选 provider | ollama |
| `ULTRAREADER_LLM_MODEL` | 模型名称 | qwen3.5:9b |
| `ULTRAREADER_LLM_BASE_URL` | API 端点 | http://localhost:11434 |
| `ANTHROPIC_API_KEY` | Minimax API Key | - |
| `ULTRAREADER_OUTPUT_DIR` | 输出目录 | output |

## 项目结构

```
ultra-reader/
├── src/ultra_reader/        # 源代码
│   ├── cli.py              # CLI 入口
│   ├── llm/                # LLM 接口（Ollama、MiniMax）
│   ├── pipeline/           # 处理流程
│   ├── prompts/            # Prompt 模板（提取、摘要、问答）
│   ├── qa/                 # 知识库问答
│   └── writers/            # Wiki 输出格式化
├── configs/                # 配置文件
├── raw/                    # 原始电子书
├── wiki/                   # 生成的 Wiki（Obsidian 格式）
├── output/                 # 结构化输出
└── tests/                  # 测试
```

## LLM 模型

### 默认配置

| Provider | 模型 | 说明 |
|----------|------|------|
| **ollama** | qwen3.5:9b | 本地模型，需要 Ollama |
| **minimax** | MiniMax-M2.7 | 云端 API，需要 API Key |

### Ollama 安装

```bash
# 安装 Ollama
brew install ollama

# 启动服务
ollama serve

# 拉取模型
ollama pull qwen3.5:9b
```

## 技术栈

- **Python**: 3.11+
- **LLM**: Ollama / OpenAI / Anthropic
- **电子书**: ebooklib
- **配置**: PyYAML
- **数据验证**: Pydantic

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 代码格式检查
ruff check src/

# 类型检查
mypy src/
```

---

*LLM-first，工程辅助*
