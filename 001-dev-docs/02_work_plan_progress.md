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

### Story 1.4: 向量嵌入与问答 ⭐ (重新设计)
**状态:** Todo  
**估时:** 1天  
**优先级:** 高

**功能描述:**
集成Chroma向量数据库和OpenRouter API，实现代码嵌入和基本问答，支持repo级别扩展。

**🎯 设计原则重新平衡 (KISS + 可扩展性):**

#### 恢复完整接口设计 (支持repo级别扩展)
```python
# 保持接口分离，支持未来repo级别处理
class IVectorStore(ABC):
    """向量数据库存储接口 - 支持repo级别扩展"""
    
    @abstractmethod
    def create_collection(self, name: str) -> bool:
        """创建向量集合 - repo级别需要多集合管理"""
        
    @abstractmethod
    def add_embeddings(self, embeddings: List[EmbeddingData]) -> bool:
        """批量添加向量嵌入 - repo级别需要批量处理"""
        
    @abstractmethod
    def search_similar(self, query_vector: EmbeddingVector, top_k: int = 5) -> List[Dict[str, Any]]:
        """语义搜索 - 核心功能"""
        
    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """删除集合 - repo级别需要清理功能"""

class IEmbeddingEngine(ABC):
    """嵌入生成引擎接口 - 支持repo级别批量处理"""
    
    @abstractmethod
    def load_model(self, model_name: str) -> bool:
        """加载嵌入模型"""
        
    @abstractmethod
    def encode_text(self, text: str) -> EmbeddingVector:
        """单个文本编码"""
        
    @abstractmethod
    def encode_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """批量编码 - repo级别必需(289文件)"""
        
    @abstractmethod
    def encode_function(self, function: Function) -> EmbeddingData:
        """函数专用编码"""

class IChatBot(ABC):
    """聊天机器人接口 - 支持多种问答模式"""
    
    @abstractmethod
    def initialize(self, api_key: str, model: str) -> bool:
        """初始化OpenRouter API"""
        
    @abstractmethod
    def ask_question(self, question: str, context: List[str]) -> QueryResult:
        """基于上下文问答"""
        
    @abstractmethod
    def generate_summary(self, code: str) -> str:
        """生成代码摘要 - 用户明确需要的功能"""
```

#### 完整功能集 (用户需求 + repo级别支持)
**核心功能:**
- ✅ 代码向量化 (jina-embeddings-v2-base-code)
- ✅ 批量处理支持 (repo级别289文件)
- ✅ 向量存储 (Chroma持久化存储)
- ✅ 语义搜索和相似性分析
- ✅ 基本问答 (OpenRouter API)
- ✅ **代码摘要生成** (用户明确需求)

**repo级别扩展支持:**
- ✅ 多集合管理 (按模块/目录分组)
- ✅ 批量向量化 (encode_batch)
- ✅ 增量更新支持
- ✅ 大规模语义搜索

#### 真实测试策略 (无mock，无fallback)
**测试复杂度:**
- **真实API测试:** 所有接口使用真实服务
- **真实数据测试:** 使用OpenSBI项目真实代码
- **端到端测试:** 完整的repo处理流程
- **性能测试:** 验证289文件处理能力

```python
class TestStory14Acceptance:
    """Story 1.4验收测试 - 全部真实API"""
    
    def test_embedding_engine_real_model(self):
        """真实jina-embeddings模型测试"""
        engine = EmbeddingEngine()
        assert engine.load_model("jinaai/jina-embeddings-v2-base-code")
        
        # 测试单个编码
        vector = engine.encode_text("int main() { return 0; }")
        assert len(vector) == 768  # jina-embeddings维度
        
        # 测试批量编码 (repo级别需求)
        texts = ["int main()", "void setup()", "char* get_name()"]
        vectors = engine.encode_batch(texts)
        assert len(vectors) == 3
    
    def test_vector_store_real_chroma(self):
        """真实Chroma数据库测试"""
        store = ChromaVectorStore()
        assert store.create_collection("opensbi_test")
        
        # 批量存储测试
        embeddings = [create_test_embedding(i) for i in range(100)]
        assert store.add_embeddings(embeddings)
        
        # 语义搜索测试
        query_vector = create_query_vector()
        results = store.search_similar(query_vector, top_k=5)
        assert len(results) == 5
    
    def test_chatbot_real_openrouter(self):
        """真实OpenRouter API测试"""
        chatbot = OpenRouterChatBot()
        config = ConfigManager().get_config()
        assert chatbot.initialize(config.llm.chat_api_key, config.llm.chat_model)
        
        # 基本问答测试
        context = ["int main() { printf(\"Hello\"); return 0; }"]
        result = chatbot.ask_question("这个函数做什么？", context)
        assert isinstance(result, QueryResult)
        assert "printf" in result.answer.lower()
        
        # 代码摘要测试 (用户需求)
        code = load_opensbi_function("sbi_init")
        summary = chatbot.generate_summary(code)
        assert len(summary) > 50
        assert "初始化" in summary or "init" in summary.lower()
    
    def test_repo_level_processing(self):
        """repo级别处理测试 - OpenSBI项目"""
        # 解析OpenSBI项目
        parser = CParser()
        opensbi_files = glob.glob("reference_code_repo/opensbi/**/*.c", recursive=True)
        assert len(opensbi_files) >= 100  # 验证项目规模
        
        # 批量处理测试
        all_parsed = []
        for file_path in opensbi_files[:10]:  # 测试前10个文件
            parsed = parser.parse_file(file_path)
            all_parsed.append(parsed)
        
        # 批量向量化
        engine = EmbeddingEngine()
        all_functions = []
        for parsed in all_parsed:
            all_functions.extend(parsed.functions)
        
        embeddings = []
        for func in all_functions:
            embedding = engine.encode_function(func)
            embeddings.append(embedding)
        
        # 批量存储
        store = ChromaVectorStore()
        assert store.add_embeddings(embeddings)
        
        # repo级别问答测试
        chatbot = OpenRouterChatBot()
        answer = chatbot.ask_question(
            "OpenSBI项目的主要初始化函数有哪些？",
            [f.code for f in all_functions if "init" in f.name.lower()]
        )
        assert "sbi_init" in answer.answer.lower()
```

