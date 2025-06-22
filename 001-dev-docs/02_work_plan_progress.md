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
**状态:** Todo  
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
- 环境依赖测试：5/5通过
- ConfigManager单元测试：4/4通过
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
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    max_tokens: int = 1000

class ConfigManager:
    def load_config(self, config_path: Optional[Path] = None) -> Config
    def _validate_config(self, config: Config) -> bool
    def _load_environment_vars(self) -> Dict[str, str]
```

---

### Story 1.2: Tree-sitter C语言解析器实现 ⭐
**状态:** Todo  
**估时:** 1天  
**优先级:** 高

**功能描述:**
实现完整的CParser类，集成Tree-sitter-c解析器，提供C文件解析和AST特征提取功能。

**详细任务清单:**
1. **CParser类实现**
   - 实现IParser接口
   - Tree-sitter解析器初始化和配置
   - 文件读取和编码处理

2. **AST特征提取**
   - 递归函数定义提取
   - 函数调用关系分析
   - Include文件识别
   - 参数和返回类型解析

3. **错误处理和验证**
   - 文件不存在处理
   - 语法错误恢复
   - 编码问题处理
   - 解析结果验证

**核心类设计:**
```python
class CParser(IParser):
    def __init__(self):
        self.config = ConfigManager().load_config()
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)
    
    def parse_file(self, file_path: str) -> ParsedCode:
        """解析C文件，返回完整的解析结果"""
    
    def extract_functions(self, content: str) -> List[Dict[str, Any]]:
        """从代码内容提取函数信息"""
        
    def _extract_functions(self, node: Node, source: str) -> List[Function]:
        """递归提取函数定义"""
        
    def _parse_function_definition(self, node: Node, source: str) -> Optional[Function]:
        """解析单个函数定义节点"""
        
    def _extract_function_calls(self, node: Node, source: str) -> List[str]:
        """提取函数内的调用关系"""
        
    def _extract_parameters(self, node: Node, source: str) -> List[str]:
        """提取函数参数"""
        
    def _extract_return_type(self, node: Node, source: str) -> str:
        """提取返回类型"""
```

**验收标准:**
1. ✅ CParser类完整实现IParser接口
2. ✅ 正确解析函数定义和调用关系
3. ✅ 处理复杂C语法结构
4. ✅ 完善的错误处理机制

**TDD测试计划:**
```python
# tests/unit/test_c_parser.py
class TestCParser:
    def test_parse_simple_file(self, sample_c_file):
        """测试解析简单C文件"""
        result = self.parser.parse_file(sample_c_file)
        assert result.parse_success is True
        assert len(result.functions) == 2
        
    def test_extract_function_calls(self, sample_c_file):
        """测试函数调用关系提取"""
        result = self.parser.parse_file(sample_c_file)
        main_func = next(f for f in result.functions if f.name == 'main')
        assert 'hello' in main_func.calls
        
    def test_parse_complex_functions(self):
        """测试复杂函数解析"""
        code = '''
        int calculate(int a, int b) {
            helper_function(a);
            return a + b;
        }
        
        void helper_function(int x) {
            printf("%d", x);
        }
        '''
        functions = self.parser.extract_functions(code)
        assert len(functions) == 2
        calc_func = next(f for f in functions if f.name == 'calculate')
        assert 'helper_function' in calc_func.calls
        assert calc_func.return_type == 'int'
        assert 'a' in calc_func.parameters
        
    def test_error_handling(self):
        """测试错误处理"""
        result = self.parser.parse_file('nonexistent.c')
        assert result.parse_success is False
        assert result.error_message is not None
        
    @pytest.mark.parametrize("code,expected_count", [
        ("int main() { return 0; }", 1),
        ("void func1() {} void func2() {}", 2),
        ("", 0),
        ("int func(int a, char* b) { other_func(); }", 1)
    ])
    def test_function_extraction_varieties(self, code, expected_count):
        """参数化测试各种函数类型"""
        functions = self.parser.extract_functions(code)
        assert len(functions) == expected_count
```

**通过标准 (100%测试通过):**
- 基础解析测试：5/5通过
- 函数提取测试：8/8通过
- 调用关系测试：6/6通过
- 错误处理测试：4/4通过
- 参数化测试：12/12通过

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

**解析结果数据模型:**
```python
@dataclass
class Function:
    name: str                    # 函数名
    file_path: str              # 所属文件
    start_line: int             # 开始行号
    end_line: int               # 结束行号
    parameters: List[str]       # 参数列表
    return_type: str            # 返回类型
    calls: List[str]            # 调用的函数列表
    source_code: str            # 函数源代码

@dataclass
class ParsedCode:
    file_path: str              # 文件路径
    file_name: str              # 文件名
    content: str                # 文件内容
    functions: List[Function]   # 函数列表
    includes: List[str]         # 包含的头文件
    parse_success: bool         # 解析是否成功
    error_message: Optional[str] = None  # 错误信息
```

---

### Story 1.3: 图数据库存储 ⭐
**状态:** Todo  
**估时:** 1天  
**优先级:** 高

**功能描述:**
集成Neo4j，实现代码结构的图存储功能。

**验收标准:**
1. ✅ Neo4j连接和基本操作
2. ✅ 存储File和Function节点
3. ✅ 创建CONTAINS和CALLS关系

**测试场景:**
- **节点创建:** 成功创建文件和函数节点
- **关系建立:** 正确建立包含和调用关系
- **基本查询:** 能查询函数列表和调用关系

**通过标准:**
- Neo4j中能查看到正确的节点和关系
- 基本Cypher查询返回正确结果

**简化的Neo4j模型:**
```cypher
// 节点
(f:File {path, name})
(fn:Function {name, file})

// 关系  
(f)-[:CONTAINS]->(fn)
(fn1)-[:CALLS]->(fn2)
```

---

### Story 1.4: 向量嵌入与问答 ⭐
**状态:** Todo  
**估时:** 1天  
**优先级:** 高

**功能描述:**
集成Chroma向量数据库和OpenRouter API，实现代码嵌入和基本问答。

**验收标准:**
1. ✅ 生成文件内容向量嵌入
2. ✅ 存储到Chroma向量数据库
3. ✅ OpenRouter API调用成功
4. ✅ 回答基本问题

**测试场景:**
- **向量生成:** 成功为C文件生成嵌入向量
- **向量存储:** Chroma中能查询到向量
- **基本问答:** 能回答"这个文件有哪些函数？"

**通过标准:**
- 向量嵌入生成无错误
- 能回答预定义的基本问题
- 问答结果与实际代码内容一致

**目标问答示例 (基于OpenSBI项目):**
```
Q: "OpenSBI项目的主要模块有哪些？"
A: "OpenSBI项目包含以下主要模块：lib(核心库)、platform(平台适配)、firmware(固件)、include(头文件)等"

Q: "sbi_init函数在哪里定义？它调用了哪些其他函数？"  
A: "sbi_init函数定义在lib/sbi/sbi_init.c文件中，它调用了sbi_platform_init、sbi_console_init等初始化函数"

Q: "这个项目总共有多少个C文件和函数？"
A: "OpenSBI项目包含172个C文件、117个头文件，总计约XXX个函数定义"
```

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
- [ ] Story 1.2: Tree-sitter解析集成 ⭐
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