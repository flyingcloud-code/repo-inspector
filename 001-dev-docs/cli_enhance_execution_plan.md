# 统一命令行增强 - 执行计划

本文档将CLI增强任务分解为可管理的史诗和用户故事。

## Epic 1: 统一CLI入口重构

**目标**: 将所有独立的CLI脚本整合到 `code-learner` 单一命令下，建立清晰的子命令结构。

-   **Story 1.1**: **实现主命令入口**:
    -   **As a**: 开发者
    -   **I want**: 一个名为 `code-learner` 的主 python 脚本作为所有功能的入口
    -   **So that**: 用户只需记住一个命令。
    -   **AC**: 使用 `argparse` 创建主解析器，并设置子命令解析器。

-   **Story 1.2**: **迁移 `analyze` 功能**:
    -   **As a**: 开发者
    -   **I want**: 将 `code_analyzer_cli.py` 的核心分析逻辑重构为一个可调用的函数
    -   **So that**: `code-learner analyze` 子命令可以执行它。
    -   **AC**: `analyze` 子命令接收 `--project` 参数，并成功触发完整的分析流程。

-   **Story 1.3**: **迁移 `call-graph` 功能**:
    -   **As a**: 开发者
    -   **I want**: 将 `call_graph_cli.py` 的逻辑迁移到 `code-learner call-graph` 子命令下
    -   **So that**: 用户可以用统一的命令查询调用图。
    -   **AC**: `code-learner call-graph --project <id> <func>` 能正确生成调用图。

-   **Story 1.4**: **迁移 `dependency-graph` 功能**:
    -   **As a**: 开发者
    -   **I want**: 将 `dependency_cli.py` 的查询功能迁移到 `code-learner dep-graph` 子命令下
    -   **So that**: 用户可以用统一的命令查询依赖图。
    -   **AC**: `code-learner dep-graph --project <id>` 能正确生成依赖图。

-   **Story 1.5**: **清理旧的CLI脚本**:
    -   **As a**: 开发者
    -   **I want**: 删除所有已被整合的旧 `*_cli.py` 文件
    -   **So that**: 保持代码库的整洁，避免混淆。
    -   **AC**: `src/code_learner/cli/` 目录下只保留统一的入口文件和必要的模块。

## Epic 2: 项目生命周期管理

**目标**: 实现完整的项目创建、列表和删除功能，让用户可以显式管理项目。

-   **Story 2.1**: **实现项目注册表**:
    -   **As a**: 开发者
    -   **I want**: 一个健壮的模块来管理 `~/.code_learner/projects.json` 文件
    -   **So that**: 可以安全地读取、添加和删除项目条目。
    -   **AC**: 提供 `add_project`, `list_projects`, `delete_project`, `find_project` 等内部函数。

-   **Story 2.2**: **实现 `project create` 命令**:
    -   **As a**: 用户
    -   **I want**: 使用 `code-learner project create <path> --name <name>` 来注册一个新项目
    -   **So that**: 我可以用一个易记的短名称来引用我的项目。
    -   **AC**: 命令成功后，新项目信息被添加到 `projects.json`。

-   **Story 2.3**: **实现 `project list` 命令**:
    -   **As a**: 用户
    -   **I want**: 使用 `code-learner project list` 查看所有项目
    -   **So that**: 我能知道当前管理了哪些项目，以及它们的ID和路径。
    -   **AC**: 命令以清晰的表格格式输出所有已注册的项目。

-   **Story 2.4**: **实现 `project delete` 命令 (Neo4j & Chroma)**:
    -   **As a**: 用户
    -   **I want**: 使用 `code-learner project delete <name_or_id>` 来删除项目
    -   **So that**: 我能彻底清理一个项目在所有数据库中的数据。
    -   **AC**: Neo4j中所有带对应 `project_id` 的节点被删除；ChromaDB中对应的集合被删除。

-   **Story 2.5**: **实现 `project delete` 命令 (文件系统)**:
    -   **As a**: 用户
    -   **I want**: `project delete` 命令也能删除所有本地分析产物
    -   **So that**: 我的磁盘空间得到释放。
    -   **AC**: 删除项目在 `projects.json` 中的条目；删除本地的分析结果目录。

## Epic 3: 查询功能增强

**目标**: 提升 `query` 命令的灵活性，支持交互式和单次执行两种模式。

-   **Story 3.1**: **实现 `query` 命令的模式判断**:
    -   **As a**: 开发者
    -   **I want**: `query` 命令能根据是否传入 `-q` / `--query` 参数来切换模式
    -   **So that**: 框架能支持两种不同的用户使用场景。
    -   **AC**: 命令行解析逻辑能正确区分两种模式。

-   **Story 3.2**: **实现直接执行模式**:
    -   **As a**: 用户
    -   **I want**: 通过 `code-learner query --project <id> -q "..."` 直接得到答案
    -   **So that**: 我可以方便地在脚本或自动化流程中使用查询功能。
    -   **AC**: 命令执行后，打印答案并立即退出。

-   **Story 3.3**: **实现交互式会话 (REPL)**:
    -   **As a**: 用户
    -   **I want**: 运行 `code-learner query --project <id>` 后进入一个交互式环境
    -   **So that**: 我可以连续提问，进行探索性的分析，而无需每次都重新加载模型。
    -   **AC**: 进入一个循环，提示用户输入，执行查询，打印结果，直到用户输入 `exit`。

## Epic 4: 文档更新

**目标**: 确保所有面向用户的文档都与新的CLI设计保持一致。

-   **Story 4.1**: **更新 `CLI_USAGE_GUIDE.md`**:
    -   **As a**: 新用户
    -   **I want**: 阅读 `CLI_USAGE_GUIDE.md` 就能了解所有可用的命令和工作流程
    -   **So that**: 我能快速上手使用这个工具。
    -   **AC**: 文档完整地描述了 `project`, `analyze`, `query` 等所有新命令的用法和示例。 