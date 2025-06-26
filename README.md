# C语言智能代码分析调试工具 (Code Repo Learner)

## 项目概述

**Code Repo Learner** 是一个基于AI的C语言代码分析调试工具，结合Tree-sitter语法分析、Neo4j图数据库和LLM智能问答技术，为开发者提供智能的代码理解和调试助手。

### 核心功能

🔍 **智能代码解析**
- 使用Tree-sitter准确解析C语言代码结构
- 提取函数定义、变量声明、调用关系等信息
- 构建完整的代码依赖关系图

📊 **知识图谱构建**
- 基于Neo4j存储代码关系数据
- 支持复杂的图查询和关系分析
- 可视化代码结构和依赖关系

🧠 **AI驱动的智能分析**
- LLM生成代码摘要和向量嵌入
- 语义级代码搜索和相似性推荐
- 自然语言问答和调试建议

⚡ **增量处理优化**
- 基于Git变更的增量分析
- 智能缓存机制提升性能
- 支持大规模项目处理

## 技术亮点

### 🏗️ 技术架构

**设计原则:** KISS + SOLID + TDD + YAGNI

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   C 源代码文件   │───▶│  Tree-sitter   │───▶│   结构化数据    │
│  (OpenSBI项目)  │    │   C语言解析器   │    │  (函数/调用图)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             ▼
                       │  智能问答系统   │    ┌─────────────────┐
                       │  (OpenRouter)   │◀───│  Neo4j 图数据库 │
                       └─────────────────┘    │   (代码关系)   │
                                │             └─────────────────┘
                                ▼                       │
                       ┌─────────────────┐             ▼
                       │   CodeQAService │    ┌─────────────────┐
                       │  (统一问答服务)  │◀───│ Chroma 向量数据库│
                       └─────────────────┘    │  (语义搜索)    │
                                              └─────────────────┘
```

**核心组件:**
- **CParser**: Tree-sitter C语言解析器
- **Neo4jGraphStore**: 图数据库存储 (代码结构关系)
- **CodeQAService**: 统一问答服务 (向量化+语义搜索+LLM问答)
- **ConfigManager**: 配置管理 (环境变量+YAML)

### 🛠️ **技术栈**
- **后端**：Python 3.9+ (异步处理，类型提示)
- **代码解析**：Tree-sitter + tree-sitter-c
- **图数据库**：Neo4j Community Edition
- **向量数据库**：Chroma
- **AI模型**：jina-embeddings-v2-base-code, CodeBERT
- **CLI框架**：argparse, tqdm

## 安装和使用

### 环境要求
- **Python 3.11+** (推荐使用uv虚拟环境)
- **Ubuntu 24.04 LTS** (WSL2 已验证兼容)
- **Neo4j Community Edition 5.26+** (Docker容器部署)
- **Git**
- **8GB+ RAM** (推荐)

### Ubuntu环境安装

#### 1. 创建Python虚拟环境
```bash
# 创建uv虚拟环境
uv venv --python 3.11

# 激活虚拟环境
source .venv/bin/activate

# 验证Python版本
python --version  # 应该是3.11+
```

#### 2. 安装核心依赖
```bash
# Tree-sitter (C语言解析器)
sudo apt install libtree-sitter-dev
pip install tree-sitter tree-sitter-c

# Chroma向量数据库
pip install chromadb>=1.0.13

# jina-embeddings模型
pip install -U sentence-transformers>=3.0.0

# dotenv支持
pip install python-dotenv

# 其他依赖
pip install pytest flake8 mypy pyyaml requests neo4j>=5.25.0 tqdm colorama
```

#### 3. 启动Neo4j (Docker容器)
```bash
# 创建数据卷
docker volume create neo4j_data
docker volume create neo4j_logs

# 启动Neo4j容器
docker run -d --name neo4j-community \
  --restart always \
  -p 7474:7474 -p 7687:7687 \
  -v neo4j_data:/data \
  -v neo4j_logs:/logs \
  -e NEO4J_AUTH=neo4j/neo4j \
  neo4j:5.26-community

