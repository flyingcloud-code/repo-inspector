# 代码问答功能修复实施计划

## 概述

本文档详细说明代码问答功能修复的具体实施步骤、时间表和负责人分配。修复计划基于[代码问答功能修复计划](code-repo-learner-qa-issue-fix-plan.md)和[史诗故事与评估](qa-issue-epic-story.md)文档，采用分阶段实施策略，确保高质量交付。

## 实施阶段

### 第一阶段：基础功能修复（2025-06-28 ~ 2025-06-29）

| 任务ID | 任务描述 | 负责人 | 预估工时 | 计划日期 | 前置任务 |
|-------|---------|-------|---------|---------|---------|
| 1.1 | 创建失败测试用例 | 张工 | 2小时 | 2025-06-28 | 无 |
| 1.2 | 修改`CodeQAService.ask_question`方法 | 张工 | 2小时 | 2025-06-28 | 1.1 |
| 1.3 | 添加`Neo4jGraphStore.get_function_code`方法 | 李工 | 3小时 | 2025-06-28 | 无 |
| 1.4 | 修改`OpenRouterChatBot._build_qa_messages`方法 | 张工 | 1小时 | 2025-06-28 | 1.2 |
| 1.5 | 单元测试验证 | 张工 | 2小时 | 2025-06-29 | 1.2, 1.3, 1.4 |
| 1.6 | 集成测试验证 | 李工 | 2小时 | 2025-06-29 | 1.5 |
| 1.7 | 代码审查与修复 | 王工 | 2小时 | 2025-06-29 | 1.6 |

**第一阶段交付物**：
- 修复后的`CodeQAService.ask_question`方法
- 新增的`Neo4jGraphStore.get_function_code`方法
- 修改后的`OpenRouterChatBot._build_qa_messages`方法
- 单元测试与集成测试用例
- 代码审查报告

### 第二阶段：功能增强（2025-06-30 ~ 2025-07-01）

| 任务ID | 任务描述 | 负责人 | 预估工时 | 计划日期 | 前置任务 |
|-------|---------|-------|---------|---------|---------|
| 2.1 | 实现`Neo4jGraphStore.query_function_calls`方法 | 李工 | 2小时 | 2025-06-30 | 1.7 |
| 2.2 | 实现`Neo4jGraphStore.query_function_callers`方法 | 李工 | 2小时 | 2025-06-30 | 1.7 |
| 2.3 | 添加函数调用关系检索到`CodeQAService` | 张工 | 2小时 | 2025-06-30 | 2.1, 2.2 |
| 2.4 | 添加向量检索功能到`CodeQAService` | 张工 | 3小时 | 2025-07-01 | 2.3 |
| 2.5 | 单元测试验证 | 张工 | 2小时 | 2025-07-01 | 2.3, 2.4 |
| 2.6 | 集成测试验证 | 李工 | 2小时 | 2025-07-01 | 2.5 |
| 2.7 | 性能测试与优化 | 王工 | 3小时 | 2025-07-01 | 2.6 |

**第二阶段交付物**：
- 实现的函数调用关系检索方法
- 添加的向量检索功能
- 单元测试与集成测试用例
- 性能测试报告与优化建议

### 第三阶段：测试与文档（2025-07-02 ~ 2025-07-03）

| 任务ID | 任务描述 | 负责人 | 预估工时 | 计划日期 | 前置任务 |
|-------|---------|-------|---------|---------|---------|
| 3.1 | 添加手动测试脚本 | 李工 | 2小时 | 2025-07-02 | 2.7 |
| 3.2 | 更新README.md | 王工 | 1小时 | 2025-07-02 | 2.7 |
| 3.3 | 更新开发文档 | 王工 | 2小时 | 2025-07-02 | 2.7 |
| 3.4 | 端到端测试验证 | 张工 | 3小时 | 2025-07-02 | 3.1 |
| 3.5 | 用户验收测试 | 产品经理 | 4小时 | 2025-07-03 | 3.4 |
| 3.6 | 最终代码审查 | 技术主管 | 2小时 | 2025-07-03 | 3.5 |
| 3.7 | 发布准备 | 张工 | 1小时 | 2025-07-03 | 3.6 |

