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
# 基本分析
code-learner analyze /home/user/opensbi

# 增量分析，排除测试文件
code-learner analyze /home/user/opensbi --incremental --exclude "test/*,examples/*"

# 指定输出目录和线程数
code-learner analyze /home/user/opensbi --output-dir ./analysis_results --threads 8
```

### 交互式问答

启动交互式问答会话，直接针对代码库提问：

```bash
code-learner query --project /path/to/project
```

#### 选项

- `--project, -p` - 项目路径（必需）
- `--history, -H` - 保存历史记录的文件
- `--function, -f` - 聚焦于特定函数
- `--file` - 聚焦于特定文件

#### 示例

```bash
# 基本问答
code-learner query --project /home/user/opensbi

# 聚焦于特定函数，保存历史记录
code-learner query --project /home/user/opensbi --function sbi_init --history ./query_history.json
```

#### 示例问题

在交互式问答会话中，可以提问如下问题：

- "sbi_init函数的作用是什么？"
- "哪些函数调用了sbi_console_putc？"
- "文件lib/sbi/sbi_init.c中定义了哪些函数？"
- "项目中有哪些循环依赖？"
- "哪个模块依赖最多？"
- "文件sbi_hart.c和sbi_init.c之间的依赖关系是什么？"

### 系统状态检查

检查系统各组件状态：

```bash
code-learner status
```

#### 选项

- `--verbose, -v` - 显示详细信息

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
# 导出为HTML格式
code-learner export --project /home/user/opensbi --format html --output opensbi_analysis.html

# 只导出调用关系
code-learner export --project /home/user/opensbi --format json --output calls.json --type calls
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

## 性能优化建议

- 对于大型项目，增加线程数可以加速分析过程
- 使用增量分析模式减少重复处理
- 排除测试文件和示例代码可以提高分析效率
- 对于非常大的项目，可以先分析特定目录，再逐步扩展

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