# 验证安装
docker ps | grep neo4j
curl http://localhost:7474  # 访问Web界面
```

#### 4. 配置环境变量 (重要)
```bash
# 创建.env文件 (包含敏感信息，不要提交到Git)
cat > .env << EOF
NEO4J_PASSWORD=your_password
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
OPENROUTER_API_KEY=your_api_key
VERBOSE=true
EOF
```

> **安全提示**: 所有敏感信息（如密码和API密钥）都应通过.env文件或环境变量提供，而不是直接存储在配置文件中。确保将.env文件添加到.gitignore以防止意外提交。

### 🎯 POC目标

证明Tree-sitter + Neo4j + Chroma + OpenRouter能协同工作，完成一个中型项目（C语言）解析到问答的端到端流程。

**测试项目：** OpenSBI (RISC-V开源固件)
- 项目规模：289个文件，48,744行代码
- 项目路径：`reference_code_repo/opensbi/`
- 核心技术：Tree-sitter-c + Neo4j + Chroma + OpenRouter (google/gemini-2.0-flash-001)
- **LLM服务状态：** ✅ Jina嵌入模型 + ✅ OpenRouter API 已验证

### 快速开始 (POC版本)

#### 验证环境
```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行环境测试
python -m pytest tests/unit/test_ubuntu_environment.py -v

# 测试Neo4j连接
python -m pytest tests/integration/test_story_1_3_acceptance.py -v

# 验证LLM服务 ✅
python tests/jina-test.py          # 测试嵌入模型
python tests/openrouter_test.py   # 测试OpenRouter API
```

#### 基本使用

```bash
# 安装开发版本
pip install -e .

# 检查系统状态
code-learner status --verbose

# 分析项目代码
code-learner analyze reference_code_repo/opensbi/ --threads 8

# 交互式问答
code-learner query --project reference_code_repo/opensbi/ --function sbi_init

# 导出分析结果
code-learner export --project reference_code_repo/opensbi/ --format html --output opensbi_analysis.html
```

#### 专用命令

```bash
# 分析函数调用关系
call-graph main --format mermaid --output call_graph.md

# 分析依赖关系
dependency-graph analyze reference_code_repo/opensbi/

# 生成依赖图
dependency-graph graph --format mermaid --scope module --output deps.md

# 检测循环依赖
dependency-graph cycle
```

#### 开发者测试
```bash
# 测试C语言解析器
python -m pytest tests/unit/test_c_parser.py -v

# 测试Neo4j存储
python -m pytest tests/integration/test_story_1_3_acceptance.py -v

# 测试函数调用分析
python -m pytest tests/integration/test_story_2_1_4_acceptance.py -v

# 测试依赖关系分析
python -m pytest tests/integration/test_story_2_2_acceptance.py -v

# 详细日志模式
VERBOSE=true python -m pytest tests/integration/test_story_1_3_acceptance.py -v -s
```

### 主要命令

#### 🔍 代码分析命令
```bash
# 分析C代码项目
code-learner analyze <项目路径> [选项]

# 选项:
# --output-dir, -o: 指定输出目录
# --incremental, -i: 增量分析（只分析变更文件）
# --include: 包含的文件模式
# --exclude: 排除的文件模式
# --threads, -t: 并行处理线程数

# 示例 - 基本分析
code-learner analyze reference_code_repo/opensbi/

# 示例 - 增量分析，排除测试文件
code-learner analyze reference_code_repo/opensbi/ --incremental --exclude "test/*,examples/*"

# 示例 - 指定输出目录和线程数
code-learner analyze reference_code_repo/opensbi/ --output-dir ./analysis_results --threads 8
```

#### 💬 交互式问答命令
```bash
# 启动交互式问答会话
code-learner query --project <项目路径> [选项]

# 选项:
# --project, -p: 项目路径（必需）
# --history, -H: 保存历史记录的文件
# --function, -f: 聚焦于特定函数
# --file: 聚焦于特定文件

# 示例 - 基本问答
code-learner query --project reference_code_repo/opensbi/

# 示例 - 聚焦于特定函数，保存历史记录
code-learner query --project reference_code_repo/opensbi/ --function sbi_init --history ./query_history.json
```

#### 🔄 系统状态检查
```bash
# 检查系统各组件状态
code-learner status [--verbose, -v]

# 示例 - 详细状态检查
code-learner status --verbose
```

#### 📤 导出分析结果
```bash
# 导出分析结果
code-learner export --project <项目路径> --format <格式> --output <输出文件> [选项]

# 选项:
# --project, -p: 项目路径（必需）
# --format, -f: 导出格式（json, md, html, dot）
# --output, -o: 输出文件路径（必需）
# --type, -t: 导出数据类型（calls, deps, all）

# 示例 - 导出为HTML格式
code-learner export --project reference_code_repo/opensbi/ --format html --output opensbi_analysis.html

# 示例 - 只导出调用关系
code-learner export --project reference_code_repo/opensbi/ --format json --output calls.json --type calls
```

#### 📊 函数调用图谱命令
```bash
# 生成函数调用图谱
call-graph <函数名> [选项]