**第三阶段交付物**：
- 手动测试脚本
- 更新的README.md
- 更新的开发文档
- 端到端测试报告
- 用户验收测试报告
- 最终代码审查报告
- 发布就绪代码

## 代码实现细节

### 1. `CodeQAService.ask_question`方法优化

```python
def ask_question(self, question: str, context: Optional[dict] = None) -> str:
    """询问代码相关问题
    
    Args:
        question: 用户问题
        context: 上下文信息，包含project_path, focus_function, focus_file
        
    Returns:
        str: 回答内容
    """
    try:
        # 初始化代码上下文
        code_context = self._build_code_context(question, context)
        
        # 调用聊天机器人，传入代码上下文
        response = self.chatbot.ask_question(question, code_context)
        return response.content
        
    except Exception as e:
        logger.error(f"代码问题回答失败: {e}")
        raise ServiceError(f"Failed to answer question: {str(e)}")

def _build_code_context(self, question: str, context: Optional[dict] = None) -> str:
    """构建代码上下文，从多个来源获取相关代码
    
    Args:
        question: 用户问题
        context: 上下文信息
        
    Returns:
        str: 代码上下文
    """
    code_context = ""
    
    # 1. 从Neo4j获取函数代码
    if context and context.get("focus_function"):
        code_context += self._get_function_context(context["focus_function"])
    
    # 2. 从文件获取代码
    if context and context.get("focus_file"):
        code_context += self._get_file_context(context["focus_file"])
    
    return code_context

def _get_function_context(self, function_name: str) -> str:
    """获取函数上下文
    
    Args:
        function_name: 函数名
        
    Returns:
        str: 函数上下文
    """
    context = ""
    try:
        # 获取Neo4j图存储
        graph_store = self.service_factory.get_graph_store()
        
        # 从Neo4j检索函数代码
        function_code = graph_store.get_function_code(function_name)
        if function_code:
            context += f"函数 '{function_name}' 的代码:\n```c\n{function_code}\n```\n\n"
        else:
            logger.warning(f"函数 '{function_name}' 未找到或没有代码")
        
        # 检索函数调用关系
        callers = graph_store.query_function_callers(function_name)
        if callers:
            context += f"调用 '{function_name}' 的函数: {', '.join(callers)}\n\n"
        
        callees = graph_store.query_function_calls(function_name)
        if callees:
            context += f"'{function_name}' 调用的函数: {', '.join(callees)}\n\n"
            
    except Exception as e:
        logger.warning(f"获取函数上下文失败: {e}")
        
    return context
```

### 2. `Neo4jGraphStore.get_function_code`方法优化

