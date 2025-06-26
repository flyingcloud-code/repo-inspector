 # Code-Repo-Learner 数据探索指南

本文档提供了使用 Cypher 查询语言与 Neo4j 数据库交互的常用命令，帮助你探索 `code-learner` 工具分析代码仓库后生成的数据。

## 1. 如何连接到 Neo4j

最简单的方式是使用 Neo4j 的浏览器界面：

1.  在你的网页浏览器中打开：`http://localhost:7474`
2.  使用以下凭据登录：
    *   **Username**: `neo4j`
    *   **Password**: 这是你在 `.env` 文件中为 `NEO4J_PASSWORD` 设置的密码 (例如: `neo4j` 或  from .env file)

登录后，你将看到一个可以输入 Cypher 命令的查询框。

## 2. 基本查询

### 查看所有节点类型和关系
这是一个很好的起点，可以了解数据库中有哪些类型的数据。
```cypher
CALL db.schema.visualization()
```

### 查看少量数据样本
查看数据库中任意25个节点和它们的关系，对数据建立一个初步印象。
```cypher
MATCH (n) RETURN n LIMIT 25
```

## 3. 查询特定节点

### 查询文件 (File)
查看项目中被分析的所有文件。
```cypher
// 返回前50个文件的路径和名称
MATCH (f:File) 
RETURN f.path, f.name 
LIMIT 50
```

### 查询函数 (Function)
查看代码中定义的所有函数。
```cypher
// 返回前50个函数的名称和它们所在的文件路径
MATCH (fn:Function) 
RETURN fn.name, fn.file_path 
LIMIT 50
```

### 查询模块 (Module)
模块是根据文件路径的目录结构推断出来的。
```cypher
// 返回所有模块的名称
MATCH (m:Module)
RETURN m.name
```

## 4. 查询节点属性

你可以查询任何节点的具体属性。只需要在 `RETURN` 语句中指定你想要的属性即可。

### 查看特定函数的所有属性
将 `main` 替换为你感兴趣的任何函数名。
```cypher
MATCH (fn:Function {name: 'main'}) 
RETURN fn
```
*   **提示**: Neo4j 浏览器会以非常友好的方式展示节点的所有属性。

### 查看特定文件的所有属性
将 `/path/to/your/file.c` 替换为真实的文件路径。
```cypher
MATCH (f:File {path: '/path/to/your/file.c'})
RETURN f
```

## 5. 查询调用图 (Call Graph)

调用图是通过 `Function` 节点之间的 `CALLS` 关系来表示的。

### 查看一个函数调用了哪些其他函数
这个查询会找出 `main` 函数直接调用的所有函数。
```cypher
// 将 'main' 替换为任何你想查询的函数名
MATCH (caller:Function {name: 'main'})-[:CALLS]->(callee:Function)
RETURN caller.name AS 调用者, callee.name AS 被调用者
```

### 查看一个函数被哪些函数调用
这个查询会找出是哪些函数调用了 `sbi_console_putchar`。
```cypher
// 将 'sbi_console_putchar' 替换为任何你想查询的函数名
MATCH (caller:Function)-[:CALLS]->(callee:Function {name: 'sbi_console_putchar'})
RETURN caller.name AS 调用者, callee.name AS 被调用者
```

### 可视化部分调用图
这是 Cypher 最强大的功能之一。这个查询会找到10条调用路径，并在浏览器中将它们绘制成图。
```cypher
MATCH path = (f1:Function)-[:CALLS]->(f2:Function)
RETURN path
LIMIT 10
```

## 6. 查询依赖关系

依赖关系是通过 `File` 和 `Module` 节点之间的 `DEPENDS_ON` 关系来表示的。

### 查看文件间的依赖
```cypher
MATCH path = (f1:File)-[:DEPENDS_ON]->(f2:File)
RETURN path
LIMIT 20
```

### 查看模块间的依赖
```cypher
MATCH path = (m1:Module)-[:DEPENDS_ON]->(m2:Module)
RETURN path
```

希望这份指南能帮助你开始探索代码的奥秘！
