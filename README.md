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
- **CLI框架**：Click

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

# 其他依赖
pip install click pytest flake8 mypy pyyaml requests neo4j>=5.25.0
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
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:5.26-community

# 验证安装
docker ps | grep neo4j
curl http://localhost:7474  # 访问Web界面
```

#### 4. 配置环境变量
```bash
# 创建.env文件
cat > .env << EOF
NEO4J_PASSWORD=your_password
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
VERBOSE=true
EOF
```

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
# 分析OpenSBI项目 (计划中)
code-learner analyze reference_code_repo/opensbi/

# 基本问答 (计划中)
code-learner ask "OpenSBI项目的主要模块有哪些？"
code-learner ask "sbi_init函数在哪里定义？"

# 初始化环境 (计划中)
code-learner setup
```

#### 开发者测试
```bash
# 测试C语言解析器
python -m pytest tests/unit/test_c_parser.py -v

# 测试Neo4j存储
python -m pytest tests/integration/test_story_1_3_acceptance.py -v

# 详细日志模式
VERBOSE=true python -m pytest tests/integration/test_story_1_3_acceptance.py -v -s
```

### 主要命令

#### 📊 分析命令
```bash
# 完整分析
code-learner analyze /path/to/repo

# 增量分析
code-learner analyze /path/to/repo --incremental

# 分析特定文件
code-learner analyze /path/to/repo --files "src/*.c"
```

#### 🔍 查询命令
```bash
# 自然语言查询
code-learner query "find buffer overflow vulnerabilities"

# 函数调用关系查询
code-learner query --type calls --function malloc

# 相似代码搜索
code-learner query --type similar --code "for(int i=0; i<n; i++)"
```

#### 🐛 调试命令
```bash
# 调试助手模式
code-learner debug --error "segmentation fault" --context "main.c:42"

# 交互式调试
code-learner debug --interactive

# 日志分析
code-learner debug --log error.log
```

## 项目结构

```
code-repo-learner/
├── dev-docs/                  # 项目文档
│   ├── 00_prd.md              # 产品需求文档
│   ├── 01_architecture.md     # 技术架构文档
│   └── checklists/            # 质量检查清单
├── src/                       # 源代码
│   └── code_learner/          # 主要包
│       ├── cli/               # 命令行接口
│       ├── parser/            # 代码解析引擎
│       ├── graph/             # 图数据库操作
│       ├── embeddings/        # 向量嵌入
│       └── query/             # 查询分析引擎
├── tests/                     # 测试文件
└── config/                    # 配置文件
```

## Neo4j使用指南

### 🔍 Neo4j Web界面

**访问地址:** http://localhost:7474  
**登录信息:** neo4j / your_password

**常用Cypher查询:**
```cypher
// 查看所有节点和关系
MATCH (n) RETURN n LIMIT 25

// 查看文件包含的函数
MATCH (f:File)-[:CONTAINS]->(fn:Function) 
RETURN f.name, fn.name, fn.start_line, fn.end_line

// 统计节点数量
MATCH (n) RETURN labels(n) as type, count(n) as count

// 查找特定函数
MATCH (fn:Function {name: "main"}) 
RETURN fn.name, fn.code, fn.start_line, fn.file_path

// 清空所有数据
MATCH (n) DETACH DELETE n
```

### ⚠️ 故障排除

**1. Neo4j连接失败**
```bash
# 检查容器状态
docker ps | grep neo4j
docker logs neo4j-community

# 重启容器
docker restart neo4j-community

# 重新创建容器
docker rm -f neo4j-community
docker run -d --name neo4j-community \
  --restart always \
  -p 7474:7474 -p 7687:7687 \
  -v neo4j_data:/data \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:5.26-community
```

**2. 认证错误**
```bash
# 检查环境变量
echo $NEO4J_PASSWORD

# 重置密码
docker exec neo4j-community neo4j-admin dbms set-initial-password new_password
```

**3. 测试失败调试**
```bash
# 开启详细日志
VERBOSE=true python -m pytest tests/integration/test_story_1_3_acceptance.py -v -s

# 单独测试连接
python -c "
from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.config.config_manager import ConfigManager
store = Neo4jGraphStore()
config = ConfigManager().get_config()
result = store.connect(config.database.neo4j_uri, config.database.neo4j_user, config.database.neo4j_password)
print(f'Connection result: {result}')
store.close()
"
```

### 📊 性能监控

**连接池状态:**
- 最大连接数: 50
- 连接超时: 60秒
- 自动重连: 支持

**批量操作优化:**
- 使用UNWIND批量创建节点
- 事务安全保证数据一致性
- 支持大文件和多函数处理

## 开发计划

### 📋 开发阶段 (Epics)

1. **Epic 1: 代码解析与结构分析引擎**
   - Tree-sitter集成和C语言语法解析
   - 代码结构提取和关系建模

2. **Epic 2: 知识图谱构建与存储系统**
   - Neo4j集成和数据建模
   - 图查询和关系分析

3. **Epic 3: 智能嵌入与向量搜索系统**
   - LLM集成和向量生成
   - 语义搜索和相似性分析

4. **Epic 4: AI调试助手与问答系统**
   - 智能问答和调试建议
   - 自然语言查询支持

5. **Epic 5: 性能优化与增量处理**
   - 缓存机制和增量分析
   - 大规模项目支持

### 🎯 开发原则
- **TDD驱动**：测试优先的开发方法
- **KISS原则**：保持简单，避免过度设计
- **SOLID原则**：代码结构清晰，易于维护
- **增量开发**：逐步迭代，持续集成

## 性能指标

### 📊 目标性能
- 单文件解析时间：< 1秒
- 大型项目处理：< 30分钟 (10万行代码)
- 查询响应时间：< 3秒
- 代码解析准确率：> 95%

### 🚀 优化特性
- 并行处理多个文件
- 智能缓存减少重复计算
- 流式处理控制内存使用
- 增量分析只处理变更

## 贡献指南

### 🔧 开发环境设置
```bash
# 克隆仓库
git clone https://github.com/your-org/code-repo-learner.git
cd code-repo-learner

# 安装开发依赖
pip install -e .[dev]

# 运行测试
pytest

# 代码质量检查
flake8 src/
mypy src/
```

### 📝 代码规范
- 遵循PEP 8代码风格
- 使用类型提示
- 编写详细的文档字符串
- 保持单元测试覆盖率 > 90%

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- 项目文档：[dev-docs/](dev-docs/)
- 问题反馈：[GitHub Issues](https://github.com/your-org/code-repo-learner/issues)

---

*这个工具旨在提升C语言开发者的代码理解和调试效率，通过AI技术降低代码维护的复杂度。* 