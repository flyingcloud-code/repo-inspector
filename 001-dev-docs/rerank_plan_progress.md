# 多源检索 + Rerank系统实施计划

## 📋 项目概述

**目标**: 实现基于KISS和SOLID原则的多源检索+统一Rerank架构，充分利用Neo4j图数据库的27M+关系数据

**架构**: 并行检索 + 统一Rerank
- Vector检索器 (语义相似度)
- CallGraph检索器 (函数调用关系) 
- Dependency检索器 (依赖关系)
- LLM Reranker (智能重排序)

## 🎯 实施阶段

### 阶段1：核心接口和数据模型 (Day 1)

#### 任务1.1：创建统一上下文项接口
- [ ] 创建 `ContextItem` 数据类
- [ ] 实现 `to_rerank_format()` 方法
- [ ] 添加类型注解和文档

#### 任务1.2：定义检索器接口
- [ ] 创建 `IContextRetriever` 抽象基类
- [ ] 定义 `retrieve()` 方法签名
- [ ] 添加配置参数支持

#### 任务1.3：创建Reranker接口
- [ ] 创建 `IReranker` 抽象基类
- [ ] 定义 `rerank()` 方法签名
- [ ] 设计prompt模板系统

**预期产出**:
- `src/code_learner/core/context_models.py`
- `src/code_learner/core/retriever_interfaces.py`
- 单元测试

### 阶段2：Vector检索器实现 (Day 1-2)

#### 任务2.1：重构现有向量检索
- [ ] 适配 `VectorContextRetriever` 类
- [ ] 实现 `IContextRetriever` 接口
- [ ] 返回 `ContextItem` 格式

#### 任务2.2：增强多查询策略
- [ ] 基于意图分析构建多个查询
- [ ] 实现查询去重和合并
- [ ] 添加相似度阈值过滤

#### 任务2.3：性能优化
- [ ] 批量查询优化
- [ ] 结果缓存机制
- [ ] 并发查询支持

**预期产出**:
- `src/code_learner/retrieval/vector_retriever.py`
- 集成测试

### 阶段3：CallGraph检索器实现 (Day 2-3)

#### 任务3.1：调用关系检索
- [ ] 实现 `CallGraphContextRetriever` 类
- [ ] 集成现有Neo4j调用关系查询
- [ ] 支持调用深度配置

#### 任务3.2：调用上下文构建
- [ ] 获取函数调用者列表
- [ ] 获取函数被调用者列表
- [ ] 构建调用链路径信息

#### 任务3.3：调用图分析
- [ ] 递归调用检测
- [ ] 调用频率统计
- [ ] 热点函数识别

**预期产出**:
- `src/code_learner/retrieval/call_graph_retriever.py`
- Neo4j查询优化

### 阶段4：Dependency检索器实现 (Day 3-4)

#### 任务4.1：依赖关系检索
- [ ] 实现 `DependencyContextRetriever` 类
- [ ] 集成文件依赖查询
- [ ] 支持模块依赖分析

#### 任务4.2：依赖上下文构建
- [ ] 获取文件依赖关系
- [ ] 获取头文件包含关系
- [ ] 构建依赖层次信息

#### 任务4.3：循环依赖检测
- [ ] 集成现有循环依赖检测
- [ ] 依赖路径分析
- [ ] 依赖影响评估

**预期产出**:
- `src/code_learner/retrieval/dependency_retriever.py`
- 依赖分析报告

### 阶段5：LLM Reranker实现 (Day 4-5)

#### 任务5.1：Reranker核心实现
- [ ] 实现 `LLMReranker` 类
- [ ] 集成现有ChatBot服务
- [ ] 支持批量重排序

#### 任务5.2：Prompt工程
- [ ] 设计rerank prompt模板
- [ ] 支持不同问题类型的prompt
- [ ] 实现prompt参数化

#### 任务5.3：结果解析
- [ ] 解析LLM返回的排序结果
- [ ] 错误处理和fallback机制
- [ ] 结果验证和修正

**预期产出**:
- `src/code_learner/rerank/llm_reranker.py`
- Prompt模板库

### 阶段6：多源上下文构建器 (Day 5-6)

#### 任务6.1：协调器实现
- [ ] 实现 `MultiSourceContextBuilder` 类
- [ ] 并行检索逻辑
- [ ] 结果聚合和去重

#### 任务6.2：配置系统集成
- [ ] 支持检索源开关配置
- [ ] 支持top-k参数配置
- [ ] 支持性能参数调优

#### 任务6.3：错误处理和监控
- [ ] 检索失败的fallback机制
- [ ] 性能监控和日志
- [ ] 健康检查接口

