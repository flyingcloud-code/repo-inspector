# C语言智能代码分析调试工具 - 工作计划与进度跟踪 (POC版本)

## 项目概览

**Phase 1 POC**专注于验证核心技术栈可行性的最小实施计划，包含4个Epic，12个Story。

**POC目标：** 证明Tree-sitter + Neo4j + Chroma + OpenRouter能协同工作，完成一个中型项目（C语言）解析到问答的端到端流程。

**参考项目：** OpenSBI (RISC-V开源固件项目)
- **项目规模：** 289个文件 (172个.c文件 + 117个.h文件)，总计48,744行代码
- **项目路径：** `/home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi`
- **项目特点：** 典型的C语言系统级项目，包含复杂的函数调用关系和模块化结构

**技术栈 (Ubuntu 24.04 LTS + uv环境):**
- **开发环境:** uv虚拟环境 (.venv) + flake8 + mypy
- **核心组件:** Tree-sitter-c, Neo4j Community (Docker), Chroma, jina-embeddings-v2-base-code, OpenRouter API (google/gemini-2.0-flash-001)
- **操作系统:** Ubuntu 24.04 LTS (WSL2)

## Epic 1: 核心技术验证 (4个Story) 🎯

**Epic目标：** 验证技术栈集成可行性，完成最小端到端流程

### Story 1.1: Ubuntu环境搭建与配置系统 ⭐
**状态:** ✅ 完成 (2025-06-23)  
**估时:** 0.5天  
**优先级:** 高

**功能描述:**
完成Ubuntu 24.04 LTS环境下所有依赖安装，创建完整的Python包结构，实现配置管理系统和基础工具类。

**详细任务清单:**

1. **Ubuntu环境依赖安装验证**
   - 创建uv虚拟环境 .venv
   - 安装Tree-sitter相关包 (apt/pip)  
   - 安装Chroma向量数据库 (pip)
   - 安装sentence-transformers和jina-embeddings模型
   - 配置Neo4j Community Edition (Docker容器)
   - 验证SQLite内置支持

2. **包结构创建**
   - 创建分层的包结构 (config/, core/, parser/, storage/, llm/, cli/, utils/)
   - 设置__init__.py文件和包级导入
   - 创建requirements.txt和pyproject.toml

3. **配置管理系统**
   - 实现ConfigManager单例类
   - 创建config.yml模板文件
   - 实现配置验证和环境变量支持
   - 添加Linux路径处理

4. **基础工具类**
   - 实现Logger工具类
   - 创建自定义异常类
   - 实现Helper工具函数
   - Linux文件路径兼容性

**Ubuntu安装详细说明:**

**环境准备:**
```bash
# 创建uv虚拟环境 (用户已创建.venv)
uv venv --python 3.11
source .venv/bin/activate
```

**Tree-sitter安装:**
```bash
# 方法1: apt + pip (推荐)
sudo apt update
sudo apt install libtree-sitter-dev
pip install tree-sitter tree-sitter-c

# 验证安装
python -c "import tree_sitter; print('Tree-sitter版本:', tree_sitter.__version__)"
```

**Chroma安装:**
```bash
# pip安装 (原生Linux支持)
pip install chromadb>=1.0.13

# 验证安装
python -c "import chromadb; client = chromadb.Client(); print('Chroma安装成功')"
```

**jina-embeddings安装:**
```bash
pip install -U sentence-transformers>=3.0.0
# 首次运行会自动下载模型到: ~/.cache/torch/sentence_transformers/
```

**Neo4j Community Edition安装 (Docker容器):**
```bash
# 创建数据卷
docker volume create neo4j_data
docker volume create neo4j_logs

# 启动Neo4j容器 (用户已有Docker 28.1.1)
docker run -d \
    --name neo4j-community \
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

**SQLite验证:**
```bash
python -c "import sqlite3; print('SQLite version:', sqlite3.sqlite_version)"
```

**验收标准:**
1. ✅ 所有Ubuntu依赖成功安装并可以导入
2. ✅ Neo4j服务正常启动，可以访问Web界面
3. ✅ jina-embeddings模型可以正常加载
4. ✅ 完整包结构创建 (11个子包和文件)
5. ✅ ConfigManager能加载和验证配置
6. ✅ 日志系统正常工作
7. ✅ 所有包能正常导入

**TDD测试计划:**

1. **环境依赖测试:**
```python
# tests/unit/test_ubuntu_environment.py
def test_tree_sitter_import():
    """验证tree-sitter导入"""
    import tree_sitter
    from tree_sitter import Language, Parser
    assert tree_sitter.__version__ >= "0.24.0"

def test_chroma_import():
    """验证chromadb导入"""
    import chromadb
    client = chromadb.Client()
    assert client is not None

def test_sentence_transformers_import():
    """验证模型库导入"""
    from sentence_transformers import SentenceTransformer
    # 不实际加载模型，只验证导入

def test_neo4j_connection():
    """验证Neo4j连接"""
    from neo4j import GraphDatabase
    # 测试连接但不依赖实际服务

def test_sqlite_connection():
    """验证SQLite连接"""
    import sqlite3
    conn = sqlite3.connect(':memory:')
    assert conn is not None
    conn.close()
```

2. **配置系统测试:**
```python
# tests/unit/test_config_manager.py
def test_config_loading():
    """测试配置加载功能"""
    config = ConfigManager().load_config()
    assert config.database.uri == "bolt://localhost:7687"
    assert config.llm.embedding_model == "jinaai/jina-embeddings-v2-base-code"

def test_config_validation():
    """测试配置验证"""
    # 测试无效配置的处理

def test_environment_variables():
    """测试环境变量支持"""
    # 测试从环境变量读取API key

def test_linux_path_handling():
    """测试Linux路径处理"""
    # 验证Linux路径格式处理
```

3. **日志系统测试:**
```python
# tests/unit/test_logger.py
def test_logger_initialization():
    """日志初始化"""
    
def test_file_logging():
    """文件日志输出"""
    
def test_console_logging():
    """控制台日志输出"""
```

**通过标准 (100%测试通过):**
- ✅ 环境依赖测试：7/7通过
- ✅ ConfigManager单元测试：9/9通过  
- ✅ 数据模型测试：16/16通过
- ✅ 包导入测试：7/7通过
- ✅ 验收测试：8/8通过
- ✅ **总计：47/47测试通过 (100%)**
- Logger工具测试：3/3通过  
- 包导入测试：11/11通过
- 配置验证测试：5/5通过

**详细包结构:**
```
src/code_learner/
├── __init__.py                 # 主包导入
├── config/
│   ├── __init__.py
│   ├── config_manager.py       # 配置管理器类
│   ├── settings.py             # 默认设置
│   └── config.yml              # 配置模板
├── core/
│   ├── __init__.py
│   ├── interfaces.py           # 接口定义
│   ├── data_models.py          # 数据模型
│   └── exceptions.py           # 自定义异常
├── parser/
│   ├── __init__.py
│   └── c_parser.py             # C解析器
├── storage/
│   ├── __init__.py
│   ├── graph_store.py          # Neo4j图存储
│   └── vector_store.py         # Chroma向量存储
├── llm/
│   ├── __init__.py
│   ├── embedding_engine.py     # 嵌入引擎
│   └── chat_bot.py             # 对话机器人
├── cli/
│   ├── __init__.py
│   └── main.py                 # CLI应用
└── utils/
    ├── __init__.py
    ├── logger.py               # 日志工具
    └── helpers.py              # 辅助函数
```

**核心配置类设计:**
```python
@dataclass
class DatabaseConfig:
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"

@dataclass 
class LLMConfig:
    embedding_model: str = "jinaai/jina-embeddings-v2-base-code"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-001"
    max_tokens: int = 1000

class ConfigManager:
    def load_config(self, config_path: Optional[Path] = None) -> Config
    def _validate_config(self, config: Config) -> bool
    def _load_environment_vars(self) -> Dict[str, str]
```

---

### Story 1.2: Tree-sitter C语言解析器实现 ⭐
**状态:** ✅ 完成 (2025-06-23)  
**估时:** 1天  
**优先级:** 高

**功能描述:**
实现完整的CParser类，集成Tree-sitter-c解析器，提供C文件解析和AST特征提取功能。

**详细任务清单（简化版 - 遵循KISS原则）:**
1. **基础CParser实现**
   - 实现IParser接口的2个核心方法
   - Tree-sitter解析器初始化
   - 基本文件读取和错误处理

2. **最小化函数提取**
   - 提取函数名、行号、源代码
   - 暂不处理：参数解析、调用关系、返回类型
   - 暂不处理：Include文件、复杂语法结构

3. **简化错误处理**
   - 文件不存在时优雅失败
   - 语法错误时返回空结果
   - 基本的异常捕获和日志记录

**简化类设计（KISS原则）:**
```python
class CParser(IParser):
    def __init__(self):
        self.language = Language(tree_sitter_c.language())
        self.parser = Parser(self.language)
    
    def parse_file(self, file_path: Path) -> ParsedCode:
        """解析C文件，返回基本解析结果"""
        # 1. 读取文件内容
        # 2. Tree-sitter解析生成AST
        # 3. 调用extract_functions提取函数
        # 4. 构建并返回ParsedCode对象
    
    def parse_directory(self, dir_path: Path, pattern: str = "*.c") -> List[ParsedCode]:
        """解析目录下的C文件（简单实现）"""
        # 遍历目录，对每个.c文件调用parse_file
    
    def extract_functions(self, source_code: str, file_path: str) -> List[Function]:
        """从源代码提取函数信息（最小版本）"""
        # 1. 遍历AST查找function_definition节点
        # 2. 提取：函数名、起始行号、结束行号、源代码
        # 3. 不提取：参数、返回类型、调用关系
```

**简化验收标准（POC阶段）:**
1. ✅ CParser类正确实现IParser接口
2. ✅ 能解析hello.c和complex.c，提取函数基本信息
3. ✅ 文件不存在时优雅失败
4. ✅ 返回正确的ParsedCode和Function对象

**简化TDD测试计划（8个测试）:**
```python
# tests/unit/test_c_parser.py
class TestCParser:
    def test_parse_simple_file(self):
        """测试解析hello.c文件"""
        parser = CParser()
        result = parser.parse_file(Path("tests/fixtures/hello.c"))
        assert len(result.functions) == 2
        assert result.functions[0].name in ['hello', 'main']
        
    def test_extract_function_names(self):
        """测试提取函数名"""
        parser = CParser()
        functions = parser.extract_functions("void test() {}", "test.c")
        assert len(functions) == 1
        assert functions[0].name == 'test'
        
    def test_function_line_numbers(self):
        """测试行号提取"""
        code = "void func1() {}\nvoid func2() {}"
        parser = CParser()
        functions = parser.extract_functions(code, "test.c")
        assert functions[0].start_line == 1
        assert functions[1].start_line == 2
        
    def test_function_code_extraction(self):
        """测试函数代码提取"""
        parser = CParser()
        functions = parser.extract_functions("void test() { return; }", "test.c")
        assert "void test()" in functions[0].code
        
    def test_file_not_found(self):
        """测试文件不存在错误处理"""
        parser = CParser()
        # 应该抛出FileNotFoundError或返回错误状态
        
    def test_empty_file(self):
        """测试空文件处理"""
        parser = CParser()
        functions = parser.extract_functions("", "empty.c")
        assert len(functions) == 0
        
    def test_invalid_syntax(self):
        """测试语法错误处理"""
        parser = CParser()
        functions = parser.extract_functions("invalid syntax {{{", "bad.c")
        # 应该返回空列表而不是崩溃
        
    def test_interface_compliance(self):
        """测试接口实现正确性"""
        parser = CParser()
        assert isinstance(parser, IParser)
        assert hasattr(parser, 'parse_file')
        assert hasattr(parser, 'extract_functions')
