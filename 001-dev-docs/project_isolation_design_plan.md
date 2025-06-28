# 项目隔离机制设计文档

## 1. 当前状态分析

### 1.1 现有机制

当前系统在处理不同代码仓库时存在以下隔离机制：

#### Neo4j图数据库
- **隔离状态**: ❌ 无隔离
- **存储内容**: 代码结构信息（函数、文件、调用关系等）
- **当前行为**: 所有项目的数据存储在同一个Neo4j数据库中，没有项目级别的隔离
- **潜在问题**: 
  - 不同项目的函数可能存在名称冲突
  - 无法区分来自不同项目的代码结构
  - 项目之间的数据混合可能导致错误的关系分析

#### Chroma向量数据库
- **隔离状态**: ✅ 部分隔离（通过集合名称）
- **存储内容**: 代码块的向量嵌入
- **当前行为**: 可以通过不同的集合名称实现项目隔离，但需要手动指定
- **潜在问题**:
  - 集合名称需要手动管理，没有自动化机制
  - 没有统一的项目标识符贯穿整个系统

### 1.2 问题总结

1. **缺乏统一的项目标识符**：没有一个贯穿Neo4j和Chroma的统一项目标识
2. **Neo4j无项目隔离**：Neo4j中的数据没有按项目隔离
3. **手动管理集合名称**：Chroma集合名称需要手动指定，容易出错
4. **命令行工具缺乏项目参数**：部分命令行工具没有项目参数

## 2. 设计目标

1. 实现不同代码仓库的完全隔离
2. 提供统一的项目标识符系统
3. 简化用户操作，减少手动配置
4. 保持向后兼容性，不破坏现有功能
5. 支持跨项目查询（可选高级功能）

## 3. 解决方案

### 3.1 项目标识符系统

设计一个统一的项目标识符系统：

1. **项目ID生成**：
   - 基于代码仓库路径的哈希值生成唯一项目ID
   - 支持用户自定义项目名称（可选）

2. **项目元数据存储**：
   - 创建项目元数据表/集合，存储项目信息
   - 包括项目ID、名称、路径、创建时间等

### 3.2 Neo4j隔离机制

在Neo4j中实现项目隔离：

1. **节点标记**：
   - 为所有节点添加`project_id`属性
   - 查询时使用`project_id`过滤结果

2. **关系标记**：
   - 为所有关系添加`project_id`属性
   - 确保跨项目关系正确标记

3. **查询修改**：
   - 修改所有查询，添加项目ID过滤条件
   - 优化查询性能，添加适当索引

### 3.3 Chroma隔离机制

完善Chroma的项目隔离：

1. **集合命名规范**：
   - 使用`{project_id}_{collection_type}`格式命名集合
   - 例如：`p123456_code_chunks`

2. **自动集合管理**：
   - 根据项目ID自动创建和管理集合
   - 提供集合列表和清理功能

### 3.4 命令行接口增强

增强命令行工具支持项目隔离：

1. **项目参数**：
   - 为所有命令添加`--project-id`和`--project-name`参数
   - 支持从配置文件读取默认项目

2. **项目管理命令**：
   - 添加`project list`命令列出所有项目
   - 添加`project create`命令创建新项目
   - 添加`project delete`命令删除项目

## 4. 技术实现方案

### 4.1 项目管理模块

创建新的项目管理模块：

```python
# src/code_learner/project/project_manager.py
class ProjectManager:
    def __init__(self, config):
        self.config = config
        
    def create_project(self, repo_path, name=None):
        """创建新项目或获取现有项目"""
        project_id = self._generate_project_id(repo_path)
        if not name:
            name = os.path.basename(os.path.abspath(repo_path))
        
        # 存储项目元数据
        self._store_project_metadata(project_id, name, repo_path)
        return project_id
        
    def get_project(self, project_id=None, repo_path=None):
        """获取项目信息"""
        pass
        
    def list_projects(self):
        """列出所有项目"""
        pass
        
    def delete_project(self, project_id):
        """删除项目及其所有数据"""
        pass
        
    def _generate_project_id(self, repo_path):
        """根据仓库路径生成唯一项目ID"""
        abs_path = os.path.abspath(repo_path)
        return "p" + hashlib.md5(abs_path.encode()).hexdigest()[:10]
        
    def _store_project_metadata(self, project_id, name, repo_path):
        """存储项目元数据"""
        pass
```

### 4.2 Neo4j存储修改

