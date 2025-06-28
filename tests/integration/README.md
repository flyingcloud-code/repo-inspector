# 集成测试

本目录包含代码库学习工具的集成测试，特别是针对项目隔离功能的测试。

## 测试内容

集成测试主要测试以下功能：

1. **项目隔离基本功能**：验证不同项目的数据在Neo4j和Chroma中彼此隔离
2. **C代码解析和存储隔离**：使用真实的OpenSBI代码库测试C代码解析和存储在不同项目中的隔离效果
3. **端到端测试**：验证从代码解析、存储到嵌入、查询的完整流程中的项目隔离

## 环境要求

运行这些测试需要以下环境：

1. 运行中的Neo4j数据库实例
2. 环境变量设置：
   - `NEO4J_URI`：Neo4j数据库URI（默认：`bolt://localhost:7687`）
   - `NEO4J_USER`：Neo4j用户名（默认：`neo4j`）
   - `NEO4J_PASSWORD`：Neo4j密码（默认：`password`）
3. OpenSBI代码库：位于`/home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi`

## 运行测试

### 运行所有集成测试

```bash
python tests/run_integration_tests.py
```

### 运行特定测试

```bash
python tests/run_integration_tests.py -p project_isolation
```

### 运行测试并显示详细输出

```bash
python tests/run_integration_tests.py -v
```

## 注意事项

1. 这些测试使用真实的数据库和代码库，不使用mock或fallback
2. 测试会创建临时目录和数据，测试完成后会自动清理
3. 测试会清空Neo4j数据库中的相关数据，请确保不要在生产环境中运行这些测试
4. 测试会创建多个项目并在Chroma中存储嵌入向量，需要足够的磁盘空间