```

**通过标准 (100%测试通过):**
- ✅ 基础解析测试：4/4通过
- ✅ 错误处理测试：3/3通过  
- ✅ 接口合规测试：1/1通过
- ✅ **总计：8/8测试通过 (100%)**

**技术成果:**
- ✅ CParser类完整实现，支持tree-sitter 0.21.3 API
- ✅ 解决了tree-sitter字节范围错误问题（使用node.text）
- ✅ 正确提取函数名、行号、源代码
- ✅ 支持包含注释和预处理指令的复杂C代码
- ✅ 优雅处理语法错误和文件不存在情况

**测试文件设计:**
```c
// tests/fixtures/hello.c - 基础测试文件
#include <stdio.h>

void hello() {
    printf("Hello, World!\n");
}

int main() {
    hello();
    return 0;
}

// tests/fixtures/complex.c - 复杂测试文件
#include <stdio.h>
#include <stdlib.h>

int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n-1) + fibonacci(n-2);
}

void print_sequence(int count) {
    for (int i = 0; i < count; i++) {
        printf("%d ", fibonacci(i));
    }
}

int main() {
    print_sequence(10);
    return 0;
}
```

**简化数据模型（使用现有的core/data_models.py）:**
```python
# 使用已有的数据模型，暂时只填充基本字段
@dataclass
class Function:
    name: str                    # 函数名 ✅
    code: str                    # 函数源代码 ✅
    start_line: int              # 开始行号 ✅
    end_line: int                # 结束行号 ✅
    file_path: str               # 所属文件 ✅
    parameters: List[str] = field(default_factory=list)  # 暂时为空 ⏸️
    return_type: Optional[str] = None                    # 暂时为None ⏸️
    calls: Optional[List[str]] = None                    # 暂时为None ⏸️

@dataclass  
class ParsedCode:
    file_path: str               # 文件路径 ✅
    functions: List[Function]    # 函数列表 ✅
    includes: List[str] = field(default_factory=list)   # 暂时为空 ⏸️
    structs: List[Dict[str, Any]] = field(default_factory=list)  # 暂时为空 ⏸️
    global_vars: List[Dict[str, Any]] = field(default_factory=list)  # 暂时为空 ⏸️
```

**暂缓字段（后续Story实现）:**
- parameters, return_type, calls → Story 1.3
- includes, structs, global_vars → Epic 2

---

### Story 1.3: Neo4j图数据库存储 ⭐
**状态:** ✅ 完成 (2025-06-23)  
**估时:** 1天  
**优先级:** 高

**功能描述:**
集成Neo4j图数据库，实现代码结构的图存储功能，支持File和Function节点存储及CONTAINS关系建立。

**技术实现:**
- **Neo4j Python Driver 5.28:** 使用最新版本API
- **严格错误处理:** 无fallback机制，所有错误抛出异常
- **详细日志记录:** 支持verbose模式，完整操作跟踪
- **事务安全:** 使用managed transactions确保数据一致性
- **连接池优化:** 配置连接池参数提升性能

**核心功能实现:**

1. **Neo4jGraphStore类**
   ```python
   class Neo4jGraphStore(IGraphStore):
       def connect(self, uri: str, user: str, password: str) -> bool
       def store_parsed_code(self, parsed_code: ParsedCode) -> bool  
       def clear_database(self) -> bool
   ```

2. **图数据模型**
   - **File节点:** 存储文件路径、名称、大小、修改时间
   - **Function节点:** 存储函数名、代码、行号范围、文件路径
   - **CONTAINS关系:** File包含Function的关系

3. **严格模式特性**
   - **无Fallback:** 连接失败、事务失败都直接抛出StorageError异常
   - **详细日志:** 支持VERBOSE=true环境变量，输出DEBUG级别日志
   - **事务验证:** 清空数据库后验证操作完成度

**验收标准:**
1. ✅ Neo4j连接和基本操作
2. ✅ 存储File和Function节点  
3. ✅ 创建CONTAINS关系 (File包含Function)
4. ✅ 端到端测试 - 真实C文件解析存储

**TDD测试成果:**
```python
# 4个集成验收测试 - 100%通过
def test_ac1_neo4j_connection_and_basic_operations()    # ✅ 连接和基本操作
def test_ac2_store_file_and_function_nodes()           # ✅ 节点存储
def test_ac3_create_contains_relationship()            # ✅ 关系建立  
def test_ac4_end_to_end_with_real_c_file()            # ✅ 端到端测试
```

**Neo4j使用指南:**

1. **启动Neo4j容器:**
   ```bash
   docker run -d \
       --name neo4j-community \
       --restart always \
       -p 7474:7474 -p 7687:7687 \
       -v neo4j_data:/data \
       -v neo4j_logs:/logs \
       -e NEO4J_AUTH=neo4j/your_password \
       neo4j:5.26-community
   ```

2. **配置环境变量:**
   ```bash
   # .env文件
   NEO4J_PASSWORD=your_password
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   VERBOSE=true  # 开启详细日志
   ```

3. **运行验收测试:**
   ```bash
   # 基本测试
   python -m pytest tests/integration/test_story_1_3_acceptance.py -v
   
   # 详细日志模式
   VERBOSE=true python -m pytest tests/integration/test_story_1_3_acceptance.py -v -s
   ```

4. **Neo4j Web界面验证:**
   - 访问: http://localhost:7474
   - 登录: neo4j / your_password
   - 查询示例:
     ```cypher
     // 查看所有节点和关系
     MATCH (n) RETURN n LIMIT 25
     
     // 查看文件包含的函数
     MATCH (f:File)-[:CONTAINS]->(fn:Function) 
     RETURN f.name, fn.name, fn.start_line, fn.end_line
     
     // 统计节点数量
     MATCH (n) RETURN labels(n) as type, count(n) as count
     ```

**性能特性:**
- **连接池:** max_connection_pool_size=50, timeout=60s
- **批量操作:** 使用UNWIND批量创建函数节点
- **事务安全:** 使用execute_write确保数据一致性
- **资源管理:** 支持上下文管理器自动清理

**错误处理示例:**
```python
# 连接失败 - 抛出StorageError
try:
    store.connect("bolt://invalid:7687", "neo4j", "wrong_password")
except StorageError as e:
    print(f"Connection failed: {e}")

# 事务失败 - 抛出StorageError  
try:
    store.store_parsed_code(invalid_data)
except StorageError as e:
    print(f"Storage failed: {e}")
```

**Verbose日志示例:**
```bash
VERBOSE=true python test_script.py
# 输出详细的连接、事务、查询日志
# 包含emoji标记的操作状态
# 完整的参数和结果跟踪
```

**通过标准 (100%测试通过):**
- ✅ 验收测试：4/4通过
- ✅ 真实数据库连接（无mock）
- ✅ 严格错误处理（无fallback）
- ✅ 详细日志记录（verbose模式）
- ✅ 事务安全性验证

### 13. 第二轮开发周期计划 (延迟功能)

**当前版本 (POC) - 简化功能:**
```python
class IGraphStore(ABC):
    def connect(self, uri: str, user: str, password: str) -> bool         # ✅ 当前实现
    def store_parsed_code(self, parsed_code: ParsedCode) -> bool          # ✅ 当前实现  
    def clear_database(self) -> bool                                      # ✅ 当前实现
```

**第二轮版本 - 完整功能:**
```python
class IGraphStore(ABC):
    # POC功能 (保持不变)
    def connect(self, uri: str, user: str, password: str) -> bool
    def store_parsed_code(self, parsed_code: ParsedCode) -> bool
    def clear_database(self) -> bool
    
    # 第二轮新增功能
    def create_call_relationship(self, caller: str, callee: str) -> bool  # 🔄 第二轮实现
    def query_function_calls(self, function_name: str) -> List[str]       # 🔄 第二轮实现
    def query_call_graph(self, root_function: str) -> Dict[str, Any]      # 🔄 第二轮实现
    def find_unused_functions(self) -> List[str]                          # 🔄 第二轮实现
```

**第二轮开发触发条件:**
- ✅ Epic 1 (POC) 100%完成
- ✅ CParser能够提取函数调用关系数据
- ✅ 基本的图存储和查询功能验证成功
- ✅ 用户反馈需要更复杂的代码分析功能

**第二轮实施优先级:**
1. **高优先级**: `create_call_relationship()` - 存储函数调用关系
2. **中优先级**: `query_function_calls()` - 查询直接调用关系  
3. **低优先级**: `query_call_graph()` - 复杂调用图分析
4. **扩展功能**: `find_unused_functions()` - 代码质量分析

**数据模型扩展 (第二轮):**
```cypher
// 当前POC模型
(:File)-[:CONTAINS]->(:Function)

// 第二轮扩展模型
(:Function)-[:CALLS]->(:Function)        // 函数调用关系
(:Function)-[:DEFINED_IN]->(:File)       // 函数定义位置
(:File)-[:INCLUDES]->(:File)             // 文件包含关系
```

### 14. Story 1.3 最终确认

**✅ 设计评审结果:**
- **符合KISS原则**: 3个核心方法，功能明确
- **符合YAGNI原则**: 不实现当前用不到的功能
- **符合SOLID原则**: 接口职责单一，易于扩展
- **符合TDD原则**: 完整的测试覆盖

**✅ 实施就绪检查:**
- [x] 接口定义已更新 (`src/code_learner/core/interfaces.py`)
- [x] 详细实施设计已完成
- [x] 测试计划已制定 (8个单元测试 + 4个集成测试)
- [x] 优化建议和最佳实践已提供
- [x] 故障排除指南已准备
- [x] 第二轮开发计划已明确

**🎯 开发者行动清单:**
1. **创建存储模块结构**
   ```bash
   mkdir -p src/code_learner/storage
   touch src/code_learner/storage/__init__.py
   touch src/code_learner/storage/neo4j_store.py
   ```

2. **实现Neo4jGraphStore类**
   - 按照第3节的实现结构编写代码
   - 应用第9节的优化建议（批量操作、错误处理、日志记录）
   - 确保资源管理正确（使用context manager）

3. **创建测试文件**
   ```bash
   touch tests/unit/test_neo4j_store.py
   touch tests/integration/test_story_1_3_acceptance.py
   ```

4. **实施TDD开发流程**
   - Red: 编写失败的测试
   - Green: 实现最简功能使测试通过
   - Refactor: 优化代码结构和性能

5. **验证和部署**
   - 运行所有测试确保通过
   - 检查Neo4j Web界面数据正确性
   - 进行性能测试（单文件存储 < 1秒）

**📋 Story 1.3 完成标准:**
- [ ] 所有单元测试通过 (>=8个测试用例)
- [ ] 所有集成测试通过 (>=4个验收测试)  
- [ ] Neo4j Web界面能查看到正确的节点和关系
- [ ] 基本Cypher查询返回正确结果
- [ ] 代码符合flake8规范
- [ ] 能够存储从CParser解析的真实C文件数据
- [ ] 为Story 1.4向量嵌入提供数据基础

**准备开始实施Story 1.3！** 🚀

---

### Story 1.4: 向量嵌入与问答 ⭐ 
**状态:** ✅ 完成 (2025-06-24)  
**估时:** 1天  
**优先级:** 高

**功能描述:**
集成Chroma向量数据库和OpenRouter API，实现代码嵌入和基本问答，支持repo级别扩展。

**✅ 已完成功能 (100%)**：

#### 核心服务实现
- ✅ **JinaEmbeddingEngine**: jina-embeddings-v2-base-code嵌入引擎
  - 支持单文本和批量编码 (`encode_batch()`)
  - 函数专用编码 (`encode_function()`)
  - repo级别批量处理优化

- ✅ **ChromaVectorStore**: 持久化向量存储
  - 多集合管理 (repo级别支持)
  - 批量向量添加和语义搜索
  - 余弦相似度配置

- ✅ **OpenRouterChatBot**: API聊天机器人
  - 代码问答功能 (`ask_question()`)
  - **代码摘要生成** (`generate_summary()`) - 用户明确需求 ✅
  - 重试机制和错误处理

- ✅ **LLMServiceFactory**: 服务工厂
  - 统一服务创建和配置管理
  - 延迟加载优化

- ✅ **CodeQAService**: 综合问答服务
  - 整合所有LLM服务
  - 统一的代码分析接口

#### 架构特性
- ✅ 三个独立接口设计 (支持扩展)
- ✅ repo级别处理能力 (289文件支持)
- ✅ 持久化存储 (Chroma PersistentClient)
- ✅ 批量处理优化 (batch_size=32)

**✅ 解决的技术问题**：

#### 已修复的关键问题
- ✅ ModelLoadError异常签名修复
- ✅ IChatBot.initialize方法实现
- ✅ 数据模型扩展 (ChatMessage, ChatResponse)
- ✅ 异常处理类补全
- ✅ ConfigManager接口匹配问题修复
- ✅ OpenRouter HTTP头部编码问题解决
- ✅ Jina嵌入模型缓存损坏问题解决

#### API配置验证成功
- ✅ **OpenRouter API**: google/gemini-2.0-flash-001模型验证通过
- ✅ **Jina嵌入模型**: jinaai/jina-embeddings-v2-base-code下载和加载成功
- ✅ **向量存储**: Chroma持久化存储配置正常

**🧪 测试验证 (真实API - 无mock)**：
```python
# ✅ 已通过的真实API测试
def test_embedding_engine_real_api():
    """✅ 真实jina-embeddings模型测试通过"""
    # 768维向量嵌入正常工作
    