修改Neo4j存储类以支持项目隔离：

```python
# src/code_learner/storage/neo4j_store.py
class Neo4jGraphStore:
    def __init__(self, uri, user, password, project_id=None):
        self.uri = uri
        self.user = user
        self.password = password
        self.project_id = project_id
        
    def create_file_node(self, file_path, language):
        # 添加项目ID到节点属性
        query = """
        CREATE (f:File {path: $path, language: $language, project_id: $project_id})
        RETURN f
        """
        return self._run_query(query, {"path": file_path, "language": language, "project_id": self.project_id})
        
    # 修改其他方法，添加project_id参数
    
    def _run_query(self, query, params=None):
        if params is None:
            params = {}
        
        # 确保所有查询都包含项目ID
        if self.project_id and "project_id" not in params:
            params["project_id"] = self.project_id
            
        # 执行查询
        with self._driver.session() as session:
            return session.run(query, params)
```

### 4.3 Chroma存储修改

修改Chroma存储类以支持项目隔离：

```python
# src/code_learner/llm/vector_store.py
class ChromaVectorStore:
    def __init__(self, persist_directory="./data/chroma", project_id=None):
        self.persist_directory = persist_directory
        self.project_id = project_id
        self.client = chromadb.PersistentClient(path=persist_directory)
        
    def get_collection_name(self, base_name="code_chunks"):
        """根据项目ID生成集合名称"""
        if self.project_id:
            return f"{self.project_id}_{base_name}"
        return base_name
        
    def add_embeddings(self, texts, embeddings, metadatas=None, collection_name=None):
        """添加嵌入到指定集合"""
        if collection_name is None:
            collection_name = self.get_collection_name()
            
        # 创建或获取集合
        collection = self.client.get_or_create_collection(name=collection_name)
        
        # 添加嵌入
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=[str(uuid.uuid4()) for _ in range(len(texts))]
        )
        
    # 修改其他方法，使用项目特定的集合名称
```

### 4.4 命令行接口修改

修改命令行接口以支持项目参数：

```python
# src/code_learner/cli/code_analyzer_cli.py
@click.option("--project-id", help="项目ID，如果不指定则根据仓库路径生成")
@click.option("--project-name", help="项目名称，如果不指定则使用仓库名称")
def analyze(repo_path, output_dir, project_id, project_name):
    """分析代码仓库"""
    # 初始化项目管理器
    project_manager = ProjectManager(config)
    
    # 获取或创建项目
    if not project_id:
        project_id = project_manager.create_project(repo_path, project_name)
    
    # 初始化存储，传入项目ID
    graph_store = Neo4jGraphStore(uri, user, password, project_id)
    vector_store = ChromaVectorStore(persist_directory, project_id)
    
    # 执行分析
    analyzer = CodeAnalyzer(graph_store)
    analyzer.analyze_repo(repo_path)
```

### 4.5 项目管理命令

添加项目管理命令：

```python
# src/code_learner/cli/project_cli.py
@click.group()
def project():
    """项目管理命令"""
    pass

@project.command()
@click.argument("repo_path")
@click.option("--name", help="项目名称")
def create(repo_path, name):
    """创建新项目"""
    project_manager = ProjectManager(config)
    project_id = project_manager.create_project(repo_path, name)
    click.echo(f"项目已创建，ID: {project_id}")

@project.command()
def list():
    """列出所有项目"""
    project_manager = ProjectManager(config)
    projects = project_manager.list_projects()
    # 显示项目列表
    
@project.command()
@click.argument("project_id")
def delete(project_id):
    """删除项目"""
    project_manager = ProjectManager(config)
    project_manager.delete_project(project_id)
    click.echo(f"项目 {project_id} 已删除")
```

## 5. 实现计划

### 5.1 工作项划分

1. **核心项目管理模块**
   - 创建项目管理器类
   - 实现项目ID生成和元数据存储
   - 单元测试

2. **Neo4j隔离实现**
   - 修改Neo4j存储类
   - 更新所有查询添加项目ID
   - 添加项目ID索引
   - 单元测试

3. **Chroma隔离实现**
   - 修改Chroma存储类
   - 实现基于项目ID的集合命名
   - 单元测试

4. **命令行接口增强**
   - 为现有命令添加项目参数
   - 创建项目管理命令
   - 集成测试

5. **文档和示例更新**
   - 更新README
   - 添加项目管理文档
   - 更新架构文档