**预期产出**:
- `src/code_learner/retrieval/multi_source_builder.py`
- 配置文档

### 阶段7：集成和测试 (Day 6-7)

#### 任务7.1：CodeQAService集成
- [ ] 集成新的多源检索系统
- [ ] 替换现有的上下文构建逻辑
- [ ] 保持向后兼容性

#### 任务7.2：端到端测试
- [ ] 创建集成测试用例
- [ ] 测试不同查询类型
- [ ] 性能基准测试

#### 任务7.3：配置调优
- [ ] 调优各检索器的top-k参数
- [ ] 优化rerank prompt
- [ ] 性能瓶颈分析和优化

**预期产出**:
- 完整的集成系统
- 测试报告
- 性能基准

## 📁 文件结构

```
src/code_learner/
├── core/
│   ├── context_models.py          # ContextItem等数据模型
│   └── retriever_interfaces.py    # 检索器接口定义
├── retrieval/
│   ├── __init__.py
│   ├── vector_retriever.py        # 向量检索器
│   ├── call_graph_retriever.py    # 调用图检索器
│   ├── dependency_retriever.py    # 依赖图检索器
│   └── multi_source_builder.py    # 多源协调器
├── rerank/
│   ├── __init__.py
│   ├── llm_reranker.py            # LLM重排序器
│   └── prompt_templates.py        # Prompt模板
└── tests/
    ├── test_retrievers.py         # 检索器测试
    ├── test_reranker.py           # 重排序器测试
    └── test_integration.py        # 集成测试
```

## 🔧 配置更新

需要在 `config/settings.yaml` 中添加：

```yaml
enhanced_query:
  enable: true
  
  sources:
    vector:
      enable: true
      top_k: 5
    call_graph:
      enable: true
      top_k: 5
      max_depth: 3
    dependency:
      enable: true
      top_k: 5
      include_circular: true
  
  rerank:
    enable: true
    final_top_k: 5
    model: "gemini-2.0-flash"
    prompt_template: "default"
  
  performance:
    parallel_retrieval: true
    cache_enabled: true
    timeout_seconds: 30
```

## 📊 进度跟踪

| 阶段 | 任务 | 状态 | 开始时间 | 完成时间 | 备注 |
|------|------|------|----------|----------|------|
| 1 | 核心接口和数据模型 | ✅ 已完成 | 2025-06-29 | 2025-06-29 | 完成所有核心数据结构 |
| 1.1 | 创建ContextItem | ✅ 已完成 | 2025-06-29 | 2025-06-29 | context_models.py |
| 1.2 | 定义检索器接口 | ✅ 已完成 | 2025-06-29 | 2025-06-29 | retriever_interfaces.py |
| 1.3 | 创建Reranker接口 | ✅ 已完成 | 2025-06-29 | 2025-06-29 | 包含在接口文件中 |
| 2 | Vector检索器实现 | ✅ 已完成 | 2025-06-29 | 2025-06-29 | 多查询策略和意图驱动 |
| 3 | CallGraph检索器实现 | ✅ 已完成 | 2025-06-29 | 2025-06-29 | 基于Neo4j调用关系 |
| 4 | Dependency检索器实现 | ✅ 已完成 | 2025-06-29 | 2025-06-29 | 文件依赖和循环依赖检测 |
| 5 | LLM Reranker实现 | ✅ 已完成 | 2025-06-29 | 2025-06-29 | 包含prompt模板库 |
| 6 | 多源上下文构建器 | ✅ 已完成 | 2025-06-29 | 2025-06-29 | 并行检索和统一协调 |
| 7 | 集成和测试 | 🔄 进行中 | 2025-06-29 | | 需要集成到现有系统 |

## 🎯 成功标准

### 功能标准
- [ ] 所有三个检索器正常工作
- [ ] LLM Reranker能够智能重排序
- [ ] 多源协调器能并行处理
- [ ] 配置系统支持灵活调整

### 性能标准
- [ ] 检索响应时间 < 3秒
- [ ] Rerank时间 < 2秒
- [ ] 总响应时间 < 8秒
- [ ] 内存使用 < 3GB

### 质量标准
- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试通过
- [ ] 代码质量检查通过
- [ ] 文档完整

## 🚨 风险和缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| LLM API限制 | 中 | 高 | 实现fallback机制，支持多个API |
| Neo4j查询性能 | 中 | 中 | 查询优化，添加索引 |
| 内存使用过高 | 低 | 中 | 分批处理，结果缓存 |
| 集成复杂度 | 中 | 中 | 渐进式集成，保持向后兼容 |

---

**创建时间**: 2025-06-29  
**预计完成**: 2025-07-06  
**负责人**: AI Assistant  
**状态**: 🔄 进行中 