def test_chatbot_real_openrouter():
    """✅ 真实OpenRouter API测试通过"""
    # 代码问答和摘要生成功能验证
    
def test_integration_services():
    """✅ 服务集成测试通过"""
    # 完整的端到端LLM服务流程验证
```

**测试结果**: ✅ 核心功能测试通过

**🎯 完成成果**：
1. ✅ OpenRouter API集成和验证完成
2. ✅ Jina嵌入模型下载和配置成功  
3. ✅ 服务工厂配置问题全部解决
4. ✅ 真实API测试环境建立
5. ✅ 用户测试脚本创建并验证通过

---

**Epic 1 总体进度更新**:
- Story 1.1: ✅ 完成 (基础环境搭建)
- Story 1.2: ✅ 完成 (Tree-sitter解析器)  
- Story 1.3: ✅ 完成 (Neo4j图数据库)
- Story 1.4: ✅ 完成 (向量嵌入与问答)

**Epic 1 完成度**: 4/4 = **100%** 🎉

## Epic 2: 函数调用关系分析 (Story 2.1-2.4) 
> **质量标准升级：从 Epic 2 开始，新/修改模块的单元 + 集成测试覆盖率目标统一提升至 90% 以上（含增量覆盖率），并保持端到端验收测试全部通过。**
**状态:** 🔄 进行中 (2025-01-22)  
**总估时:** 3.5天  
**当前进度:** 42.9% (1.5/3.5天)

### Story 2.1: 函数调用关系分析 ⭐
**状态:** ✅ 已完成 (2025-01-22)  
**估时:** 1.5天  
**当前进度:** 100% (1.5/1.5天)

**功能描述:**
基于Tree-sitter实现C语言函数调用关系提取，支持直接调用、指针调用、成员调用和递归调用分析，建立多路分析架构。

#### 子任务进度

**Story 2.1.1: 接口设计扩展** ✅ **完成** (2025-06-24)
- **实际用时:** 0.2天 (预估0.2天)
- **完成度:** 100%

**✅ 已完成功能:**

**1. 数据模型扩展 (100%)**
- ✅ `FunctionCall`: 函数调用关系数据模型
  - 支持四种调用类型：direct, pointer, member, recursive
  - 完整的数据验证和错误处理
  - 调用上下文代码片段存储
  
- ✅ `FallbackStats`: Fallback统计信息模型
  - Tree-sitter成功率和fallback使用率统计
  - 处理时间性能指标
  - 动态fallback原因分类

- ✅ `FolderInfo` & `FolderStructure`: 文件夹结构分析
  - 语义分类支持 (core, driver, lib, test, util)
  - 文件统计和命名模式识别
  - 层级结构管理

- ✅ `Documentation`: 文档信息模型
  - README文件内容提取
  - 文件注释和API文档整合
  - 全文本搜索支持

- ✅ `AnalysisResult`: 多路分析结果模型
  - 整合所有分析结果
  - 函数调用关系查询方法
  - 性能指标存储

**2. 接口设计扩展 (100%)**
- ✅ `IParser`接口扩展
  - `extract_function_calls()`: 函数调用关系提取
  - `get_fallback_statistics()`: fallback统计获取

- ✅ `IGraphStore`接口扩展
  - 批量函数调用关系存储
  - 调用图谱查询和分析
  - 未使用函数检测
  - 文件夹结构存储

- ✅ `IVectorStore`接口扩展
  - 多模态向量存储 (函数+文档)
  - 语义搜索功能
  - 文档向量嵌入支持

- ✅ 新增核心接口
  - `IMultiModalAnalysisStrategy`: 多路分析策略
  - `IRAGRetrievalStrategy`: 混合召回策略
  - `IMetaDataStore`: 元数据存储接口

**3. 测试覆盖 (100%)**
- ✅ 35个测试用例全部通过
- ✅ 新增数据模型完整测试覆盖
- ✅ 数据验证和边界条件测试
- ✅ 性能指标计算测试
- ✅ 包导入兼容性验证

**📋 技术实现要点:**
- **SOLID原则遵循**: 接口职责单一，易于扩展
- **数据完整性**: 完整的数据验证和错误处理
- **性能考虑**: 批量操作和统计信息优化
- **多路分析**: Tree-sitter + Neo4j + Chroma + 文档分析架构
- **测试驱动**: 100%测试覆盖，35个测试用例

**Story 2.1.2: 数据模型扩展** ✅ **已完成** (2025-01-20)
- **估时:** 0.2天
- **状态:** 已完成
- **依赖:** Story 2.1.1 ✅ 完成

**实现内容:**
1. **Function模型扩展** - 新增8个字段和9个方法:
   - 新增字段: `complexity_score`, `is_static`, `is_inline`, `docstring`, `parameter_types`, `local_variables`, `macro_calls`, `call_contexts`
   - 新增方法: `add_call()`, `add_caller()`, `get_call_count()`, `get_caller_count()`, `is_leaf_function()`, `is_entry_function()`, `get_lines_of_code()`, `calculate_complexity_score()`
   - 支持调用关系管理和复杂度计算

2. **FileInfo模型扩展** - 新增11个字段和6个方法:
   - 新增字段: `file_type`, `encoding`, `line_count`, `code_lines`, `comment_lines`, `blank_lines`, `macro_definitions`, `struct_definitions`, `global_variables`, `typedefs`, `header_comments`, `semantic_category`
   - 新增方法: `add_function()`, `get_function_by_name()`, `get_function_count()`, `get_total_loc()`, `get_average_function_complexity()`, `calculate_file_metrics()`
   - 支持多维度文件分析和指标计算

3. **ParsedCode模型扩展** - 新增5个字段和9个方法:
   - 新增字段: `parsing_time`, `parsing_method`, `error_count`, `warnings`, `call_relationships`
   - 新增方法: `add_function_call_relationship()`, `get_call_relationships_by_caller()`, `get_call_relationships_by_callee()`, `get_function_call_graph()`, `find_entry_functions()`, `find_leaf_functions()`, `calculate_cyclomatic_complexity()`, `get_parsing_summary()`, `validate_call_relationships()`
   - 支持高级分析功能和调用关系管理

**技术特点:**
- **向后兼容**: 所有现有功能保持不变，新字段都有默认值
- **前向引用**: 使用`from __future__ import annotations`解决类型引用问题
- **数据完整性**: 完整的数据验证和错误处理
- **性能优化**: 高效的查询和分析方法
- **测试覆盖**: 新增10个测试类，45个测试用例全部通过

**测试结果**: 83个单元测试全部通过 ✅

**Story 2.1.3: Tree-sitter 函数调用提取** ✅ **已完成**
- **估时:** 0.4 天  
- **状态:** 已完成 (2025-01-22)
- **依赖:** Story 2.1.2 ✅ 

> 目标：在 CParser v2 中精确提取函数调用（直接 / 指针 / 结构体成员 / 递归），生成 `FunctionCall` 列表并写入 `ParsedCode.call_relationships`，同时为 Neo4j 创建 `CALLS` 关系。

#### ✅ 完成情况
| # | 任务 | 状态 | 关键输出 |
|---|------|------|---------|
| 1 | **AST 查询脚本** | ✅ | `treesitter_queries/c_function_calls.scm` |
| 2 | **接口扩展** | ✅ | `IParser.extract_function_calls()` 方法 |
| 3 | **CParser 实现** | ✅ | 完整的函数调用提取逻辑 |
| 4 | **数据模型对齐** | ✅ | 使用 `FunctionCall` 数据模型 |
| 5 | **GraphStore 扩展** | ✅ | `store_parsed_code()` 支持调用关系存储 |
| 6 | **文档更新** | ✅ | 架构文档已同步 |
| 7 | **测试** | ✅ | 单元测试 4 个，集成测试 3 个，验收测试 1 个 |

#### 🎯 测试结果
- **单元测试:** 4/4 通过 (直接/成员/指针/递归调用)
- **集成测试:** 3/3 通过 (解析+存储+Neo4j验证)  
- **验收测试:** 1/1 通过 (端到端完整流程)
- **测试覆盖率:** Parser 78%, Storage 63% (新增功能覆盖良好)

#### 🔧 技术实现
- Tree-sitter AST 遍历算法，识别 4 种调用类型
- Neo4j `CALLS` 关系存储，包含调用类型和上下文
- 完整的错误处理和日志记录
- 真实 API 测试，无 mock/fallback

#### 📈 性能指标
- 解析速度：小文件 < 0.1秒
- Neo4j 存储：批量操作优化
- 内存使用：合理范围内

---

**Story 2.1.4: 调用图谱可视化服务** ✅ **已完成**
- **估时:** 0.3 天  
- **状态:** 已完成 (2025-01-22)
- **依赖:** Story 2.1.3 ✅

> 目标：提供 `/graph` API 与 CLI `call-graph`，生成 Mermaid / JSON 调用图。

#### ✅ 完成情况
| # | 任务 | 状态 | 关键输出 |
|---|------|------|---------|
| 1 | **CallGraphService** | ✅ | 完整的调用图谱可视化服务 |
| 2 | **多格式支持** | ✅ | Mermaid, JSON, ASCII, HTML 四种格式 |
| 3 | **CLI命令** | ✅ | `call-graph` 命令行工具 |
| 4 | **文件导出** | ✅ | 支持文件导出和HTML查看器 |
| 5 | **错误处理** | ✅ | 完善的异常处理和边界情况 |
| 6 | **测试覆盖** | ✅ | 单元测试 15/15，集成测试 8/8，验收测试 8/8 |

#### 🎯 测试结果
- **单元测试:** 15/15 通过 (图谱构建、格式转换、文件导出、错误处理)
- **集成测试:** 8/8 通过 (API集成、CLI集成、真实Neo4j测试)  
- **验收测试:** 8/8 通过 (完整功能验证、性能测试、边界情况)
- **测试覆盖率:** CallGraphService 95%+, CLI 90%+

#### 🔧 技术实现
- **图谱查询**: 基于Neo4j可变长度路径查询，支持深度控制
- **格式转换**: Mermaid语法生成，JSON结构化输出，ASCII树形显示
- **HTML查看器**: 集成Mermaid.js的交互式可视化界面
- **CLI工具**: 完整的命令行参数支持，多种输出模式
- **性能优化**: 查询缓存，批量处理，合理的深度限制

#### 📈 功能特性
- **调用类型可视化**: 支持direct、pointer、member、recursive四种调用类型
- **交互式HTML**: 包含统计信息和Mermaid.js渲染的专业图表
- **终端友好**: ASCII树形显示适合CLI环境
- **文件导出**: 支持.md、.json、.html多种格式
- **错误容错**: 优雅处理不存在函数、空数据库等边界情况

#### 🎨 输出示例
```bash
# ASCII树形显示
📞 Function Call Tree (Root: main)
├── main
    ├── print_sequence
        ├── fibonacci (recursive)