#### 实现架构 (平衡简单和扩展性)
```python
# 具体实现类
class JinaEmbeddingEngine(IEmbeddingEngine):
    """jina-embeddings-v2-base-code实现"""
    
    def __init__(self):
        self.model = None
        
    def load_model(self, model_name: str) -> bool:
        from sentence_transformers import SentenceTransformer
        try:
            self.model = SentenceTransformer(model_name)
            return True
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            return False
    
    def encode_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """批量编码 - repo级别优化"""
        if not self.model:
            raise ModelLoadError("模型未加载")
        
        # 使用sentence-transformers的批量编码优化
        embeddings = self.model.encode(texts, batch_size=32, show_progress_bar=True)
        return [embedding.tolist() for embedding in embeddings]

class ChromaVectorStore(IVectorStore):
    """Chroma向量数据库实现 - 持久化存储"""
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        import chromadb
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collections = {}
    
    def create_collection(self, name: str) -> bool:
        try:
            collection = self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            self.collections[name] = collection
            return True
        except Exception as e:
            logger.error(f"集合创建失败: {e}")
            return False

class OpenRouterChatBot(IChatBot):
    """OpenRouter API实现"""
    
    def generate_summary(self, code: str) -> str:
        """生成代码摘要 - 用户需求"""
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你是一个C语言代码分析专家。请为给定的代码生成简洁的中文摘要。"},
                        {"role": "user", "content": f"请为以下C代码生成摘要:\n\n{code}"}
                    ],
                    "max_tokens": 200,
                    "temperature": 0.3
                }
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                raise APIError(f"API调用失败: {response.status_code}")
                
        except Exception as e:
            logger.error(f"代码摘要生成失败: {e}")
            raise
```

**验收标准 (repo级别):**
1. ✅ 成功为OpenSBI项目(>=100个文件)生成向量嵌入
2. ✅ 向量存储到Chroma持久化数据库
3. ✅ OpenRouter API调用成功(问答+摘要)
4. ✅ 回答关于OpenSBI项目的复杂问题
5. ✅ 为主要函数生成准确的代码摘要

**目标问答示例 (repo级别):**
```
Q: "OpenSBI项目的主要模块有哪些？"
A: "OpenSBI项目包含以下主要模块：lib(核心库)、platform(平台适配)、firmware(固件)、include(头文件)等"

Q: "sbi_init函数在哪里定义？它的作用是什么？"  
A: "sbi_init函数定义在lib/sbi/sbi_init.c文件中。它是OpenSBI的主要初始化函数，负责初始化SBI运行时环境。"

Q: "请总结sbi_platform_init函数的功能"
A: [通过generate_summary生成] "sbi_platform_init函数负责初始化特定平台的硬件抽象层，包括设置平台相关的回调函数和硬件配置。"
```

**实施优先级 (repo级别支持):**
1. **第一步:** 实现三个核心接口类
2. **第二步:** 集成真实的jina-embeddings (支持批量)
3. **第三步:** 集成Chroma持久化存储
4. **第四步:** 集成OpenRouter API (问答+摘要)
5. **第五步:** repo级别端到端测试 (OpenSBI项目)

**成功标准 (提高要求):**
- ✅ 能处理OpenSBI项目100+文件
- ✅ 批量向量化性能 < 10分钟
- ✅ 语义搜索准确率 >= 80%
- ✅ 问答准确率 >= 75%
- ✅ 代码摘要质量人工评估 >= 良好

---

## Epic 2: POC整合与演示 (2个Story) 🚀

### Story 2.1: 端到端流程整合
**功能描述:** 将所有组件整合为完整的演示流程

### Story 2.2: CLI演示命令
**功能描述:** 实现简单的demo命令，展示完整功能

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
- [ ] Story 1.3: 图数据库存储 ⭐
- [ ] Story 1.4: 向量嵌入与问答 ⭐

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