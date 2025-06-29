# C语言智能代码分析调试工具 - CLI使用指南

本文档提供了C语言智能代码分析调试工具命令行界面的详细使用说明。

## 安装

确保已安装所有依赖：

```bash
pip install -e .
```

## 可用命令

工具提供以下主要命令：

- `code-learner` - 主命令，提供完整的项目分析和查询功能
- `call-graph` - 专注于函数调用图谱生成
- `dependency-graph` - 专注于依赖关系分析
- `code-learner-all` - 统一命令，一键执行所有分析功能（推荐）

## 项目隔离机制

**重要更新**：系统现在支持完全的项目隔离机制，确保不同代码仓库的数据不会相互干扰。

### 项目ID自动生成

- 当分析项目时，系统会自动为每个项目生成唯一的项目ID
- 项目ID基于项目路径的哈希值生成，格式为：`auto_xxxxxxxx`
- 所有数据（Neo4j节点、Chroma集合）都会标记项目ID，实现完全隔离

### 项目隔离的好处

- **数据安全**：不同项目的函数、文件不会混合
- **查询准确**：只从当前项目检索相关信息
- **并行分析**：可以同时分析多个项目而不冲突

## 统一命令行工具 (code-learner-all)

**新增功能**：统一命令行工具整合了代码分析、调用图和依赖分析功能，提供一键式分析体验。

### 基本用法

```bash
code-learner-all <项目路径> [选项]
```

### 选项说明

| 选项 | 简写 | 描述 |
|------|------|------|
| `--output-dir` | `-o` | 指定输出目录，默认为`data/<项目名>_analysis` |
| `--include` | | 包含的文件模式，逗号分隔（例如：`"*.c,*.h"`） |
| `--exclude` | | 排除的文件模式，逗号分隔（例如：`"test/*"`） |
| `--threads` | `-t` | 并行处理线程数 |
| `--verbose` | `-v` | 显示详细日志 |

### 示例用法

```bash
# 基本分析
code-learner-all /path/to/project

# 指定输出目录
code-learner-all /path/to/project --output-dir ./my_analysis

# 过滤特定文件
code-learner-all /path/to/project --include "*.c,*.h" --exclude "test/*"

# 使用多线程加速
code-learner-all /path/to/project --threads 8

# 显示详细日志
code-learner-all /path/to/project --verbose
```

### 工作流程

统一命令行工具执行以下步骤：

1. **代码分析**：
   - 解析项目中的C语言代码
   - 提取函数、调用关系、依赖关系等
   - 存储到Neo4j图数据库
   - 生成代码嵌入，存储到Chroma向量数据库

2. **依赖分析**：
   - 分析项目中文件之间的依赖关系
   - 检测循环依赖
   - 计算模块化评分
   - 生成依赖图（Mermaid格式）

3. **调用图分析**：
   - 识别项目中的主要函数
   - 为每个主要函数生成调用图
   - 以Mermaid格式保存调用图

### 输出内容

分析完成后，输出目录将包含：

- `dependency_graph.md`：项目依赖关系图（Mermaid格式）
- `call_graph_<函数名>.md`：主要函数的调用图（Mermaid格式）
- `.analysis/`：分析元数据和中间结果
  - `info.json`：包含项目ID和其他分析信息

### 项目ID

分析过程中会生成并显示项目ID，格式为`auto_xxxxxxxx`。这个ID在后续查询中非常重要，用于确保只检索当前项目的数据。

### 错误处理

统一命令行工具会处理各种错误情况：

- 数据库连接失败
- 代码解析错误
- 依赖分析或调用图生成失败

即使某个步骤失败，工具也会尝试继续执行其他步骤，并在最后提供完整的状态报告。

## code-learner 命令

### 分析项目

分析C代码项目，提取函数、调用关系和依赖关系：

```bash
code-learner analyze /path/to/project
```

#### 选项

- `--output-dir, -o` - 指定输出目录（默认为项目目录下的.analysis）
- `--incremental, -i` - 增量分析，只处理变更文件
- `--include` - 包含的文件模式，逗号分隔（默认为"*.c,*.h"）
- `--exclude` - 排除的文件模式，逗号分隔
- `--threads, -t` - 并行处理线程数（默认为4）

#### 示例

```bash
# 基本分析 - 系统自动生成项目ID
code-learner analyze /home/user/opensbi

# 增量分析，排除测试文件
code-learner analyze /home/user/opensbi --incremental --exclude "test/*,examples/*"

# 指定输出目录和线程数
code-learner analyze /home/user/opensbi --output-dir ./analysis_results --threads 8

# 分析多个项目（每个项目自动获得独立的项目ID）
code-learner analyze /home/user/project1
code-learner analyze /home/user/project2  # 与project1完全隔离
```