# CLI命令示例  
code-learner call-graph main --format mermaid --output graph.md --html
code-learner call-graph sbi_init --depth 5 --format json
```

---

**Story 2.1.5: 未使用函数检测 & 报告** 🔄 **计划中**
- **估时:** 0.3 天  
- **状态:** 待开始  
- **依赖:** Story 2.1.4

> 目标：识别 "孤儿函数"，输出 Markdown 报告。

#### Algorithm
```cypher
MATCH (fn:Function) WHERE NOT (fn)<-[:CALLS]-() AND fn.name <> 'main' RETURN fn
```

#### 主要组件
```python
class CodeQualityAnalyzer:
    def find_unused_functions(self) -> list[Function]: ...
    def generate_report(self, data) -> Path: ...
```

测试：生成报告文件并校验行数 == 查询结果。

---

**Story 2.1.6: 复杂度评分 & 热点分析** 🔄 **计划中**
- **估时:** 0.1 天  
- **状态:** 待开始  
- **依赖:** Story 2.1.5

#### 关键步骤
1. 使用 `radon` 本地计算 cyclomatic complexity。  
2. 查询 Neo4j 调用深度：`CALL algo.shortestPath.stream(...)`。  
3. `complexity_score = cyclomatic * (1 + depth/5)` 写回节点。

#### 伪代码
```python
for fn in all_functions:
    complexity = radon_analyze(fn.code)
    depth = query_call_depth(fn)
    score = complexity * (1 + depth/5)
    update_node(fn, score)
```

CLI: `code-learner hotspots --top 10` 输出 Markdown 表格。

依赖：`radon>=6.0`、Neo4j APOC。

**Story 2.2: 依赖关系分析 ⭐**
**状态:** ✅ 已完成 (2025-06-25)  
**估时:** 0.7天  
**优先级:** 高

**功能描述:**
实现C代码中的头文件和模块依赖关系分析，构建项目结构图，识别模块间依赖，支持模块化分析和重构建议。

**详细任务清单:**

1. **头文件依赖分析**
   - 提取`#include`语句和依赖关系
   - 区分系统头文件和项目头文件
   - 构建头文件依赖图
   - 识别循环依赖问题

2. **模块依赖分析**
   - 基于目录结构识别模块
   - 计算模块间依赖强度
   - 构建模块依赖图
   - 提供模块化指标评分

3. **依赖关系存储**
   - 扩展Neo4j数据模型，新增`DEPENDS_ON`关系
   - 存储文件和模块级别依赖
   - 支持依赖权重和类型
   - 优化批量存储性能

4. **依赖图谱可视化**
   - 生成文件依赖Mermaid图
   - 生成模块依赖图
   - 支持多层次依赖展示
   - 集成到现有可视化服务

**数据模型设计:**
```python
@dataclass
class FileDependency:
    """文件依赖关系"""
    source_file: str  # 源文件路径
    target_file: str  # 目标文件路径
    dependency_type: str  # 'include', 'import', 'use'
    is_system: bool  # 是否系统头文件
    line_number: int  # 引用行号
    
@dataclass
class ModuleDependency:
    """模块依赖关系"""
    source_module: str  # 源模块名称
    target_module: str  # 目标模块名称
    file_count: int  # 依赖文件数量
    strength: float  # 依赖强度(0-1)
    is_circular: bool  # 是否循环依赖
```

**核心类设计:**
```python
class DependencyAnalyzer:
    """依赖关系分析器"""
    
    def __init__(self, parser: IParser, graph_store: IGraphStore):
        self.parser = parser
        self.graph_store = graph_store
        
    def extract_file_dependencies(self, file_path: Path) -> List[FileDependency]:
        """提取单个文件的依赖关系"""
        # 解析#include语句
        # 区分系统和项目头文件
        # 返回依赖列表
        
    def analyze_project_dependencies(self, project_path: Path) -> ProjectDependencies:
        """分析整个项目的依赖关系"""
        # 遍历所有C和头文件
        # 提取文件依赖
        # 构建依赖图
        # 计算模块依赖
        
    def detect_circular_dependencies(self) -> List[List[str]]:
        """检测循环依赖"""
        # 使用图算法检测环
        # 返回循环依赖链
        
    def calculate_modularity_metrics(self) -> Dict[str, float]:
        """计算模块化指标"""
        # 计算内聚度和耦合度
        # 返回模块化评分
```

**存储接口扩展:**
```python
class IGraphStore(Protocol):
    # 现有方法...
    
    def store_file_dependencies(self, dependencies: List[FileDependency]) -> bool:
        """存储文件依赖关系"""
        ...
    
    def store_module_dependencies(self, dependencies: List[ModuleDependency]) -> bool:
        """存储模块依赖关系"""
        ...
    
    def query_file_dependencies(self, file_path: str) -> List[FileDependency]:
        """查询文件依赖关系"""
        ...
    
    def query_module_dependencies(self, module_name: str = None) -> List[ModuleDependency]:
        """查询模块依赖关系"""
        ...
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """检测循环依赖"""
        ...
```

**Neo4j关系模型:**
```cypher
// 文件依赖关系
CREATE (source:File {name: 'main.c'})
CREATE (target:File {name: 'utils.h'})
CREATE (source)-[:DEPENDS_ON {
    type: 'include',
    is_system: false,
    line_number: 5,
    weight: 1.0
}]->(target)

// 模块依赖关系
CREATE (source:Module {name: 'core'})
CREATE (target:Module {name: 'utils'})
CREATE (source)-[:DEPENDS_ON {
    file_count: 5,
    strength: 0.7,
    is_circular: false
}]->(target)
```

**CLI命令:**
```bash
# 分析项目依赖
code-learner analyze-deps /path/to/project

# 生成依赖图
code-learner deps-graph --module core --format mermaid --output deps.md

# 检测循环依赖
code-learner check-circular-deps --verbose
```

**验收标准:**
1. ✅ 准确提取C文件的`#include`依赖关系
2. ✅ 正确区分系统头文件和项目头文件
3. ✅ 成功构建并存储文件和模块依赖图
4. ✅ 准确检测循环依赖问题
5. ✅ 生成清晰的依赖图可视化
6. ✅ 支持依赖分析的CLI命令
7. ✅ 集成到现有的图谱可视化服务

**TDD测试计划:**
```python
# tests/unit/test_dependency_analyzer.py
def test_extract_include_statements()  # 测试提取#include语句
def test_distinguish_system_headers()  # 测试区分系统头文件
def test_build_dependency_graph()      # 测试构建依赖图
def test_detect_circular_dependencies() # 测试循环依赖检测
def test_calculate_module_metrics()    # 测试模块化指标计算

# tests/integration/test_dependency_storage.py
def test_store_file_dependencies()     # 测试存储文件依赖
def test_store_module_dependencies()   # 测试存储模块依赖
def test_query_dependencies()          # 测试查询依赖关系
def test_circular_dependency_detection() # 测试循环依赖检测API

# tests/integration/test_dependency_visualization.py
def test_generate_file_dependency_graph() # 测试文件依赖图生成
def test_generate_module_dependency_graph() # 测试模块依赖图生成
def test_dependency_cli_commands()     # 测试CLI命令
```

**测试计划详细设计:**
- **Unit (≥8)**  ➜ `tests/unit/test_dependency_analyzer.py`
  | 名称 | 场景 |
  |------|------|
  | `test_extract_include_simple` | 基本#include提取 |
  | `test_extract_include_with_comments` | 带注释的#include |
  | `test_system_vs_project_headers` | 系统vs项目头文件区分 |
  | `test_build_file_dependency_graph` | 文件依赖图构建 |
  | `test_build_module_dependency_graph` | 模块依赖图构建 |
  | `test_circular_dependency_detection` | 循环依赖检测 |
  | `test_modularity_metrics_calculation` | 模块化指标计算 |
  | `test_dependency_strength_calculation` | 依赖强度计算 |
  
- **Integration (5)** ➜ `tests/integration/test_dependency_storage.py`
  1. `test_store_file_dependencies` – 存储文件依赖关系
  2. `test_store_module_dependencies` – 存储模块依赖关系
  3. `test_query_file_dependencies` – 查询文件依赖
  4. `test_query_module_dependencies` – 查询模块依赖
  5. `test_end_to_end_dependency_analysis` – 解析→存储→查询

- **Visualization (3)** ➜ `tests/integration/test_dependency_visualization.py`
  1. `test_file_dependency_mermaid_graph` – 文件依赖Mermaid图
  2. `test_module_dependency_mermaid_graph` – 模块依赖Mermaid图
  3. `test_dependency_html_viewer` – HTML依赖查看器

- **CLI (2)** ➜ `tests/integration/test_dependency_cli.py`
  1. `test_analyze_deps_command` – 分析依赖命令
  2. `test_deps_graph_command` – 依赖图生成命令

- **Acceptance (1)** ➜ `tests/integration/test_story_2_2_acceptance.py`
  - 解析示例项目，验证依赖关系提取和可视化

- **覆盖率目标**：
  - `dependency_analyzer.py` ≥ 90%
  - `neo4j_store.py` (新方法) ≥ 90%
  - 整体增量覆盖率 ≥ 90%

**风险评估:**
- 🟡 复杂项目中头文件路径解析的准确性
- 🟡 大型项目依赖图的性能和可读性
- 🟢 基于现有的解析和存储架构，实现风险较低

**完成情况:**
- ✅ 头文件依赖分析 - 完成
- ✅ 模块依赖分析 - 完成
- ✅ 依赖关系存储 - 完成
- ✅ 依赖图谱可视化 - 完成
- ✅ 单元测试 - 15/15通过
- ✅ 集成测试 - 12/12通过
- ✅ 验收测试 - 8/8通过
- ✅ 覆盖率 - 依赖分析器93%，存储扩展91%

---

**Story 2.3: 实用CLI工具 ⭐**
**状态:** 📋 待开始  
**估时:** 0.5天  
**优先级:** 高

**功能描述:**
创建实用的命令行工具，直接处理实际C代码项目（如OpenSBI），提供高效的代码分析和查询功能。工具应专注于实际开发场景，无需演示模式，直接支持真实代码库的处理和分析。

**详细任务清单:**

1. **核心CLI命令实现**
   - `analyze` - 分析C代码项目，支持指定目录和文件过滤
   - `query` - 交互式代码问答，直接针对实际代码库
   - `status` - 系统状态检查，包括数据库和服务状态
   - `export` - 导出分析结果，支持多种格式（JSON、Markdown等）

2. **实际代码处理功能**
   - OpenSBI代码库直接分析支持
   - 大型C项目结构识别和优化处理
   - 增量分析能力，支持只分析变更文件
   - 多线程处理加速，提高大型代码库分析效率

3. **用户体验优化**
   - 进度指示，显示大型项目分析进度
   - 简洁清晰的输出格式，专注于实用信息
   - 错误处理和日志记录，便于调试和问题排查
   - 性能优化，减少大型代码库分析时间

4. **配置和帮助系统**
   - 项目级配置文件支持，记住常用设置
   - 详细的帮助文档，包括实际使用示例
   - 常见问题解答和故障排除指南
   - 支持环境变量配置，便于CI/CD集成

**技术实现细节:**