### 5.2 优先级和时间估计

| 工作项 | 优先级 | 时间估计 | 依赖项 |
|-------|-------|---------|-------|
| 核心项目管理模块 | 高 | 1天 | 无 |
| Neo4j隔离实现 | 高 | 2天 | 核心项目管理模块 |
| Chroma隔离实现 | 高 | 1天 | 核心项目管理模块 |
| 命令行接口增强 | 中 | 1天 | 所有存储实现 |
| 文档和示例更新 | 低 | 0.5天 | 所有实现 |

### 5.3 向后兼容性

为确保向后兼容性，我们将：

1. 默认项目ID为空时保持现有行为
2. 在不指定项目参数时使用默认集合名称
3. 提供迁移工具将现有数据标记为默认项目

## 6. 测试计划

### 6.1 单元测试

1. **项目管理器测试**
   - 测试项目ID生成
   - 测试项目创建和获取
   - 测试项目列表和删除

2. **Neo4j存储测试**
   - 测试带项目ID的节点创建
   - 测试项目隔离查询
   - 测试跨项目查询

3. **Chroma存储测试**
   - 测试项目特定集合名称
   - 测试嵌入添加和查询
   - 测试集合管理

### 6.2 集成测试

1. **端到端工作流测试**
   - 测试完整分析流程
   - 测试多项目并行处理
   - 测试项目删除和清理

2. **性能测试**
   - 测试大型项目处理性能
   - 测试多项目环境下的查询性能

## 7. 风险和缓解措施

| 风险 | 影响 | 缓解措施 |
|-----|-----|---------|
| 数据迁移复杂 | 中 | 提供迁移工具和详细文档 |
| 性能下降 | 低 | 添加适当索引，优化查询 |
| 向后兼容性问题 | 高 | 保留默认行为，全面测试 |
| 存储空间增加 | 低 | 实现数据清理和压缩功能 |

## 8. 结论和建议

实现项目隔离机制对于支持多项目分析至关重要。通过统一的项目ID系统和存储隔离，我们可以确保不同代码仓库的数据不会相互干扰，同时保持系统的灵活性和可扩展性。

建议按照以下步骤实施：

1. 首先实现核心项目管理模块
2. 然后实现存储隔离机制
3. 最后更新命令行接口和文档

这种渐进式实施方法可以最小化对现有功能的影响，同时逐步引入新功能。

# 实施计划（Epic/Story）

## Epic 1: 项目管理基础设施

**目标**: 创建统一的项目管理系统，支持多项目隔离

### Story 1.1: 项目管理器实现
- 创建ProjectManager类
- 实现项目ID生成算法
- 实现项目元数据存储和检索
- 编写单元测试

### Story 1.2: 项目配置管理
- 创建项目配置文件结构
- 实现配置读取和写入
- 支持默认项目设置
- 编写单元测试

## Epic 2: 存储系统项目隔离

**目标**: 在Neo4j和Chroma存储中实现项目隔离

### Story 2.1: Neo4j项目隔离
- 修改Neo4jGraphStore添加项目ID支持
- 更新所有查询方法
- 添加项目ID索引
- 编写单元测试

### Story 2.2: Chroma项目隔离
- 修改ChromaVectorStore添加项目ID支持
- 实现基于项目的集合命名
- 实现集合管理功能
- 编写单元测试

### Story 2.3: 数据迁移工具
- 创建现有数据迁移工具
- 支持将未标记数据分配给默认项目
- 编写迁移指南
- 测试迁移过程

## Epic 3: 命令行接口增强

**目标**: 更新命令行工具支持项目管理

### Story 3.1: 项目参数支持
- 为analyze命令添加项目参数
- 为embed_code命令添加项目参数
- 为其他命令添加项目参数
- 编写集成测试

### Story 3.2: 项目管理命令
- 创建project命令组
- 实现项目创建、列表和删除命令
- 实现项目信息显示命令
- 编写用户指南

## Epic 4: 文档和示例更新

**目标**: 更新文档和示例以反映项目隔离功能

### Story 4.1: 架构文档更新
- 更新架构图
- 添加项目隔离说明
- 更新数据流描述
- 审查和校对

### Story 4.2: 用户指南更新
- 创建项目管理指南
- 更新命令行参考
- 添加多项目工作流示例
- 审查和校对

### Story 4.3: 示例和演示
- 创建多项目演示
- 更新示例代码
- 创建教程视频（可选）
- 测试所有示例 