### 交互式问答

启动交互式问答会话，直接针对代码库提问：

```bash
code-learner query --project /path/to/project
```

#### 智能上下文召回机制 🚀 **最新更新**

查询功能采用**多源智能上下文召回**策略，确保回答的准确性和完整性：

1. **意图分析器**：
   - 使用LLM智能分析用户问题
   - 自动提取函数名、文件名、变量名等代码实体
   - 识别问题类型（函数分析、调用关系、文件分析等）
   - 生成多个优化的搜索查询

2. **Neo4j图数据库召回**：
   - 函数的完整代码和定义
   - 精确的函数调用关系（谁调用了这个函数，这个函数调用了谁）
   - 结构化的代码图谱信息
   - 基于代码实体的精确检索

3. **Chroma向量数据库召回**：
   - 通过语义相似性检索相关代码片段
   - 使用问题的嵌入向量找到最相关的代码块
   - 多查询策略：基于原问题、函数名、关键词等构建多个查询
   - 返回top-k个最相似的代码片段，带相似度评分

4. **文件系统直接召回**：
   - 如果指定了focus_file，直接读取完整文件内容
   - 提供最新的代码状态

5. **项目隔离保证**：
   - 所有召回的上下文都严格限制在当前项目范围内
   - 不会混入其他项目的代码信息

#### 选项

- `--project, -p` - 项目路径（必需）
- `--history, -H` - 保存历史记录的文件
- `--function, -f` - 聚焦于特定函数
- `--file` - 聚焦于特定文件

#### 示例

```bash
# 基本问答 - 从项目的所有数据源召回上下文
code-learner query --project /home/user/opensbi

# 聚焦于特定函数，保存历史记录
code-learner query --project /home/user/opensbi --function sbi_init --history ./query_history.json

# 聚焦于特定文件
code-learner query --project /home/user/opensbi --file lib/sbi/sbi_init.c

# 多项目查询示例（每个项目独立的上下文）
code-learner query --project /home/user/project1  # 只访问project1的数据
code-learner query --project /home/user/project2  # 只访问project2的数据
```

#### 示例问题

在交互式问答会话中，可以提问如下问题：

- "sbi_init函数的作用是什么？"
- "哪些函数调用了sbi_console_putc？"
- "文件lib/sbi/sbi_init.c中定义了哪些函数？"
- "项目中有哪些循环依赖？"
- "哪个模块依赖最多？"
- "文件sbi_hart.c和sbi_init.c之间的依赖关系是什么？"
- "这个函数的复杂度如何？"
- "有哪些函数可能存在性能问题？"
- "what is sbi_system_suspend_set_device？"  # 支持英文问题

### 系统状态检查

检查系统各组件状态：

```bash
code-learner status
```

#### 选项

- `--verbose, -v` - 显示详细信息，包括：
  - **Neo4j数据库**：连接状态、健康检查、节点统计
  - **嵌入模型**：状态、缓存路径、模型维度
  - **LLM API**：连接状态、响应时间、模型信息
  - **Chroma向量数据库**：集合信息、chunk统计、项目隔离状态
  - **代码块（Chunk）详细信息**：
    - 每个项目的chunk数量
    - 不同类型chunk的分布（函数、注释、结构体等）
    - chunk的元数据完整性
    - 向量嵌入质量评分

#### 示例

```bash
# 基本状态检查
code-learner status

# 详细状态检查（包含chunk信息）
code-learner status --verbose
```

**详细模式输出示例**：
```
系统状态检查结果:
整体状态: healthy

组件状态:
✅ database: healthy
  - uri: bolt://localhost:7687
  - nodes: 15,234 functions, 892 files
  - health_score: 0.98

✅ embedding_model: healthy
  - model: jinaai/jina-embeddings-v2-base-code
  - dimensions: 768
  - cache_path: /home/user/.cache/torch/sentence_transformers

✅ llm_api: healthy
  - model: google/gemini-2.0-flash-001
  - response_time: 1.2s

✅ vector_database: healthy
  - collections: 3 active projects
  - total_chunks: 8,823
  - chunk_distribution:
    * functions: 3,245 (37%)
    * comments: 2,156 (24%)
    * structures: 1,892 (21%)
    * others: 1,530 (18%)
  - metadata_completeness: 94%
  - embedding_quality: 0.96
```

### 导出分析结果

导出分析结果为各种格式：

```bash
code-learner export --project /path/to/project --format html --output results.html
```

#### 选项

- `--project, -p` - 项目路径（必需）
- `--format, -f` - 导出格式（json, md, html, dot）
- `--output, -o` - 输出文件路径（必需）
- `--type, -t` - 导出数据类型（calls, deps, all）

#### 示例