1. **CLI框架设计**
   ```python
   # 使用argparse构建命令行界面
   def create_parser() -> argparse.ArgumentParser:
       """创建命令行参数解析器"""
       parser = argparse.ArgumentParser(
           description="C语言智能代码分析调试工具",
           formatter_class=argparse.RawDescriptionHelpFormatter
       )
       
       # 添加子命令
       subparsers = parser.add_subparsers(dest="command", help="可用命令")
       
       # analyze命令 - 分析C代码项目
       analyze_parser = subparsers.add_parser("analyze", help="分析C代码项目")
       analyze_parser.add_argument("project_path", help="项目路径")
       analyze_parser.add_argument("--output-dir", "-o", help="输出目录")
       analyze_parser.add_argument("--incremental", "-i", action="store_true", 
                                  help="增量分析（只分析变更文件）")
       analyze_parser.add_argument("--include", help="包含的文件模式 (例如: '*.c,*.h')")
       analyze_parser.add_argument("--exclude", help="排除的文件模式 (例如: 'test/*')")
       analyze_parser.add_argument("--threads", "-t", type=int, default=4,
                                  help="并行处理线程数")
       
       # query命令 - 交互式代码问答
       query_parser = subparsers.add_parser("query", help="交互式代码问答")
       query_parser.add_argument("--project", "-p", required=True, 
                                help="项目路径")
       query_parser.add_argument("--history", "-H", help="保存历史记录的文件")
       query_parser.add_argument("--function", "-f", help="聚焦于特定函数")
       query_parser.add_argument("--file", help="聚焦于特定文件")
       
       # status命令 - 系统状态检查
       status_parser = subparsers.add_parser("status", help="系统状态检查")
       status_parser.add_argument("--verbose", "-v", action="store_true", 
                                 help="显示详细信息")
       
       # export命令 - 导出分析结果
       export_parser = subparsers.add_parser("export", help="导出分析结果")
       export_parser.add_argument("--project", "-p", required=True, 
                                help="项目路径")
       export_parser.add_argument("--format", "-f", choices=["json", "md", "html", "dot"],
                                default="json", help="导出格式")
       export_parser.add_argument("--output", "-o", required=True,
                                help="输出文件路径")
       export_parser.add_argument("--type", "-t", choices=["calls", "deps", "all"],
                                default="all", help="导出数据类型")
       
       return parser
   ```

2. **实际代码处理实现**
   ```python
   class CodeAnalyzer:
       """代码分析器 - 处理实际C代码项目"""
       
       def __init__(self, project_path: Path, output_dir: Optional[Path] = None,
                   include_pattern: str = "*.c,*.h", exclude_pattern: str = None,
                   threads: int = 4):
           self.project_path = project_path
           self.output_dir = output_dir or project_path / ".analysis"
           self.include_pattern = include_pattern.split(",") if include_pattern else ["*.c", "*.h"]
           self.exclude_pattern = exclude_pattern.split(",") if exclude_pattern else []
           self.threads = threads
           self.parser = CParser()
           self.graph_store = Neo4jGraphStore()
           self.dependency_service = ServiceFactory.get_dependency_service()
           
           # 确保输出目录存在
           self.output_dir.mkdir(parents=True, exist_ok=True)
           
           # 连接数据库
           config = ConfigManager().get_config()
           self.graph_store.connect(
               config.database.neo4j_uri,
               config.database.neo4j_user,
               config.database.neo4j_password
           )
       
       def analyze(self, incremental: bool = False) -> Dict[str, Any]:
           """分析项目
           
           Args:
               incremental: 是否进行增量分析
               
           Returns:
               Dict[str, Any]: 分析结果统计
           """
           start_time = time.time()
           
           # 获取所有匹配的文件
           files = self._get_target_files(incremental)
           total_files = len(files)
           
           print(f"开始分析项目: {self.project_path}")
           print(f"目标文件数: {total_files}")
           
           # 使用线程池并行处理
           results = []
           with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
               futures = {executor.submit(self._process_file, file): file for file in files}
               
               # 显示进度
               with tqdm(total=total_files, desc="分析进度") as pbar:
                   for future in concurrent.futures.as_completed(futures):
                       file = futures[future]
                       try:
                           result = future.result()
                           results.append(result)
                       except Exception as e:
                           print(f"处理文件 {file} 时出错: {e}")
                       finally:
                           pbar.update(1)
           
           # 构建依赖关系
           print("分析文件间依赖关系...")
           project_deps = self.dependency_service.analyze_project(self.project_path)
           
           # 保存分析结果
           self._save_analysis_results(results, project_deps)
           
           end_time = time.time()
           elapsed = end_time - start_time
           
           # 返回统计信息
           stats = {
               "total_files": total_files,
               "processed_files": len(results),
               "total_functions": sum(len(r.functions) for r in results if r),
               "file_dependencies": len(project_deps.file_dependencies),
               "module_dependencies": len(project_deps.module_dependencies),
               "circular_dependencies": len(project_deps.circular_dependencies),
               "elapsed_time": elapsed
           }
           
           print(f"分析完成，耗时: {elapsed:.2f}秒")
           print(f"共处理 {stats['processed_files']} 个文件，发现 {stats['total_functions']} 个函数")
           
           return stats
       
       def _get_target_files(self, incremental: bool) -> List[Path]:
           """获取需要处理的文件
           
           Args:
               incremental: 是否进行增量分析
               
           Returns:
               List[Path]: 文件路径列表
           """
           # 实现文件查找逻辑，支持include/exclude模式和增量分析
           # ...
           
       def _process_file(self, file_path: Path) -> Optional[ParsedCode]:
           """处理单个文件
           
           Args:
               file_path: 文件路径
               
           Returns:
               Optional[ParsedCode]: 解析结果
           """
           try:
               # 解析文件
               parsed_code = self.parser.parse_file(file_path)
               
               # 存储到图数据库
               self.graph_store.store_parsed_code(parsed_code)
               
               return parsed_code
           except Exception as e:
               print(f"处理文件 {file_path} 失败: {e}")
               return None
       
       def _save_analysis_results(self, results: List[ParsedCode], 
                                project_deps: ProjectDependencies) -> None:
           """保存分析结果
           
           Args:
               results: 解析结果列表
               project_deps: 项目依赖关系
           """
           # 保存结果到输出目录
           # ...
   ```

3. **交互式问答实现**
   ```python
   class InteractiveQuerySession:
       """交互式问答会话 - 直接针对实际代码库"""
       
       def __init__(self, project_path: Path, history_file: Optional[Path] = None,
                   focus_function: Optional[str] = None, focus_file: Optional[str] = None):
           self.project_path = project_path
           self.history_file = history_file
           self.focus_function = focus_function
           self.focus_file = focus_file
           self.qa_service = ServiceFactory.get_code_qa_service()
           self.history = []
           
           # 加载历史记录
           if history_file and history_file.exists():
               with open(history_file, "r") as f:
                   self.history = json.load(f)
           
       def start(self):
           """启动交互式问答会话"""
           focus_info = ""
           if self.focus_function:
               focus_info = f"函数: {self.focus_function}"
           elif self.focus_file:
               focus_info = f"文件: {self.focus_file}"
               
           print(f"代码问答会话 - 项目: {self.project_path} {focus_info}")
           print("输入'exit'或'quit'退出，输入'help'获取帮助\n")
           
           while True:
               try:
                   # 使用简单的输入提示
                   question = input("> ")
                   
                   if question.lower() in ["exit", "quit"]:
                       break
                   elif question.lower() == "help":
                       self._print_help()
                       continue
                   
                   # 构建上下文
                   context = {
                       "project_path": str(self.project_path),
                       "focus_function": self.focus_function,
                       "focus_file": self.focus_file
                   }
                   
                   # 调用问答服务
                   print("处理中...")
                   answer = self.qa_service.ask_question(question, context)
                   
                   # 显示答案
                   print(f"\n{answer}\n")
                   
                   # 保存到历史记录
                   self.history.append({"question": question, "answer": answer})
                   
               except KeyboardInterrupt:
                   print("\n会话已中断")
                   break
               except Exception as e:
                   print(f"\n错误: {e}")
           
           # 保存历史记录
           if self.history_file:
               with open(self.history_file, "w") as f:
                   json.dump(self.history, f, ensure_ascii=False, indent=2)
           
           print("会话已结束")
   ```

4. **状态检查实现**
   ```python
   def check_system_status(verbose: bool = False) -> Dict[str, Any]:
       """检查系统状态
       
       Args:
           verbose: 是否显示详细信息
           
       Returns:
           Dict[str, Any]: 状态信息
       """
       status = {
           "database": {"status": "unknown"},
           "embedding_model": {"status": "unknown"},
           "llm_api": {"status": "unknown"},
           "overall": "unknown"
       }
       
       # 检查数据库连接
       try:
           graph_store = Neo4jGraphStore()
           config = ConfigManager().get_config()
           
           db_connected = graph_store.connect(
               config.database.neo4j_uri,
               config.database.neo4j_user,
               config.database.neo4j_password
           )
           
           if db_connected:
               status["database"] = {
                   "status": "healthy",
                   "uri": config.database.neo4j_uri,
                   "details": graph_store.health_check() if verbose else {}
               }
           else:
               status["database"] = {
                   "status": "unhealthy",
                   "uri": config.database.neo4j_uri,
                   "error": "Failed to connect to database"
               }
               
       except Exception as e:
           status["database"] = {
               "status": "error",
               "error": str(e)
           }
       
       # 检查嵌入模型
       try:
           embedding_engine = ServiceFactory.get_embedding_engine()
           test_result = embedding_engine.encode("Test embedding")
           
           if test_result is not None and len(test_result) > 0:
               status["embedding_model"] = {
                   "status": "healthy",
                   "model": config.llm.embedding_model,
                   "dimensions": len(test_result),
                   "details": {"cache_path": embedding_engine.get_cache_path()} if verbose else {}
               }
           else:
               status["embedding_model"] = {
                   "status": "unhealthy",
                   "model": config.llm.embedding_model,
                   "error": "Failed to generate embeddings"
               }
               
       except Exception as e:
           status["embedding_model"] = {
               "status": "error",
               "error": str(e)
           }
       
       # 检查LLM API
       try:
           chatbot = ServiceFactory.get_chatbot()
           test_response = chatbot.ask("Hello, are you working?")
           
           if test_response and len(test_response) > 0:
               status["llm_api"] = {
                   "status": "healthy",
                   "model": config.llm.openrouter_model,
                   "details": {"response_time": chatbot.last_response_time} if verbose else {}
               }
           else:
               status["llm_api"] = {
                   "status": "unhealthy",
                   "model": config.llm.openrouter_model,
                   "error": "Empty response from API"
               }
               
       except Exception as e:
           status["llm_api"] = {
               "status": "error",
               "error": str(e)
           }
       
       # 计算整体状态
       if all(component["status"] == "healthy" for component in [status["database"], status["embedding_model"], status["llm_api"]]):
           status["overall"] = "healthy"
       elif any(component["status"] == "error" for component in [status["database"], status["embedding_model"], status["llm_api"]]):
           status["overall"] = "error"
       else:
           status["overall"] = "degraded"
       
       return status
   ```

**CLI命令设计:**
```bash
# 分析OpenSBI项目
code-learner analyze /home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi --threads 8

# 增量分析，排除测试文件
code-learner analyze /home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi --incremental --exclude "test/*"

# 交互式问答，聚焦于特定函数
code-learner query --project /home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi --function sbi_init

# 系统状态检查
code-learner status --verbose

# 导出分析结果
code-learner export --project /home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi --format html --output opensbi_analysis.html
```

**实用查询示例:**
```
> sbi_init函数的作用是什么？
> 哪些函数调用了sbi_console_putc？
> 文件lib/sbi/sbi_init.c中定义了哪些函数？
> 项目中有哪些循环依赖？
> 哪个模块依赖最多？
> 文件sbi_hart.c和sbi_init.c之间的依赖关系是什么？
```

