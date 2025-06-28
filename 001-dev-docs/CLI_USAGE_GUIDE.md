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

#### 智能上下文召回机制

查询功能采用**多源上下文召回**策略，确保回答的准确性和完整性：

1. **Neo4j图数据库召回**：
   - 函数的完整代码
   - 函数调用关系（谁调用了这个函数，这个函数调用了谁）
   - 结构化的代码图谱信息

2. **Chroma向量数据库召回**：
   - 通过语义相似性检索相关代码片段
   - 使用问题的嵌入向量找到最相关的代码块
   - 返回top-k个最相似的代码片段，带相似度评分

3. **文件系统直接召回**：
   - 如果指定了focus_file，直接读取完整文件内容
   - 提供最新的代码状态

4. **项目隔离保证**：
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

### 系统状态检查

检查系统各组件状态：

```bash
code-learner status
```

#### 选项

- `--verbose, -v` - 显示详细信息，包括：
  - Neo4j数据库连接状态和健康检查
  - 嵌入模型状态和缓存路径
  - LLM API连接状态和响应时间

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

生成函数调用图谱：

```bash
call-graph main
```

### 选项

- `--depth, -d` - 最大深度（默认为3）
- `--format, -f` - 输出格式（mermaid, json, ascii）
- `--output, -o` - 输出文件路径
- `--html` - 生成HTML查看器

### 示例

```bash
# 显示ASCII树
call-graph main --format ascii

# 生成Mermaid图
call-graph main --format mermaid --output call_graph.md

# 生成HTML查看器
call-graph sbi_init --depth 5 --format json --output graph.json --html
```

## dependency-graph 命令

分析依赖关系：

```bash
dependency-graph analyze /path/to/project
```

### 子命令

- `analyze` - 分析项目依赖关系
- `file` - 分析单个文件的依赖关系
- `graph` - 生成依赖关系图
- `cycle` - 检测循环依赖

### 示例

```bash
# 分析项目依赖
dependency-graph analyze /home/user/opensbi

# 检测循环依赖
dependency-graph cycle

# 生成模块依赖图
dependency-graph graph --format mermaid --scope module --output deps.md
```

## 项目管理最佳实践

### 多项目工作流

```bash
# 1. 分析第一个项目
code-learner analyze /home/user/linux-kernel
# 系统生成项目ID: auto_abc12345

# 2. 分析第二个项目（完全独立）
code-learner analyze /home/user/opensbi  
# 系统生成项目ID: auto_def67890

# 3. 查询时自动识别项目
code-learner query --project /home/user/linux-kernel  # 只访问linux-kernel数据
code-learner query --project /home/user/opensbi       # 只访问opensbi数据

# 4. 导出时也是项目隔离的
code-learner export --project /home/user/linux-kernel --format html --output linux.html
code-learner export --project /home/user/opensbi --format html --output opensbi.html
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
code-learner analyze /home/user/opensbi  # 重新分析，保持相同项目ID

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