```bash
# 导出为HTML格式（只包含当前项目的数据）
code-learner export --project /home/user/opensbi --format html --output opensbi_analysis.html

# 只导出调用关系
code-learner export --project /home/user/opensbi --format json --output calls.json --type calls

# 导出依赖关系图
code-learner export --project /home/user/opensbi --format dot --output deps.dot --type deps
```

## call-graph 命令

`call-graph`命令专注于函数调用图谱的生成和分析，适用于以下场景：

### 何时使用call-graph命令

1. **函数调用关系分析**：
   - 想要了解特定函数的调用链
   - 分析函数之间的依赖关系
   - 查找函数的调用者和被调用者

2. **代码重构准备**：
   - 重构前需要了解函数的影响范围
   - 确定删除函数的安全性
   - 分析模块间的耦合度

3. **快速原型分析**：
   - 只需要调用图信息，不需要完整的代码分析
   - 轻量级分析，处理速度更快
   - 适合大型项目的初步探索

### 基本用法

```bash
# 生成整个项目的调用图
call-graph /path/to/project

# 分析特定函数的调用关系
call-graph /path/to/project --function main

# 生成DOT格式的调用图
call-graph /path/to/project --output-format dot
```

### 选项说明

- `--function, -f` - 指定要分析的函数名
- `--output-format` - 输出格式（json, dot, svg）
- `--max-depth` - 调用链的最大深度
- `--include-external` - 包含外部函数调用
- `--verbose, -v` - 显示详细的调用信息和统计数据

### 示例输出（--verbose模式）

```
调用图分析结果:
📊 统计信息:
  - 总函数数: 245
  - 调用关系数: 1,127
  - 最大调用深度: 8
  - 递归函数: 3

🔍 热点函数 (被调用次数最多):
  1. malloc() - 被调用 45 次
  2. printf() - 被调用 32 次  
  3. strcpy() - 被调用 28 次

📈 调用链分析:
  - 最长调用链: main -> init_system -> load_config -> parse_file -> read_line
  - 孤立函数: cleanup_temp, debug_helper
```

## dependency-graph 命令

`dependency-graph`命令专注于依赖关系分析，适用于以下场景：

### 何时使用dependency-graph命令

1. **模块依赖分析**：
   - 了解文件之间的包含关系
   - 分析头文件的依赖链
   - 检测循环依赖问题

2. **构建系统优化**：
   - 优化编译顺序
   - 减少不必要的依赖
   - 模块化重构指导

3. **架构理解**：
   - 理解项目的层次结构
   - 识别核心模块和边缘模块
   - 分析模块间的耦合程度

4. **依赖问题诊断**：
   - 查找缺失的依赖
   - 检测循环依赖
   - 分析依赖冲突

### 基本用法

```bash
# 生成整个项目的依赖图
dependency-graph /path/to/project

# 分析特定文件的依赖
dependency-graph /path/to/project --file main.c

# 检测循环依赖
dependency-graph /path/to/project --check-cycles

# 生成依赖层次图
dependency-graph /path/to/project --show-layers
```

### 选项说明

- `--file, -f` - 指定要分析的文件
- `--check-cycles` - 检测并报告循环依赖
- `--show-layers` - 显示依赖层次结构
- `--include-system` - 包含系统头文件
- `--output-format` - 输出格式（json, dot, svg）
- `--verbose, -v` - 显示详细的依赖信息和统计数据

### 示例输出（--verbose模式）

```
依赖关系分析结果:
📊 统计信息:
  - 总文件数: 67
  - 依赖关系数: 234
  - 最大依赖深度: 6
  - 循环依赖: 发现 2 个

⚠️  循环依赖检测:
  1. header1.h -> header2.h -> header3.h -> header1.h
  2. module_a.h -> module_b.h -> module_a.h

📈 依赖层次:
  Layer 0 (基础层): stdio.h, stdlib.h, string.h
  Layer 1 (工具层): utils.h, logger.h, config.h  
  Layer 2 (核心层): engine.h, parser.h
  Layer 3 (应用层): main.h, cli.h

🔍 热点文件 (被依赖次数最多):
  1. utils.h - 被依赖 23 次
  2. config.h - 被依赖 18 次
  3. logger.h - 被依赖 15 次
```

## 命令选择指南

### 使用code-learner-all（统一命令）当你需要：
- **一站式分析**：一键完成代码分析、调用图和依赖分析
- **简化工作流**：无需记住多个命令和参数
- **统一输出**：所有分析结果保存在同一目录
- **自动项目ID**：自动生成和显示项目ID
- **完整报告**：包含依赖图和主要函数的调用图