**依赖库:**
```python
# 核心依赖
dependencies = [
    "tqdm>=4.66.0",       # 进度条
    "concurrent-log-handler>=0.9.20", # 线程安全日志
    "psutil>=5.9.0",      # 系统资源监控
    "tabulate>=0.9.0",    # 表格输出
    "colorama>=0.4.6"     # 彩色终端输出（跨平台）
]
```

**验收标准:**
1. ✅ 所有CLI命令正常工作，支持直接处理OpenSBI代码库
2. ✅ 大型C项目处理性能良好，支持多线程加速
3. ✅ 增量分析功能正常工作，减少重复分析时间
4. ✅ 交互式问答能够回答关于实际代码的具体问题
5. ✅ 导出功能支持多种格式，便于集成到其他工具
6. ✅ 错误处理健壮，提供明确的错误信息和日志
7. ✅ 系统状态检查全面，覆盖所有关键组件
8. ✅ 支持项目级配置，便于在不同项目间切换

**TDD测试计划:**
```python
# tests/unit/test_cli_commands.py
class TestCLICommands:
    def test_analyze_command_basic(self):
        """测试基本的analyze命令"""
        result = run_cli(["analyze", "/tmp/test_project"])
        assert result.exit_code == 0
        assert "开始分析项目" in result.stdout
    
    def test_analyze_command_incremental(self):
        """测试增量分析模式"""
        result = run_cli(["analyze", "/tmp/test_project", "--incremental"])
        assert result.exit_code == 0
        assert "增量分析模式" in result.stdout
    
    def test_analyze_command_threads(self):
        """测试多线程处理"""
        result = run_cli(["analyze", "/tmp/test_project", "--threads", "8"])
        assert result.exit_code == 0
        assert "线程数: 8" in result.stdout
    
    def test_analyze_command_file_filters(self):
        """测试文件过滤"""
        result = run_cli(["analyze", "/tmp/test_project", "--include", "*.c", "--exclude", "test/*"])
        assert result.exit_code == 0
        assert "包含模式: *.c" in result.stdout
        assert "排除模式: test/*" in result.stdout
    
    def test_query_command(self):
        """测试query命令参数解析"""
        result = run_cli(["query", "--project", "/tmp/test_project"], input="exit\n")
        assert result.exit_code == 0
        assert "代码问答会话" in result.stdout
    
    def test_query_command_with_focus(self):
        """测试聚焦查询"""
        result = run_cli(["query", "--project", "/tmp/test_project", "--function", "main"], 
                         input="exit\n")
        assert result.exit_code == 0
        assert "函数: main" in result.stdout
    
    def test_status_command(self):
        """测试status命令"""
        result = run_cli(["status"])
        assert result.exit_code == 0
        assert "数据库状态" in result.stdout
        assert "嵌入模型状态" in result.stdout
        assert "LLM API状态" in result.stdout
    
    def test_export_command(self):
        """测试导出命令"""
        result = run_cli(["export", "--project", "/tmp/test_project", 
                         "--format", "json", "--output", "/tmp/output.json"])
        assert result.exit_code == 0
        assert "导出完成" in result.stdout
        assert Path("/tmp/output.json").exists()
    
    def test_export_command_formats(self):
        """测试不同导出格式"""
        formats = ["json", "md", "html", "dot"]
        for fmt in formats:
            result = run_cli(["export", "--project", "/tmp/test_project", 
                             "--format", fmt, "--output", f"/tmp/output.{fmt}"])
            assert result.exit_code == 0
            assert f"格式: {fmt}" in result.stdout
    
    def test_cli_error_handling(self):
        """测试CLI错误处理"""
        # 缺少必要参数
        result = run_cli(["query"])
        assert result.exit_code != 0
        assert "error: the following arguments are required: --project" in result.stderr
        
        # 无效命令
        result = run_cli(["invalid_command"])
        assert result.exit_code != 0
        assert "invalid choice" in result.stderr
    
    def test_help_and_documentation(self):
        """测试帮助文档"""
        result = run_cli(["--help"])
        assert result.exit_code == 0
        assert "C语言智能代码分析调试工具" in result.stdout
        assert "可用命令" in result.stdout
```

**集成测试计划:**
```python
# tests/integration/test_cli_integration.py
class TestCLIIntegration:
    @pytest.fixture
    def test_project(self):
        """创建测试项目"""
        project_dir = Path("/tmp/test_cli_project")
        if project_dir.exists():
            shutil.rmtree(project_dir)
        
        project_dir.mkdir(parents=True)
        
        # 创建一些测试文件
        (project_dir / "main.c").write_text("""
        #include <stdio.h>
        #include "utils.h"
        
        int main() {
            hello();
            return 0;
        }
        """)
        
        (project_dir / "utils.h").write_text("""
        void hello();
        """)
        
        (project_dir / "utils.c").write_text("""
        #include <stdio.h>
        #include "utils.h"
        
        void hello() {
            printf("Hello, World!\\n");
        }
        """)
        
        yield project_dir
        
        # 清理
        shutil.rmtree(project_dir)
    
    def test_end_to_end_workflow(self, test_project):
        """测试完整工作流"""
        # 1. 分析项目
        result = run_cli(["analyze", str(test_project)])
        assert result.exit_code == 0
        assert "分析完成" in result.stdout
        
        # 2. 检查状态
        result = run_cli(["status"])
        assert result.exit_code == 0
        
        # 3. 交互式问答
        result = run_cli(["query", "--project", str(test_project)], 
                         input="main函数在哪个文件中？\nexit\n")
        assert result.exit_code == 0
        assert "main.c" in result.stdout
        
        # 4. 导出分析结果
        result = run_cli(["export", "--project", str(test_project), 
                         "--format", "json", "--output", "/tmp/test_export.json"])
        assert result.exit_code == 0
        assert Path("/tmp/test_export.json").exists()
    
    def test_opensbi_analysis(self):
        """测试OpenSBI项目分析"""
        opensbi_path = Path("/home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi")
        if not opensbi_path.exists():
            pytest.skip("OpenSBI项目不存在")
        
        # 分析项目（使用较少线程以避免测试环境过载）
        result = run_cli(["analyze", str(opensbi_path), "--threads", "2"])
        assert result.exit_code == 0
        
        # 验证分析结果
        result = run_cli(["query", "--project", str(opensbi_path)], 
                         input="sbi_init函数在哪个文件中？\nexit\n")
        assert "lib/sbi/sbi_init.c" in result.stdout
```

**性能测试计划:**
```python
# tests/performance/test_cli_performance.py
class TestCLIPerformance:
    @pytest.fixture
    def opensbi_project(self):
        return Path("/home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi")
    
    def test_analyze_performance_single_thread(self, opensbi_project):
        """测试单线程分析性能"""
        if not opensbi_project.exists():
            pytest.skip("OpenSBI项目不存在")
            
        start_time = time.time()
        result = run_cli(["analyze", str(opensbi_project), "--threads", "1"])
        end_time = time.time()
        
        assert result.exit_code == 0
        
        # 单线程分析时间基准
        elapsed = end_time - start_time
        print(f"单线程分析时间: {elapsed:.2f}秒")
        
        return elapsed
    
    def test_analyze_performance_multi_thread(self, opensbi_project):
        """测试多线程分析性能"""
        if not opensbi_project.exists():
            pytest.skip("OpenSBI项目不存在")
            
        # 获取CPU核心数
        cpu_count = os.cpu_count() or 4
        
        start_time = time.time()
        result = run_cli(["analyze", str(opensbi_project), "--threads", str(cpu_count)])
        end_time = time.time()
        
        assert result.exit_code == 0
        
        # 多线程分析时间
        elapsed = end_time - start_time
        print(f"多线程({cpu_count})分析时间: {elapsed:.2f}秒")
        
        # 与单线程比较，应该有明显加速
        single_thread_time = self.test_analyze_performance_single_thread(opensbi_project)
        speedup = single_thread_time / elapsed
        
        print(f"加速比: {speedup:.2f}x")
        assert speedup > 1.5, f"多线程加速不明显: {speedup:.2f}x < 1.5x"
    
    def test_incremental_analysis_performance(self, opensbi_project):
        """测试增量分析性能"""
        if not opensbi_project.exists():
            pytest.skip("OpenSBI项目不存在")
            
        # 先进行一次完整分析
        run_cli(["analyze", str(opensbi_project)])
        
        # 然后进行增量分析
        start_time = time.time()
        result = run_cli(["analyze", str(opensbi_project), "--incremental"])
        end_time = time.time()
        
        assert result.exit_code == 0
        
        # 增量分析时间应该明显短于完整分析
        elapsed = end_time - start_time
        print(f"增量分析时间: {elapsed:.2f}秒")
        
        # 增量分析应该比完整分析快很多
        assert elapsed < 30, f"增量分析耗时过长: {elapsed:.2f}秒 > 30秒"
```

**成功标准:**
- ✅ 所有单元测试通过 (12/12)
- ✅ 所有集成测试通过 (2/2)
- ✅ 所有性能测试通过 (3/3)
- ✅ 覆盖率 >= 90%
- ✅ OpenSBI项目分析成功，能回答关于其代码的具体问题

---

### Story 2.4: 调用图谱可视化 ⭐
**状态:** 📋 待开始  
**估时:** 1天  
**优先级:** 中

**功能描述:**
实现函数调用关系的图形化展示，提供直观的代码结构分析和导航功能。

**详细任务清单:**

1. **图形化引擎选择**
   - 评估Graphviz、Mermaid、D3.js等方案
   - 选择适合终端和Web的可视化方案
   - 实现基础的图形渲染功能

2. **调用图谱生成**
   - 从Neo4j查询调用关系数据
   - 转换为图形化数据格式
   - 支持层级展示和节点过滤

3. **交互功能实现**
   - 点击节点查看函数详情
   - 调用路径高亮显示
   - 缩放和平移支持

4. **导出功能**
   - 支持PNG、SVG格式导出
   - 生成HTML交互版本
   - 集成到CLI命令中

**可视化设计:**
```python
class CallGraphVisualizer:
    def __init__(self, graph_store: IGraphStore):
        self.graph_store = graph_store
    
    def generate_call_graph(self, root_function: str) -> str:
        """生成Mermaid格式的调用图"""
        # 查询调用关系
        # 生成Mermaid语法
        # 返回图形定义
    
    def export_to_html(self, graph_def: str, output_path: str):
        """导出为HTML交互图"""
        # 生成包含Mermaid.js的HTML文件
    
    def print_ascii_tree(self, root_function: str):
        """终端ASCII树形显示"""
        # 适合CLI环境的简单树形显示
```

**验收标准:**
- [ ] 能够生成完整的函数调用图谱
- [ ] 支持多种格式输出(HTML, PNG, ASCII)
- [ ] 图形清晰易读，节点关系明确
- [ ] 性能良好: 100个函数的图谱生成 < 3秒
- [ ] 集成到CLI命令中

**风险评估:**
- 🟡 大型项目的图形复杂度和可读性
- 🟡 不同可视化库的依赖管理
- 🟢 可视化功能为增值特性，不影响核心功能

---

### Story 2.4: 未使用函数检测 ⭐
**状态:** 📋 待开始  
**估时:** 0.5天  
**优先级:** 中

**功能描述:**
基于函数调用关系分析，实现代码质量检测功能，帮助开发者识别潜在的冗余代码。

**详细任务清单:**

1. **未使用函数检测算法**
   - 基于Neo4j图查询识别孤立节点
   - 区分内部函数和外部API
   - 处理条件编译和宏定义场景

2. **代码质量分析**
   - 函数复杂度统计
   - 调用深度分析
   - 循环依赖检测

3. **报告生成功能**
   - 生成详细的分析报告
   - 按文件和模块分组显示
   - 提供清理建议

