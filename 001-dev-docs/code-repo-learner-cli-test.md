[MODE: PLAN]

# 代码分析工具功能测试设计文档

## 1. 测试目标

本测试设计旨在系统性验证"Code Repo Learner"工具的所有核心功能，确保各组件能够正常工作并协同完成预期任务。测试将覆盖基础系统功能、代码分析、问答系统、导出功能、函数调用图和依赖关系分析等方面。

## 2. 测试环境准备

### 2.1 环境要求
- Ubuntu 24.04 LTS (WSL2)
- Python 3.11+
- Neo4j 5.26+ (Docker容器)
- 配置好的.env文件，包含必要的API密钥

### 2.2 环境准备步骤
1. 确认Neo4j容器运行状态：`docker ps | grep neo4j`
2. 确认环境变量设置：`echo $OPENROUTER_API_KEY`
3. 确认项目安装：`pip list | grep code-repo-learner`
4. 准备测试数据：确认reference_code_repo/opensbi/目录存在

### 2.3 测试前检查清单
- [ ] Neo4j数据库已启动并可访问
- [ ] OpenRouter API密钥已设置
- [ ] 项目已安装到当前Python环境
- [ ] 测试数据已准备就绪

## 3. 测试矩阵

### 3.1 基础系统功能测试

| 测试ID | 测试项 | 测试命令 | 预期结果 |
|-------|------|---------|--------|
| BAS-01 | 系统状态检查 | `code-learner status` | 显示系统状态概览 |
| BAS-02 | 详细状态检查 | `code-learner status --verbose` | 显示详细状态，包括Neo4j连接信息 |

### 3.2 代码分析功能测试

| 测试ID | 测试项 | 测试命令 | 预期结果 |
|-------|------|---------|--------|
| ANA-01 | 基本代码分析 | `code-learner analyze reference_code_repo/opensbi/ --threads 4` | 成功分析项目代码并存储到Neo4j |
| ANA-02 | 小型项目分析 | `code-learner analyze tests/fixtures/` | 成功分析小型测试项目 |

### 3.3 问答功能测试

| 测试ID | 测试项 | 测试命令与操作 | 预期结果 |
|-------|------|------------|--------|
| QA-01 | 基本问答功能 | 1. `code-learner query --project reference_code_repo/opensbi/`<br>2. 输入: `what does function sbi_init do?` | 启动问答会话并返回关于sbi_init函数的描述 |
| QA-02 | 函数聚焦问答 | `code-learner query --project reference_code_repo/opensbi/ --function sbi_init` | 启动聚焦于sbi_init函数的问答会话 |

### 3.4 函数调用图功能测试

| 测试ID | 测试项 | 测试命令 | 预期结果 |
|-------|------|---------|--------|
| CALL-01 | ASCII调用图 | `call-graph sbi_init --format ascii` | 生成ASCII格式的函数调用树 |
| CALL-02 | Mermaid调用图 | `call-graph sbi_init --format mermaid --output call_graph.md` | 生成Mermaid格式的函数调用图 |

### 3.5 依赖关系分析功能测试

| 测试ID | 测试项 | 测试命令 | 预期结果 |
|-------|------|---------|--------|
| DEP-01 | 项目依赖分析 | `dependency-graph analyze reference_code_repo/opensbi/` | 分析项目依赖关系 |
| DEP-02 | 循环依赖检测 | `dependency-graph cycle` | 检测并报告循环依赖 |

### 3.6 导出功能测试

| 测试ID | 测试项 | 测试命令 | 预期结果 |
|-------|------|---------|--------|
| EXP-01 | JSON导出 | `code-learner export --project reference_code_repo/opensbi/ --format json --output opensbi.json` | 生成JSON格式的分析数据 |

## 4. 测试执行计划

### 4.1 测试流程
1. 按照测试矩阵中的顺序执行测试
2. 每个测试完成后记录结果
3. 对于失败的测试，记录错误信息和复现步骤
4. 完成所有测试后，生成测试报告

### 4.2 测试优先级
1. 基础系统功能 (BAS-01, BAS-02)
2. 代码分析功能 (ANA-01, ANA-02)
3. 函数调用图功能 (CALL-01, CALL-02)
4. 依赖关系分析功能 (DEP-01, DEP-02)
5. 问答功能 (QA-01, QA-02)
6. 导出功能 (EXP-01)

## 5. 测试结果记录表

| 测试ID | 测试状态 | 结果描述 | 错误信息 | 测试日期 |
|-------|---------|---------|---------|---------|
| BAS-01 | | | | |
| BAS-02 | | | | |
| ANA-01 | | | | |
| ANA-02 | | | | |
| QA-01 | | | | |
| QA-02 | | | | |
| CALL-01 | | | | |
| CALL-02 | | | | |
| DEP-01 | | | | |
| DEP-02 | | | | |
| EXP-01 | | | | |

## 6. 测试结果分析指南

### 6.1 成功标准
- 所有测试通过
- 无严重错误
- 功能按预期工作

### 6.2 问题分类
- 严重问题：阻止核心功能使用
- 中等问题：影响部分功能但不阻止使用
- 轻微问题：UI/UX问题，不影响功能

### 6.3 问题报告格式
```
问题ID: XXX-YY
测试ID: XXX-YY
严重程度: [严重/中等/轻微]
描述: [问题描述]
复现步骤: [详细步骤]
期望结果: [期望的正确行为]
实际结果: [实际观察到的行为]
可能原因: [初步分析]
```

## 7. 测试后续行动

### 7.1 问题修复优先级
1. 严重问题：立即修复
2. 中等问题：计划修复
3. 轻微问题：后续版本考虑

### 7.2 测试报告提交
- 完成所有测试后生成测试报告
- 报告包含测试结果摘要、发现的问题和建议

---

此测试设计文档提供了系统性测试"Code Repo Learner"工具所有功能的框架。执行测试时，请按照测试矩阵中的顺序进行，并详细记录每个测试的结果，以便后续分析和改进。