# 选项:
# --depth, -d: 最大深度（默认为3）
# --format, -f: 输出格式（mermaid, json, ascii）
# --output, -o: 输出文件路径
# --html: 生成HTML查看器

# 示例 - 显示ASCII树
call-graph main --format ascii

# 示例 - 生成Mermaid图
call-graph main --format mermaid --output call_graph.md

# 示例 - 生成HTML查看器
call-graph sbi_init --depth 5 --format json --output graph.json --html
```

#### 🔗 依赖关系分析命令
```bash
# 分析依赖关系
dependency-graph <子命令> [选项]

# 子命令:
# analyze: 分析项目依赖关系
# file: 分析单个文件的依赖关系
# graph: 生成依赖关系图
# cycle: 检测循环依赖

# 示例 - 分析项目依赖
dependency-graph analyze reference_code_repo/opensbi/

# 示例 - 检测循环依赖
dependency-graph cycle

# 示例 - 生成模块依赖图
dependency-graph graph --format mermaid --scope module --output deps.md
```

## 项目结构

```
code-repo-learner/
├── 001-dev-docs/               # 项目文档
│   ├── 00_prd.md               # 产品需求文档
│   ├── 01_architecture.md      # 技术架构文档
│   └── checklists/             # 质量检查清单
├── src/                        # 源代码
│   └── code_learner/          # 主要包
│       ├── cli/               # 命令行接口
│       │   ├── call_graph_cli.py  # 函数调用图CLI
│       │   └── dependency_cli.py  # 依赖分析CLI
│       ├── config/            # 配置管理
│       ├── core/              # 核心数据模型和接口
│       ├── llm/               # LLM服务
│       │   ├── call_graph_service.py  # 调用图服务
│       │   ├── dependency_service.py  # 依赖分析服务
│       │   └── embedding_engine.py    # 嵌入引擎
│       ├── parser/            # 代码解析引擎
│       └── storage/           # 数据存储
├── tests/                     # 测试文件
└── config/                    # 配置文件
```

## 已实现功能

### 1. 函数调用关系分析 ✅
- 提取函数调用关系（直接调用、指针调用、成员调用、递归调用）
- 构建函数调用图
- 生成多种格式的可视化图表（Mermaid、JSON、ASCII、HTML）

### 2. 依赖关系分析 ✅
- 提取文件依赖关系（#include语句）
- 区分系统头文件和项目头文件
- 构建模块依赖图
- 检测循环依赖问题
- 计算项目模块化评分

## 详细使用说明

详细的CLI使用说明请参考 [CLI使用指南](001-dev-docs/CLI_USAGE_GUIDE.md)。

## 项目状态

### 🚀 开发进度

**Phase 1 POC** (进行中)
- **Epic 1**: ✅ 核心技术验证 (100% 完成)
  - Story 1.1: ✅ Ubuntu环境搭建与配置系统
  - Story 1.2: ✅ Tree-sitter C语言解析器实现  
  - Story 1.3: ✅ Neo4j图数据库存储
  - Story 1.4: ✅ 向量嵌入与问答 (LLM服务验证完成)

- **Epic 2**: 🔄 高级分析功能开发 (4个Story) - **进行中**
  - Story 2.1: ✅ 函数调用关系分析 (1.5天) - **已完成**
    - Story 2.1.1: ✅ 接口设计扩展 (完成)
    - Story 2.1.2: ✅ 数据模型扩展 (完成)
    - Story 2.1.3: ✅ Tree-sitter函数调用提取 (完成)
    - Story 2.1.4: ✅ 调用图谱可视化服务 (完成)
  - Story 2.2: 🔄 依赖关系分析 (0.7天) - **下一步**
  - Story 2.3: 📋 调用图谱可视化 (1天)
  - Story 2.4: 📋 未使用函数检测 (0.5天)

- **Epic 3**: 📋 基础优化 (3个Story)  
- **Epic 4**: 📋 MVP准备 (3个Story)

**当前焦点**: Story 2.1 ✅ 完成，Story 2.2 准备开始

**项目整体进度**: Epic 1 (100%) + Story 2.1 (100%) = **42.9%** 🚀

### 🧪 测试状态

**单元测试覆盖率**: >90%
- ✅ CParser: 12/12 测试通过
- ✅ ConfigManager: 9/9 测试通过
- ✅ Neo4jGraphStore: 9/9 测试通过
- ✅ DataModels: 6/6 测试通过
- ✅ CallGraphService: 15/15 测试通过

**集成测试状态**:
- ✅ Story 1.1-1.4 验收测试: 100% 通过
- ✅ Story 2.1.3 验收测试: 8/8 通过 (函数调用提取)
- ✅ Story 2.1.4 验收测试: 8/8 通过 (调用图谱可视化)

**LLM服务验证**: ✅ 完成
- ✅ Jina嵌入模型 (768维向量，0.09秒编码时间)
- ✅ OpenRouter API (google/gemini-2.0-flash-001)
- ✅ 配置管理和错误处理
- ✅ 性能基准测试
- ✅ Qwen3模型评估完成 (保持Jina模型)

### 🎯 Epic 2 技术亮点

**多路分析架构**:
- **Tree-sitter**: 结构化代码解析 (函数调用关系)
- **Neo4j**: 图关系存储 (CALLS关系、调用图谱)
- **Chroma**: 语义向量存储 (RAG检索)
- **SQLite**: 元数据统计 (fallback统计)

**函数调用分析**:
- 支持4种调用类型: direct、member、pointer、recursive
- 精确的Tree-sitter AST遍历提取
- Neo4j CALLS关系存储，包含调用类型和上下文
- 多格式调用图谱可视化: Mermaid、JSON、ASCII、HTML

**依赖关系分析** (计划):
- 头文件依赖提取和分析
- 模块依赖关系识别
- 循环依赖检测
- 依赖图谱可视化 (生成文件和模块级别的依赖图谱)

### 🎯 里程碑

- **2025-06-23**: Epic 1 完成，所有核心技术验证成功
- **2025-06-24**: Epic 2 深度设计完成，Story 2.1 启动
- **2025-06-25**: Story 2.1 完成 (函数调用关系分析)
- **预计2025-06-27**: Story 2.2 完成 (依赖关系分析)
- **预计2025-06-30**: Epic 2 完成 (高级分析功能)
- **预计2025-07-05**: Phase 1 POC完成

---

*这个工具旨在提升C语言开发者的代码理解和调试效率，通过AI技术降低代码维护的复杂度。*

## 📊 项目进度总览

### Epic 1: 基础环境搭建与核心功能 ✅ 已完成
- **Story 1.1**: 基础环境搭建与配置系统 ✅ 
- **Story 1.2**: C语言解析器实现 ✅ 
- **Story 1.3**: Neo4j图存储实现 ✅ 
- **Story 1.4**: LLM服务集成 ✅ 

### Epic 2: 函数调用关系分析与多模态RAG 🔄 进行中
- **Story 2.1**: 函数调用关系分析 ✅ **已完成** (2025-06-25)
  - **Story 2.1.1**: 接口设计扩展 ✅ **已完成** (2025-01-20)
  - **Story 2.1.2**: 数据模型扩展 ✅ **已完成** (2025-01-20)
  - **Story 2.1.3**: Tree-sitter函数调用提取 ✅ **已完成** (2025-06-25)
  - **Story 2.1.4**: 调用图谱可视化服务 ✅ **已完成** (2025-06-25)
- **Story 2.2**: 依赖关系分析 🔄 **下一步** (0.7天)
- **Story 2.3**: 调用图谱可视化 📋 待处理 (1天)
- **Story 2.4**: 未使用函数检测 📋 待处理 (0.5天)

### 最新完成工作 (2025-06-25)

#### ✅ Story 2.1.3: Tree-sitter函数调用提取
- **核心功能**: 基于Tree-sitter AST实现精确的函数调用提取
- **支持类型**: direct、member、pointer、recursive四种调用类型
- **Neo4j存储**: CALLS关系存储，包含调用类型和上下文信息
- **测试覆盖**: 8/8测试通过，覆盖率>78%

#### ✅ Story 2.1.4: 调用图谱可视化服务
- **CallGraphService**: 支持Neo4j图谱查询，可变长度路径，深度控制
- **多格式输出**: Mermaid、JSON、ASCII、HTML四种格式
- **CLI工具**: call-graph命令行工具，支持多种输出和文件导出
- **测试覆盖**: 单元测试15/15，集成测试8/8，验收测试8/8全部通过

### 🎯 下一步工作 - Story 2.2: 依赖关系分析

**主要任务**:
- 头文件依赖分析 (#include语句提取和分析)
- 模块依赖分析 (基于目录结构识别模块)
- 循环依赖检测 (检测项目中的循环依赖问题)
- 依赖图谱可视化 (生成文件和模块级别的依赖图谱)

**预计工作量**: 0.7天
**优先级**: 高 