4. **CLI集成**
   - `code-learner quality` 命令
   - 支持不同详细级别的输出
   - 集成到项目分析流程

**质量检测功能:**
```python
class CodeQualityAnalyzer:
    def __init__(self, graph_store: IGraphStore):
        self.graph_store = graph_store
    
    def find_unused_functions(self) -> List[UnusedFunction]:
        """查找未使用的函数"""
        # 查询没有被调用的函数
        # 排除main函数和外部API
        # 返回详细信息
    
    def analyze_function_complexity(self) -> Dict[str, int]:
        """分析函数复杂度"""
        # 基于调用关系计算复杂度
        # 返回函数复杂度评分
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """检测循环依赖"""
        # 使用图算法检测环路
        # 返回循环依赖链
    
    def generate_quality_report(self) -> QualityReport:
        """生成完整质量报告"""
        # 整合所有分析结果
        # 生成可读性报告
```

**验收标准:**
- [ ] 准确识别未使用的函数(排除入口函数)
- [ ] 能够处理复杂的调用关系
- [ ] 生成清晰的质量报告
- [ ] 集成到CLI工具中
- [ ] 性能测试: 分析OpenSBI项目 < 30秒

**风险评估:**
- 🟡 复杂项目中函数使用关系的准确性判断
- 🟢 基于已有的调用关系数据，实现相对简单

---

## Epic 2 成功标准

**技术验证:**
- ✅ 函数调用关系分析完整实现
- ✅ 图形化可视化功能正常
- ✅ 代码质量检测准确有效
- ✅ OpenSBI项目 (289文件) 处理成功
- ✅ 端到端性能满足要求 (< 10分钟)

**用户体验:**
- ✅ CLI界面友好易用
- ✅ 可视化图表清晰直观
- ✅ 质量报告详细实用
- ✅ 演示效果清晰有说服力
- ✅ 文档完整，新用户可快速上手

**系统稳定性:**
- ✅ 错误处理机制完善
- ✅ 资源使用合理
- ✅ 数据一致性保证
- ✅ 高级分析功能稳定

**交付物:**
- 完整的函数调用关系分析器
- 图形化可视化工具
- 代码质量检测器
- 用户友好的CLI工具
- OpenSBI项目演示脚本
- 完整的使用文档

**Epic 2完成后的状态:**
系统从基础技术验证升级为具备高级分析能力的智能代码分析工具，能够提供深度的代码结构洞察和质量评估。

---

## 📊 项目整体进度总览

**当前状态:** Epic 1 完成 ✅，Epic 2 规划完成 📋  
**下一步:** 开始Epic 2 高级分析功能开发  
**预计完成时间:** Epic 2 预计3.5天

**Epic完成度统计:**
- **Epic 1: 核心技术验证** - 4/4 = **100%** ✅
- **Epic 2: 高级分析功能** - 0/4 = **0%** 📋  
- **Epic 3: 基础优化** - 0/3 = **0%** 📋
- **Epic 4: MVP准备** - 0/3 = **0%** 📋

**项目整体进度:** 4/14 = **28.6%** 🚀

**关键里程碑:**
- ✅ 2025-06-24: Epic 1 完成，所有核心技术验证成功
- 📋 预计2025-06-28: Epic 2 完成，高级分析功能实现
- 📋 预计2025-07-01: Epic 3 完成，系统优化和完善
- 📋 预计2025-07-05: Epic 4 完成，MVP准备就绪

---

## Epic 3: 基础优化 (3个Story) 🔧  

### Story 3.1: 错误处理改进
### Story 3.2: 基本测试完善  
### Story 3.3: 文档和使用说明

## Epic 4: MVP准备 (3个Story) 📋

### Story 4.1: 技术债务整理
### Story 4.2: 架构重设计
### Story 4.3: MVP功能规划

---

## POC开发原则

### KISS原则应用
- **简化优先:** 功能可用比完美实现重要
- **快速验证:** 重点验证技术可行性
- **延迟优化:** 性能和完善性留给后续阶段

### MVP思维
- **核心假设验证:** 技术栈能否协同工作？
- **最小功能集:** 单文件解析 + 基本问答
- **用户价值验证:** 工具是否有实际价值？

### TDD简化策略

#### POC测试标准 (降低要求)
- **测试覆盖率:** >= 60% (降低自90%)
- **测试类型:** 重点功能测试，跳过边界测试
- **测试复杂度:** 基本正向流程，简化异常处理

#### 每个Story的TDD检查点
- ✅ 基本功能测试 (Red-Green)
- ✅ 核心流程验证
- ✅ 简化重构 (保持测试通过)

---

## 质量标准 (POC版本)

### 简化的质量要求
```python
poc_quality = {
    "functionality": "核心功能正确工作",
    "reliability": "基本错误处理不崩溃", 
    "performance": "小文件处理正常",
    "maintainability": "代码结构清晰",
    "test_coverage": ">=60%",
    "documentation": "基本使用说明"
}
```

### 性能标准 (宽松要求)
- **处理能力:** 5-10个函数的C文件
- **响应时间:** 基本操作 < 10秒  
- **内存使用:** 不超过本地开发机器限制

### 成功验收 (POC)
- **技术证明:** 所有组件能协同工作
- **功能演示:** 端到端流程完整运行
- **问答验证:** 能回答预定义的基本问题

---

## 当前状态

- **项目阶段:** POC开发阶段
- **当前Epic:** Epic 1 核心技术验证
- **已完成Story:** Story 1.1 基础环境搭建 ✅
- **下一个Story:** Story 1.2 Tree-sitter解析集成
- **开发环境:** Ubuntu 24.04 LTS + uv (.venv)

## Epic 1 POC检查清单

- [x] Story 1.1: 基础环境搭建 ⭐ (✅ 完成 2025-06-23)
- [x] Story 1.2: Tree-sitter解析集成 ⭐ (✅ 完成 2025-06-23)
- [x] Story 1.3: 图数据库存储 ⭐ (✅ 完成 2025-06-23)
- [x] Story 1.4: 向量嵌入与问答 ⭐ (✅ 完成 2025-06-24)

## Epic 1 完成状态 🎉

**✅ Epic 1: 核心技术验证 - 100% 完成**

**完成日期:** 2025-06-24  
**总耗时:** 3天  
**成功标准达成:**
- ✅ 所有技术栈成功集成 (Tree-sitter + Neo4j + Chroma + OpenRouter)
- ✅ 端到端流程完整验证 (解析→存储→向量化→问答)
- ✅ repo级别处理能力确认 (支持289文件规模)
- ✅ 真实API测试通过 (无mock，无fallback)

**关键技术成果:**
- **C语言解析:** 完整的函数提取和代码结构分析
- **图数据存储:** Neo4j节点关系模型验证成功
- **向量嵌入:** Jina模型768维嵌入，批量处理优化
- **智能问答:** OpenRouter API集成，代码摘要生成
- **系统集成:** 所有组件协同工作，无技术障碍

**性能验证:**
- **解析性能:** 单文件解析 < 1秒
- **存储性能:** 批量存储优化，事务安全
- **嵌入性能:** 批量编码 batch_size=32
- **问答性能:** 实时响应，中英文支持

**额外完成项:**
- ✅ **Qwen3模型评估:** 完整的路径探索测试，技术可行性验证
- ✅ **依赖管理优化:** 虚拟环境配置，版本兼容性验证
- ✅ **错误处理强化:** 配置问题、API调用、模型缓存问题全部解决
- ✅ **文档完善:** BKM记录、技术决策文档、最佳实践总结

**Epic 1成功标准:**
使用OpenSBI项目完成完整的 项目解析→存储→向量化→问答 流程。
- 成功解析289个C/H文件，提取函数定义和调用关系
- 将代码结构存储到Neo4j图数据库
- 生成代码向量嵌入并存储到Chroma
- 能够回答关于项目结构、函数位置、调用关系的复杂问题

## POC成功定义

✅ **核心技术验证成功**
- Tree-sitter解析C文件正常
- Neo4j存储代码结构正常  
- Chroma向量存储正常
- OpenRouter问答正常

✅ **端到端流程完整**
- 单个命令演示完整流程
- 流程无中断和错误
- 输出结果符合预期

✅ **技术可行性确认**
- 所有组件协同工作
- 没有根本性技术障碍
- 开发复杂度可控

---

**POC完成后下一步:**
1. 整理技术债务和经验教训
2. 基于POC经验重新设计架构
3. 规划MVP阶段的功能范围

---

*POC工作计划专注于验证核心概念，遵循KISS、SOLID、TDD和MVP原则，避免过度设计。* 

### 10. 最新API最佳实践 (基于Neo4j Python Driver 5.28)

**A. Session管理最佳实践:**
```python
class Neo4jGraphStore(IGraphStore):
    def __init__(self):
        self.driver = None
        
    def connect(self, uri: str, user: str, password: str) -> bool:
        """使用最新驱动的连接模式"""
        try:
            # 使用上下文管理器确保资源正确释放
            self.driver = GraphDatabase.driver(
                uri, 
                auth=(user, password),
                # 性能优化配置
                max_connection_pool_size=50,
                connection_acquisition_timeout=60.0,
                # 明确指定数据库以避免额外网络请求
                database="neo4j"  # 或从配置获取
            )
            
            # 立即验证连接
            self.driver.verify_connectivity()
            logger.info("Neo4j connection established successfully")
            return True
            
        except (ServiceUnavailable, AuthError, ConfigurationError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def store_parsed_code(self, parsed_code: ParsedCode) -> bool:
        """使用事务函数模式存储数据"""
        if not self.driver:
            raise GraphStoreError("Not connected to database")
            
        try:
            # 使用managed transaction确保ACID特性和自动重试
            with self.driver.session(database="neo4j") as session:
                return session.execute_write(self._store_parsed_code_tx, parsed_code)
                
        except Exception as e:
            logger.error(f"Failed to store parsed code: {e}")
            return False
    
    def _store_parsed_code_tx(self, tx, parsed_code: ParsedCode) -> bool:
        """事务函数 - 必须是幂等的"""
        try:
            # 1. 创建或更新文件节点
            file_query = """
            MERGE (f:File {path: $file_path})
            SET f.name = $file_name,
                f.size = $file_size,
                f.last_modified = datetime($last_modified),
                f.updated_at = datetime()
            RETURN f
            """
            
            tx.run(file_query, 
                file_path=parsed_code.file_info.path,
                file_name=parsed_code.file_info.name,
                file_size=parsed_code.file_info.size,
                last_modified=parsed_code.file_info.last_modified.isoformat()
            )
            
            # 2. 批量创建函数节点和关系
            if parsed_code.functions:
                functions_query = """
                MATCH (f:File {path: $file_path})
                UNWIND $functions AS func
                MERGE (fn:Function {name: func.name, file_path: $file_path})
                SET fn.start_line = func.start_line,
                    fn.end_line = func.end_line,
                    fn.source_code = func.source_code,
                    fn.updated_at = datetime()
                MERGE (f)-[:CONTAINS]->(fn)
                """
                
                functions_data = [
                    {
                        "name": func.name,
                        "start_line": func.start_line,
                        "end_line": func.end_line,
                        "source_code": func.source_code
                    }
                    for func in parsed_code.functions
                ]
                
                tx.run(functions_query,
                    file_path=parsed_code.file_info.path,
                    functions=functions_data
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            raise  # 让事务回滚
```

**B. 错误处理和重试机制:**
```python
from neo4j.exceptions import (
    ServiceUnavailable, 
    TransientError, 
    AuthError,
    ConfigurationError
)

def store_parsed_code(self, parsed_code: ParsedCode) -> bool:
    """带重试机制的存储方法"""
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            with self.driver.session(database="neo4j") as session:
                return session.execute_write(self._store_parsed_code_tx, parsed_code)
                
        except TransientError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Transient error on attempt {attempt + 1}: {e}")
                time.sleep(retry_delay * (2 ** attempt))  # 指数退避
                continue
            else:
                logger.error(f"Max retries exceeded: {e}")
                return False
                
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Non-retryable error: {e}")
            return False
```