```python
def get_function_code(self, function_name: str) -> Optional[str]:
    """获取函数代码
    
    Args:
        function_name: 函数名
        
    Returns:
        Optional[str]: 函数代码，如果不存在则返回None
    """
    if not self.driver:
        logger.error("数据库连接未初始化")
        return None
    
    try:
        with self.driver.session() as session:
            # 单次查询，获取函数代码或位置信息
            query = """
            MATCH (f:Function {name: $name})
            OPTIONAL MATCH (file:File)-[:CONTAINS]->(f)
            RETURN f.code as code, file.path as file_path, 
                   f.start_line as start_line, f.end_line as end_line
            """
            result = session.run(query, name=function_name)
            record = result.single()
            
            if not record:
                logger.warning(f"函数 '{function_name}' 未找到")
                return None
            
            # 优先使用存储的代码
            if record.get("code"):
                return record["code"]
            
            # 如果没有存储代码但有位置信息，从文件读取
            if record.get("file_path") and record.get("start_line") and record.get("end_line"):
                return self._read_function_from_file(
                    record["file_path"], 
                    record["start_line"], 
                    record["end_line"]
                )
            
            return None
                
    except Exception as e:
        logger.error(f"从Neo4j检索函数代码失败: {e}")
        return None

def _read_function_from_file(self, file_path: str, start_line: int, end_line: int) -> Optional[str]:
    """从文件读取函数代码
    
    Args:
        file_path: 文件路径
        start_line: 起始行（从1开始）
        end_line: 结束行
        
    Returns:
        Optional[str]: 函数代码
    """
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            if start_line <= len(lines) and end_line <= len(lines):
                function_code = ''.join(lines[start_line-1:end_line])
                return function_code
            else:
                logger.warning(f"文件行数不足: {file_path}, 总行数: {len(lines)}, 请求行: {start_line}-{end_line}")
                return None
    except Exception as e:
        logger.error(f"读取文件失败: {file_path}, 错误: {e}")
        return None
```

## 测试计划

### 单元测试

1. **`test_code_qa_service.py`**:
   - `test_ask_question_with_function_context`: 测试带有函数上下文的问答
   - `test_ask_question_without_context`: 测试无上下文时的行为
   - `test_ask_question_with_invalid_function`: 测试无效函数名的处理
   - `test_build_code_context`: 测试代码上下文构建
   - `test_get_function_context`: 测试函数上下文获取

2. **`test_neo4j_store.py`**:
   - `test_get_function_code_with_stored_code`: 测试从存储的代码获取函数代码
   - `test_get_function_code_from_file`: 测试从文件获取函数代码
   - `test_get_function_code_not_found`: 测试函数不存在的情况
   - `test_query_function_calls`: 测试查询函数调用
   - `test_query_function_callers`: 测试查询函数调用者

### 集成测试

1. **`test_code_qa_integration.py`**:
   - `test_interactive_query_session`: 测试交互式问答会话
   - `test_query_with_function_focus`: 测试聚焦于函数的问答
   - `test_query_with_file_focus`: 测试聚焦于文件的问答
   - `test_vector_search_integration`: 测试向量检索集成

### 手动测试

1. **`test_qa_functionality.sh`**:
   - 测试项目分析
   - 测试聚焦于函数的问答
   - 测试聚焦于文件的问答
   - 测试向量检索功能

## 风险与缓解措施

| 风险 | 影响 | 可能性 | 缓解措施 | 负责人 |
|-----|------|-------|---------|-------|
| Neo4j数据模型不兼容 | 高 | 中 | 提前验证数据模型，准备备选方案 | 李工 |
| 文件读取错误 | 中 | 低 | 添加健壮的错误处理和日志记录 | 张工 |
| 性能问题 | 中 | 中 | 实现缓存机制，监控响应时间 | 王工 |
| 接口行为变化导致回归 | 高 | 低 | 添加详细日志，进行全面回归测试 | 张工 |
| LLM上下文长度限制 | 中 | 中 | 实现上下文截断和摘要机制 | 张工 |

## 验收标准

1. 所有单元测试和集成测试通过
2. 代码问答功能能够从Neo4j数据库检索函数代码
3. 代码问答功能能够从Chroma数据库检索相关代码片段
4. LLM能够基于检索到的代码生成准确的回答
5. 响应时间满足性能要求（<3秒）
6. 代码符合项目编码规范
7. 文档更新完整

## 发布计划

1. **代码合并**：2025-07-03
2. **内部测试**：2025-07-04
3. **正式发布**：2025-07-05

## 后续优化计划

1. **上下文优化**：实现更智能的上下文选择和截断机制
2. **缓存机制**：添加函数代码和向量检索结果的缓存
3. **用户反馈**：添加用户反馈机制，持续改进问答质量
4. **多模态支持**：添加对代码图表和可视化的支持 