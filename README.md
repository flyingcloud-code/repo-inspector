# C语言智能代码分析调试工具

## 项目概述

本项目是一个针对C语言代码库的智能分析和问答工具，通过结合图数据库(Neo4j)、向量数据库(Chroma)和大语言模型，实现代码理解、问答和调试辅助功能。

## 主要功能

1. **代码分析**：解析C语言代码，提取函数、变量、调用关系等信息
2. **代码问答**：基于实际代码回答开发者问题，辅助理解代码逻辑
3. **调用关系可视化**：生成函数调用图，帮助理解代码结构
4. **依赖分析**：识别模块间依赖，发现潜在问题
5. **代码嵌入**：将代码转换为向量表示，支持语义搜索

## 安装与部署

请参考 [部署指南](001-dev-docs/DEPLOY_UBUNTU.md) 进行环境配置和安装。

## 使用方法

### 代码分析

```bash
# 分析整个代码库
code-learner analyze <项目路径>

# 分析特定文件
code-learner analyze --file <文件路径>
```

### 代码问答

```bash
# 启动交互式问答会话
code-learner query --project <项目路径>

# 聚焦于特定函数
code-learner query --project <项目路径> --function <函数名>

# 聚焦于特定文件
code-learner query --project <项目路径> --file <文件路径>

# 保存问答历史
code-learner query --project <项目路径> --history <历史文件路径>
```

### 生成调用图

```bash
# 生成特定函数的调用图
code-learner graph --function <函数名> --output <输出文件>
```

### 代码嵌入

```bash
# 使用tree-sitter策略生成代码嵌入（推荐，不依赖Neo4j）
code-learner embed-code --strategy tree_sitter --dir <项目路径>

# 使用固定大小分块策略生成代码嵌入
code-learner embed-code --strategy fixed_size --dir <项目路径> --chunk-size 512 --chunk-overlap 100

# 使用Neo4j中的语义单元生成代码嵌入
code-learner embed-code --strategy semantic

# 自定义集合名称和文件扩展名
code-learner embed-code --strategy tree_sitter --dir <项目路径> --collection my_embeddings --file-extensions .c,.h
```

## 代码分块策略

本项目支持三种代码分块策略，用于生成代码嵌入：

1. **Tree-sitter分块策略**（推荐）：
   - 使用tree-sitter直接解析代码，提取语义单元
   - 不依赖Neo4j数据库，可独立使用
   - 能识别函数、结构体、枚举、全局变量、宏定义等
   - 保留代码的语义完整性
   - 命令：`--strategy tree_sitter`

2. **固定大小分块策略**：
   - 按固定字符数分块，适用于任何文本文件
   - 简单高效，但可能切分语义单元
   - 可调整块大小和重叠参数
   - 命令：`--strategy fixed_size`

3. **Neo4j语义分块策略**：
   - 从Neo4j数据库中提取已解析的语义单元
   - 需要先运行代码分析命令
   - 依赖Neo4j数据库
   - 命令：`--strategy semantic`

## 当前状态与计划

### 已完成功能

- [x] 代码解析与存储
- [x] 基础问答界面
- [x] Neo4j图数据库集成
- [x] Chroma向量数据库集成
- [x] 调用关系分析
- [x] 代码问答功能修复 (2025-06-27)
  - [x] 实现从Neo4j检索函数代码
  - [x] 添加向量检索功能
  - [x] 增强上下文理解能力
- [x] 智能意图分析系统 (2025-06-28)
  - [x] 实现LLM驱动的用户问题分析
  - [x] 智能提取函数名、文件名和关键词
  - [x] 多查询向量检索策略
  - [x] Neo4j和Chroma双数据源集成
- [x] 多种代码分块策略 (2025-06-28)
  - [x] Tree-sitter分块策略（不依赖Neo4j）
  - [x] 固定大小分块策略
  - [x] Neo4j语义分块策略

### 计划功能

- [ ] 代码质量分析
- [ ] 自动化测试生成
- [ ] 多语言支持扩展

## 技术架构

本项目采用模块化设计，主要组件包括：

1. **解析器**：使用Tree-sitter解析C语言代码
2. **存储层**：
   - Neo4j图数据库：存储函数、文件和调用关系
   - Chroma向量数据库：存储代码嵌入向量
3. **LLM集成**：
   - 嵌入引擎：生成代码的向量表示
   - 聊天机器人：处理用户问题并生成回答
4. **服务层**：
   - 代码问答服务：整合各组件，提供问答功能
   - 依赖分析服务：分析代码依赖关系
   - 调用图服务：生成函数调用图
5. **分块器**：
   - Tree-sitter分块器：基于语法树的语义分块
   - 固定大小分块器：基于字符数的简单分块

## 贡献指南

欢迎贡献代码或提出建议！请遵循以下步骤：

1. Fork本仓库
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

## 许可证

本项目采用MIT许可证。 