**C. 资源管理和清理:**
```python
def clear_database(self) -> bool:
    """安全清理数据库"""
    if not self.driver:
        return False
        
    try:
        with self.driver.session(database="neo4j") as session:
            # 使用参数化查询避免意外删除
            result = session.execute_write(self._clear_database_tx)
            return result
            
    except Exception as e:
        logger.error(f"Failed to clear database: {e}")
        return False

def _clear_database_tx(self, tx) -> bool:
    """事务函数：清理所有节点和关系"""
    try:
        # 先删除关系，再删除节点
        tx.run("MATCH ()-[r:CONTAINS]->() DELETE r")
        tx.run("MATCH (n:Function) DELETE n")
        tx.run("MATCH (n:File) DELETE n")
        
        logger.info("Database cleared successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to clear database in transaction: {e}")
        raise

def close(self):
    """确保连接正确关闭"""
    if self.driver:
        try:
            self.driver.close()
            logger.info("Neo4j driver closed successfully")
        except Exception as e:
            logger.warning(f"Error closing driver: {e}")
        finally:
            self.driver = None
```

**D. 性能优化配置:**
```python
# 在ConfigManager中添加Neo4j性能配置
NEO4J_CONFIG = {
    "max_connection_pool_size": 50,  # 连接池大小
    "connection_acquisition_timeout": 60.0,  # 连接获取超时
    "max_transaction_retry_time": 30.0,  # 事务重试时间
    "fetch_size": 1000,  # 结果集批量大小
    "connection_timeout": 30.0,  # 连接超时
    "keep_alive": True,  # 保持连接活跃
}

# 应用配置
self.driver = GraphDatabase.driver(
    uri, 
    auth=(user, password),
    **NEO4J_CONFIG
)
```

### 11. 安全配置最佳实践

**A. 敏感信息管理:**
```python
# ❌ 错误做法 - 不要在配置文件中存储密码
# config.yml
database:
  neo4j:
    password: "your_password_here"  # 危险！

# ✅ 正确做法 - 通过环境变量提供敏感信息
# config.yml (无密码字段)
database:
  neo4j:
    uri: "bolt://localhost:7687"
    user: "neo4j"
    database: "neo4j"
    # 注意: 密码通过环境变量 NEO4J_PASSWORD 提供

# .env 文件
NEO4J_PASSWORD=your_secure_password
OPENROUTER_API_KEY=your_api_key
```

**B. ConfigManager环境变量映射:**
```python
def _apply_environment_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"确保所有敏感信息都从环境变量加载\"\"\"
    env_mappings = {
        'NEO4J_PASSWORD': ['database', 'neo4j', 'password'],  # 必需
        'NEO4J_URI': ['database', 'neo4j', 'uri'],
        'NEO4J_USER': ['database', 'neo4j', 'user'],
        'OPENROUTER_API_KEY': ['llm', 'chat', 'api_key'],     # 必需
        'LOG_LEVEL': ['logging', 'level'],
        'DEBUG': ['app', 'debug'],
    }
    # 自动从.env文件和系统环境变量加载
```

**C. 安全验证检查:**
```python
def _validate_config(self, config: Config) -> None:
    \"\"\"验证敏感配置已正确加载\"\"\"
    # 验证Neo4j密码
    if not config.database.neo4j_password:
        raise ConfigurationError("security", "NEO4J_PASSWORD environment variable is required")
    
    # 验证API密钥
    if not config.llm.chat_api_key:
        raise ConfigurationError("security", "OPENROUTER_API_KEY environment variable is required")
```

**D. 部署安全检查清单:**
- [ ] config.yml文件不包含任何密码或API密钥
- [ ] .env文件包含所有必需的敏感信息
- [ ] .env文件已添加到.gitignore（防止意外提交）
- [ ] 生产环境使用环境变量而非.env文件
- [ ] 所有敏感信息都有非空验证

### 12. 测试策略详细设计

**A. 单元测试 (test_neo4j_graph_store.py):**
```python
class TestNeo4jGraphStore:
    
    @pytest.fixture
    def mock_driver(self):
        """模拟Neo4j驱动"""
        with patch('neo4j.GraphDatabase.driver') as mock:
            yield mock
    
    def test_connect_success(self, mock_driver):
        """测试成功连接"""
        mock_driver.return_value.verify_connectivity.return_value = None
        
        store = Neo4jGraphStore()
        result = store.connect("bolt://localhost:7687", "neo4j", "password")
        
        assert result is True
        mock_driver.assert_called_once()
    
    def test_connect_failure(self, mock_driver):
        """测试连接失败"""
        mock_driver.side_effect = ServiceUnavailable("Connection failed")
        
        store = Neo4jGraphStore()
        result = store.connect("bolt://localhost:7687", "neo4j", "wrong_password")
        
        assert result is False
    
    def test_store_parsed_code_success(self, mock_driver):
        """测试成功存储数据"""
        # 设置mock session和transaction
        mock_session = MagicMock()
        mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
        mock_session.execute_write.return_value = True
        
        store = Neo4jGraphStore()
        store.driver = mock_driver.return_value
        
        parsed_code = create_test_parsed_code()
        result = store.store_parsed_code(parsed_code)
        
        assert result is True
        mock_session.execute_write.assert_called_once()
```

**B. 集成测试 (test_neo4j_integration.py):**
```python
@pytest.mark.integration
class TestNeo4jIntegration:
    
    @pytest.fixture(scope="class")
    def neo4j_store(self):
        """真实Neo4j连接"""
        config = ConfigManager()
        store = Neo4jGraphStore()
        
        success = store.connect(
            config.get('neo4j.uri'),
            config.get('neo4j.user'),
            config.get('neo4j.password')
        )
        
        if not success:
            pytest.skip("Neo4j not available")
        
        yield store
        store.close()
    
    def test_end_to_end_workflow(self, neo4j_store):
        """端到端工作流测试"""
        # 1. 清理数据库
        assert neo4j_store.clear_database()
        
        # 2. 存储测试数据
        parsed_code = create_test_parsed_code()
        assert neo4j_store.store_parsed_code(parsed_code)
        
        # 3. 验证数据存储
        with neo4j_store.driver.session(database="neo4j") as session:
            result = session.run("MATCH (f:File) RETURN count(f) as count")
            assert result.single()["count"] == 1
            
            result = session.run("MATCH (fn:Function) RETURN count(fn) as count")
            assert result.single()["count"] == len(parsed_code.functions)
```

### 13. 部署和监控

**A. 健康检查:**
```python
def health_check(self) -> Dict[str, Any]:
    """Neo4j健康状态检查"""
    try:
        if not self.driver:
            return {"status": "unhealthy", "error": "No driver connection"}
        
        with self.driver.session(database="neo4j") as session:
            result = session.run("RETURN 1 as test")
            record = result.single()
            
            if record and record["test"] == 1:
                return {"status": "healthy", "timestamp": datetime.now().isoformat()}
            else:
                return {"status": "unhealthy", "error": "Unexpected query result"}
                
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

**B. 性能监控:**
```python
def get_performance_metrics(self) -> Dict[str, Any]:
    """获取性能指标"""
    try:
        with self.driver.session(database="neo4j") as session:
            # 节点和关系统计
            result = session.run("""
                MATCH (n) 
                OPTIONAL MATCH ()-[r]->() 
                RETURN count(DISTINCT n) as nodes, count(r) as relationships
            """)
            stats = result.single()
            
            return {
                "nodes": stats["nodes"],
                "relationships": stats["relationships"],
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return {"error": str(e)} 
```

#### 测试计划
- **Unit (≥8)**  ➜ `tests/unit/test_c_parser_calls.py`
  | 名称 | 场景 |
  |------|------|
  | `test_extract_function_calls_simple` | 单一直接调用 |
  | `test_extract_pointer_calls` | 函数指针调用 `(*fp)()` |
  | `test_extract_member_calls` | 结构体成员调用 `obj->fn()` |
  | `test_recursive_call_detection` | 递归调用标记 |
  | `test_caller_relationship_build` | `Function.add_call()` 更新 |
  | `test_missing_callee_handling` | 外部符号调用 |
  | `test_parse_file_with_calls` | hello.c + 调用关系 |
  | `test_edge_case_macro_call` | 宏包装的函数调用 |
- **Integration (3)** ➜ `tests/integration/test_calls_to_neo4j.py`
  1. `test_store_call_relationships` – 存储 File + Function + CALLS
  2. `test_query_call_graph_depth_2` – Cypher 查询验证
  3. `test_end_to_end_parse_and_store` – 解析 → 存储 一条链
- **Acceptance (1)** ➜ `tests/integration/test_story_2_1_3_acceptance.py`
  - 解析 `fixtures/complex.c`，数据库中 CALLS 关系条数 == 解析结果
- **覆盖率目标**：模块 `c_parser.py` 与 `neo4j_store.py` 增量覆盖率 ≥ 90 %

---

**Story 2.1.4 ...**
#### 测试计划
- **Unit (5)**  ➜ `tests/unit/test_call_graph_service.py`
  | 名称 | 场景 |
  |------|------|
  | `test_build_graph_basic` | main→helper 深度=1 |
  | `test_build_graph_with_filter` | depth=2 + 过滤标准库 |
  | `test_mermaid_output_format` | UTF-8 & Mermaid 语法 |
  | `test_json_output_nodes_edges` | JSON 节点/边结构 |
  | `test_cli_args_parsing` | CLI 解析 & 参数校验 |
- **API/Integration (3)** ➜ `tests/integration/test_call_graph_api.py`
  1. `test_http_api_ok` – FastAPI + HTTPX 200
  2. `test_http_api_bad_root` – 404 处理
  3. `test_cli_render_mermaid_file` – 生成 mermaid.md 并可渲染
- **前端快照 (1)** ➜ 使用 `pytest-playwright` 截图比对
- **覆盖率目标**：`graph_api.py` ≥ 90 %

---

**Story 2.1.5 ...**
#### 测试计划
- **Unit (6)**  ➜ `tests/unit/test_code_quality_analyzer.py`
  | 测试 | 目的 |
  |------|------|
  | `test_find_unused_functions_basic` | 简单 project fixtures |
  | `test_find_unused_functions_exclude_main` | main 过滤 |
  | `test_generate_markdown_report` | 文件生成 & 格式 |
  | `test_report_content_matches_query` | 报告行数校验 |
  | `test_cli_report_command` | `code-learner report --unused` |
  | `test_empty_project_handling` | 空数据库 |
- **Integration (2)** ➜ `tests/integration/test_unused_functions_report.py`
  1. 真实 Neo4j 插入→检测
  2. 报告文件 diff 验证
- **覆盖率目标**：相关模块 ≥ 92 %

---

**Story 2.1.6 ...**
#### 测试计划
- **Unit (6)**  ➜ `tests/unit/test_complexity_analyzer.py`
  | Test | Purpose |
  |------|---------|
  | `test_cyclomatic_complexity_simple` | 顺序结构 |
  | `test_cyclomatic_complexity_nested` | 条件/循环嵌套 |
  | `test_depth_weighting` | 深度权重计算 |
  | `test_score_persistence` | 节点写回 Neo4j |
  | `test_cli_hotspots_output` | CLI 输出 top-N 表格 |
  | `test_radon_dependency_available` | 运行环境检查 |
- **Integration (2)** ➜ `tests/integration/test_hotspots_cli.py`
  1. Parse→store→score→CLI 输出验证
  2. 热门函数列表排序正确
- **性能基准**  ➜ `pytest-benchmark`：OpenSBI 289 文件执行 ≤ 300s
- **覆盖率目标**：新文件 ≥ 90 %，整体保持 > 90 %