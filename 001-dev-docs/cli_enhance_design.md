# 统一命令行增强设计方案 (CLI Enhancement Design)

## 1. 核心目标

将当前散落的多个CLI脚本 (`code_analyzer_cli.py`, `call_graph_cli.py`, `dependency_cli.py` 等) 统一到一个名为 `code-learner` 的单一命令入口下。同时，引入完整的项目管理生命周期（创建、列表、删除），并增强查询命令的交互性。

## 2. 统一命令结构

所有功能将通过 `code-learner` 的子命令形式提供。

```
code-learner
├── project           # (新) 项目管理
│   ├── create        # 创建一个新项目
│   ├── list          # 列出所有项目
│   └── delete        # 删除一个项目
├── analyze           # 分析一个已创建的项目
├── query             # 对项目进行问答 (支持交互式和直接查询)
├── call-graph        # (迁移) 查询指定函数的调用图
├── dep-graph         # (迁移) 查询项目的依赖图
└── status            # (迁移) 检查系统状态
```

## 3. 项目管理生命周期 (Project Lifecycle)

这是本次设计的核心。我们将从"隐式"项目（基于路径哈希）转变为"显式"项目管理。

### 3.1. 项目注册表

-   系统将在用户主目录下的一个隐藏文件中维护一个项目注册表，例如 `~/.code_learner/projects.json`。
-   此文件将存储项目短名称、唯一的项目ID和项目在磁盘上的绝对路径的映射关系。
    ```json
    {
      "projects": [
        {
          "name": "opensbi_main",
          "id": "auto_a1b2c3d4",
          "path": "/home/user/repos/opensbi"
        },
        {
          "name": "linux_kernel_dev",
          "id": "auto_e5f6g7h8",
          "path": "/home/user/repos/linux"
        }
      ]
    }
    ```

### 3.2. `project create` 命令

-   **用途**: 显式创建一个新项目，为其分配一个唯一的ID和用户指定的短名称。
-   **命令**: `code-learner project create <path_to_project> --name <short_name>`
-   **执行流程**:
    1.  验证 `<path_to_project>` 是否存在。
    2.  验证 `<short_name>` 是否已在注册表中使用。
    3.  基于路径生成一个唯一的 `project_id` (继续使用路径哈希，保证唯一性)。
    4.  将 `{ "name": short_name, "id": project_id, "path": path }` 写入项目注册表。
    5.  返回成功信息，显示项目名称和ID。

### 3.3. `project list` 命令

-   **用途**: 列出所有已创建的项目。
-   **命令**: `code-learner project list`
-   **执行流程**:
    1.  读取项目注册表 `~/.code_learner/projects.json`。
    2.  以表格形式打印出所有项目的短名称、ID和路径。

### 3.4. `project delete` 命令

-   **用途**: 彻底删除一个项目及其所有相关数据。这是一个危险操作，需要用户确认。
-   **命令**: `code-learner project delete <name_or_id>`
-   **执行流程**:
    1.  根据用户提供的名称或ID，从注册表查找项目信息。
    2.  向用户显示将要删除的项目信息，并要求输入项目名称进行二次确认。
    3.  **Neo4j清理**: 使用项目的 `project_id` 删除所有相关的节点和关系 (`MATCH (n {project_id: '...'}) DETACH DELETE n`)。
    4.  **ChromaDB清理**: 使用项目的 `project_id` 删除对应的集合 (`collection_name = f"{project_id}_code_embeddings"`)。
    5.  **本地文件清理**: 删除分析产物目录 (例如 `data/<project_name>_analysis`)。
    6.  从项目注册表 `~/.code_learner/projects.json` 中移除该项目条目。

## 4. 核心工作流重构

### 4.1. `analyze` 命令

-   **命令**: `code-learner analyze --project <name_or_id>`
-   **流程**:
    1.  根据 `<name_or_id>` 从项目注册表查找项目的 `project_id` 和 `path`。
    2.  使用获取到的 `project_id` 和 `path` 执行完整的分析流程（代码解析、数据库存储、向量嵌入等）。

### 4.2. `query` 命令

-   **命令**:
    -   交互式: `code-learner query --project <name_or_id>`
    -   直接查询: `code-learner query --project <name_or_id> --query "your question"`
-   **流程**:
    1.  根据 `--project` 参数查找 `project_id`。
    2.  使用 `project_id` 初始化 `CodeQAService`，确保查询范围限定在本项目。
    3.  检查是否提供了 `--query` 参数：
        -   **如果提供了**：执行单次查询，打印结果，然后退出。
        -   **如果未提供**：启动一个循环读取-求值-打印的交互式会话（REPL），直到用户输入 `exit` 或 `quit`。

## 5. 其他命令迁移

-   `call-graph`: 改为 `code-learner call-graph --project <name_or_id> <root_function>`。
-   `dep-graph`: 改为 `code-learner dep-graph --project <name_or_id> --format <format>`。
-   `status`: 保持 `code-learner status`，但其内部实现需要更新，以能汇总所有已注册项目的信息。 