### 使用code-learner（主命令）当你需要：
- **完整的代码分析**：包括函数提取、调用关系、依赖分析、向量化存储
- **智能问答功能**：基于AI的代码理解和问答
- **项目管理**：长期维护和增量更新
- **多数据源查询**：结合Neo4j图数据库和Chroma向量数据库

### 使用call-graph当你需要：
- **专注调用关系**：只关心函数之间的调用关系
- **快速分析**：不需要完整的代码解析，只要调用图
- **重构准备**：了解函数的影响范围
- **性能优化**：识别热点函数和调用瓶颈

### 使用dependency-graph当你需要：
- **专注依赖关系**：只关心文件之间的依赖关系
- **构建优化**：优化编译顺序和依赖管理
- **架构分析**：理解项目的模块化程度
- **问题诊断**：检测循环依赖和依赖冲突

## 性能对比

| 命令 | 分析速度 | 内存使用 | 功能完整性 | 适用场景 |
|------|----------|----------|------------|----------|
| code-learner-all | 中 | 高 | 完整 | 一站式分析 |
| code-learner | 慢 | 高 | 完整 | 深度分析、AI问答 |
| call-graph | 快 | 中 | 专项 | 调用关系分析 |
| dependency-graph | 快 | 低 | 专项 | 依赖关系分析 |

## 项目管理最佳实践

### 多项目工作流

```bash
# 1. 使用统一命令分析第一个项目
code-learner-all /home/user/linux-kernel --output-dir ./linux_analysis
# 系统生成项目ID: auto_abc12345

# 2. 分析第二个项目（完全独立）
code-learner-all /home/user/opensbi --output-dir ./opensbi_analysis
# 系统生成项目ID: auto_def67890

# 3. 查询时自动识别项目
code-learner query --project /home/user/linux-kernel  # 只访问linux-kernel数据
code-learner query --project /home/user/opensbi       # 只访问opensbi数据
```

### 性能优化建议

- **大型项目**：增加线程数可以加速分析过程
- **增量分析**：使用`--incremental`减少重复处理
- **文件过滤**：排除测试文件和示例代码提高效率
- **分批处理**：对于超大项目，可以先分析核心目录

### 数据清理

如果需要重新分析项目或清理数据：

```bash
# 重新分析会自动覆盖同一项目的旧数据
code-learner-all /home/user/opensbi  # 重新分析，保持相同项目ID

# 系统会自动管理项目隔离，无需手动清理
```

## 常见问题

### 数据库连接错误

确保Neo4j数据库已启动：

```bash
docker ps | grep neo4j
```

如果没有运行，启动Neo4j容器：

```bash
docker run -d --name neo4j-community -p 7474:7474 -p 7687:7687 -v neo4j_data:/data -v neo4j_logs:/logs -e NEO4J_AUTH=neo4j/your_password neo4j:5.26-community
```

### 嵌入模型错误

首次运行时，嵌入模型需要下载，可能需要一些时间。如果模型缓存损坏，可以删除缓存目录：

```bash
rm -rf ~/.cache/torch/sentence_transformers/models--jinaai--jina-embeddings-v2-base-code
```

### API密钥配置

确保已设置必要的环境变量：

```bash
export NEO4J_PASSWORD=your_password
export OPENROUTER_API_KEY=your_api_key
```

或者创建`.env`文件：

```
NEO4J_PASSWORD=your_password
OPENROUTER_API_KEY=your_api_key
```

### 项目隔离问题

如果遇到项目数据混合的问题：

1. 检查项目路径是否正确
2. 确认系统日志中显示的项目ID
3. 重新分析项目以刷新数据

### 查询上下文不准确

如果查询结果不准确：

1. 确保项目已完成分析
2. 检查Neo4j和Chroma数据库状态
3. 使用`--function`或`--file`参数聚焦特定范围
4. 查看详细日志了解上下文召回情况

### Chunk数据质量问题

如果chunk信息显示质量较低：

1. 重新运行分析以刷新向量嵌入
2. 检查源代码文件编码是否正确
3. 确认嵌入模型已正确加载
4. 使用`--verbose`查看详细的chunk统计信息

## 高级功能

### 向量检索调优

系统使用Jina嵌入模型进行语义检索，默认参数：
- 嵌入维度：768
- 检索数量：top-3
- 相似度阈值：自动优化

### 图数据库查询

支持复杂的图查询，包括：
- 函数调用链分析
- 依赖关系遍历
- 循环依赖检测
- 模块化度量

### 多模态分析

结合结构化图数据和向量语义检索，提供：
- 精确的代码结构分析
- 语义相似的代码发现
- 上下文感知的代码问答

### 智能意图分析

最新的意图分析器能够：
- 自动识别问题类型（函数分析、调用关系、文件分析等）
- 提取代码实体（函数名、文件名、变量名）
- 生成优化的搜索策略
- 支持中英文混合问题 