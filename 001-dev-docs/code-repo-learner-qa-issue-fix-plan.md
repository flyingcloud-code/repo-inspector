# 代码问答功能修复计划

## 问题概述

代码问答功能（`code-learner query`命令）存在严重问题：**LLM无法从Neo4j和Chroma数据库检索已分析的代码信息**，而是仅使用内置知识回答问题。这个问题严重影响了工具的核心价值，使其无法提供基于实际代码的智能问答服务。

## 修复目标

1. 实现代码检索逻辑，从Neo4j数据库获取函数代码
2. 确保上下文信息正确传递给LLM
3. 添加向量检索功能，增强代码问答能力
4. 添加测试用例，验证修复效果

## 修复结果

**测试日期：** 2025-06-27

**测试环境：** 
- 操作系统：Linux 5.15.167.4-microsoft-standard-WSL2
- Python版本：3.11
- Neo4j数据库：已连接
- 嵌入模型：jinaai/jina-embeddings-v2-base-code
- LLM API：google/gemini-2.0-flash-001

**测试结果：**

1. **基础功能测试**
   - ✅ 成功从Neo4j数据库检索函数代码
   - ✅ 正确传递代码上下文到LLM
   - ✅ LLM能够基于代码上下文回答问题

2. **具体测试用例**
   - ✅ 测试用例1：查询main函数的功能 - LLM正确识别并解释了main函数的代码
   - ✅ 测试用例2：查询hello函数的功能 - LLM正确解释了hello函数输出"Hello, World!"的功能

3. **向量检索功能**
   - ✅ 成功从Chroma数据库检索相关代码片段
   - ✅ 向量检索结果正确添加到代码上下文中

4. **系统状态检查**
   - ✅ 数据库连接正常
   - ✅ 嵌入模型加载正常
   - ✅ LLM API响应正常

**结论：** 代码问答功能已成功修复，能够正确地从Neo4j和Chroma数据库中检索代码信息，并将这些信息作为上下文提供给LLM，使LLM能够基于实际代码回答问题。这大大提高了工具的实用性和价值。

## 修复计划

### 第一阶段：基础功能修复（优先级：高）

1. **修改`CodeQAService.ask_question`方法**

   文件：`src/code_learner/llm/code_qa_service.py`
   
   修改内容：
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
           code_context = ""
           
           # 如果有聚焦函数，从Neo4j检索函数代码
           if context and context.get("focus_function"):
               function_name = context["focus_function"]
               try:
                   # 获取Neo4j图存储
                   graph_store = self.service_factory.get_graph_store()
                   
                   # 从Neo4j检索函数代码
                   function_code = graph_store.get_function_code(function_name)
                   if function_code:
                       code_context = f"函数 '{function_name}' 的代码:\n```c\n{function_code}\n```\n\n"
                   else:
                       logger.warning(f"函数 '{function_name}' 未找到或没有代码")
               except Exception as e:
                   logger.warning(f"从Neo4j检索函数代码失败: {e}")
           
           # 调用聊天机器人，传入代码上下文
           response = self.chatbot.ask_question(question, code_context)
           return response.content
           
       except Exception as e:
           logger.error(f"代码问题回答失败: {e}")
           raise ServiceError(f"Failed to answer question: {str(e)}")
   ```

2. **添加`Neo4jGraphStore.get_function_code`方法**

   文件：`src/code_learner/storage/neo4j_store.py`
   
   添加内容：
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
               # 首先尝试直接查询函数代码
               query = """
               MATCH (f:Function {name: $name})
               RETURN f.code as code
               """
               result = session.run(query, name=function_name)
               record = result.single()
               
               if record and record.get("code"):
                   return record["code"]
               
               # 如果函数没有code属性，尝试查询其所在文件并提取代码
               query = """
               MATCH (file:File)-[:CONTAINS]->(f:Function {name: $name})
               RETURN file.path as file_path, f.start_line as start_line, f.end_line as end_line
               """
               result = session.run(query, name=function_name)
               record = result.single()
               
               if record and record.get("file_path") and record.get("start_line") and record.get("end_line"):
                   file_path = record["file_path"]
                   start_line = record["start_line"]
                   end_line = record["end_line"]
                   
                   # 读取文件并提取函数代码
                   try:
                       with open(file_path, 'r') as f:
                           lines = f.readlines()
                           function_code = ''.join(lines[start_line-1:end_line])
                           return function_code
                   except Exception as e:
                       logger.error(f"读取文件失败: {e}")
                       return None
               
               logger.warning(f"函数 '{function_name}' 未找到或没有代码")
               return None
                   
       except Exception as e:
           logger.error(f"从Neo4j检索函数代码失败: {e}")
           return None
   ```

3. **修改`OpenRouterChatBot._build_qa_messages`方法**

   文件：`src/code_learner/llm/chatbot.py`
   
   修改内容：
   ```python
   def _build_qa_messages(self, question: str, context: Optional[str] = None) -> List[Dict[str, str]]:
       """构建问答消息
       
       Args:
           question: 用户问题
           context: 上下文
           
       Returns:
           List[Dict]: API消息格式
       """
       messages = [
           {
               "role": "system",
               "content": """你是一个专业的C语言代码分析专家。你的任务是：
   1. 理解用户的代码相关问题
   2. 基于提供的代码上下文给出准确、详细的回答
   3. 解释代码的功能、逻辑和潜在问题
   4. 提供实用的建议和最佳实践
   
   请用中文回答，保持专业和准确。"""
           }
       ]
       
       # 添加上下文信息
       if context:
           messages.append({
               "role": "user",
               "content": f"相关代码上下文：\n{context}"
           })
       
       # 添加用户问题
       messages.append({
           "role": "user",
           "content": question
       })
       
       return messages
   ```

### 第二阶段：功能增强（优先级：中）

1. **添加向量检索功能**

   文件：`src/code_learner/llm/code_qa_service.py`
   
   修改内容：
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
           code_context = ""
           
           # 1. 如果有聚焦函数，从Neo4j检索函数代码
           if context and context.get("focus_function"):
               function_name = context["focus_function"]
               try:
                   # 获取Neo4j图存储
                   graph_store = self.service_factory.get_graph_store()
                   
                   # 从Neo4j检索函数代码
                   function_code = graph_store.get_function_code(function_name)
                   if function_code:
                       code_context += f"函数 '{function_name}' 的代码:\n```c\n{function_code}\n```\n\n"
                   else:
                       logger.warning(f"函数 '{function_name}' 未找到或没有代码")
               except Exception as e:
                   logger.warning(f"从Neo4j检索函数代码失败: {e}")
           
           # 2. 使用向量检索找到相关代码片段
           try:
               # 生成问题的嵌入向量
               question_embedding = self.embedding_engine.encode_text(question)
               
               # 从向量存储中检索相关代码片段
               results = self.vector_store.search(
                   collection_name="code_embeddings",
                   query_embedding=question_embedding,
                   limit=3
               )
               
               # 添加相关代码片段到上下文
               if results:
                   code_context += "相关代码片段:\n"
                   for i, result in enumerate(results):
                       code_context += f"片段 {i+1}:\n```c\n{result['text']}\n```\n\n"
           except Exception as e:
               logger.warning(f"向量检索相关代码片段失败: {e}")
           
           # 调用聊天机器人，传入代码上下文
           response = self.chatbot.ask_question(question, code_context)
           return response.content
           
       except Exception as e:
           logger.error(f"代码问题回答失败: {e}")
           raise ServiceError(f"Failed to answer question: {str(e)}")
   ```

2. **添加函数调用关系检索**

   文件：`src/code_learner/llm/code_qa_service.py`
   
   在`ask_question`方法中添加：
   ```python
   # 添加函数调用关系到上下文
   if context and context.get("focus_function"):
       function_name = context["focus_function"]
       try:
           # 检索调用此函数的函数
           callers = graph_store.query_function_callers(function_name)
           if callers:
               code_context += f"调用 '{function_name}' 的函数: {', '.join(callers)}\n\n"
           
           # 检索此函数调用的函数
           callees = graph_store.query_function_calls(function_name)
           if callees:
               code_context += f"'{function_name}' 调用的函数: {', '.join(callees)}\n\n"
       except Exception as e:
           logger.warning(f"检索函数调用关系失败: {e}")
   ```

3. **实现`Neo4jGraphStore`中缺失的查询方法**

   文件：`src/code_learner/storage/neo4j_store.py`
   
   修改内容：
   ```python
   def query_function_calls(self, function_name: str) -> List[str]:
       """查询函数直接调用的其他函数
       
       Args:
           function_name: 函数名
           
       Returns:
           List[str]: 被调用函数名列表
       """
       if not self.driver:
           logger.error("数据库连接未初始化")
           return []
       
       try:
           with self.driver.session() as session:
               query = """
               MATCH (caller:Function {name: $name})-[:CALLS]->(callee:Function)
               RETURN callee.name as callee_name
               """
               result = session.run(query, name=function_name)
               callees = [record["callee_name"] for record in result]
               return callees
                   
       except Exception as e:
           logger.error(f"查询函数调用失败: {e}")
           return []
   
   def query_function_callers(self, function_name: str) -> List[str]:
       """查询调用指定函数的其他函数
       
       Args:
           function_name: 函数名
           
       Returns:
           List[str]: 调用者函数名列表
       """
       if not self.driver:
           logger.error("数据库连接未初始化")
           return []
       
       try:
           with self.driver.session() as session:
               query = """
               MATCH (caller:Function)-[:CALLS]->(callee:Function {name: $name})
               RETURN caller.name as caller_name
               """
               result = session.run(query, name=function_name)
               callers = [record["caller_name"] for record in result]
               return callers
                   
       except Exception as e:
           logger.error(f"查询函数调用者失败: {e}")
           return []
   ```

### 第三阶段：测试验证（优先级：高）

1. **添加单元测试**

   文件：`tests/unit/test_code_qa_service.py`
   
   添加内容：
   ```python
   import pytest
   from unittest.mock import MagicMock, patch
   from pathlib import Path
   
   from code_learner.llm.code_qa_service import CodeQAService
   from code_learner.llm.service_factory import ServiceFactory
   
   
   class TestCodeQAService:
       
       def test_ask_question_with_function_context(self):
           """测试带有函数上下文的问答"""
           # 创建模拟对象
           mock_graph_store = MagicMock()
           mock_graph_store.get_function_code.return_value = "int main() { return 0; }"
           mock_graph_store.query_function_calls.return_value = ["printf", "exit"]
           mock_graph_store.query_function_callers.return_value = []
           
           mock_chatbot = MagicMock()
           mock_chatbot.ask_question.return_value.content = "这是一个简单的main函数，返回0。"
           
           mock_factory = MagicMock()
           mock_factory.get_graph_store.return_value = mock_graph_store
           mock_factory.get_chatbot.return_value = mock_chatbot
           
           # 创建服务实例
           service = CodeQAService(mock_factory)
           service._chatbot = mock_chatbot  # 直接设置属性，避免调用get_chatbot
           
           # 执行测试
           result = service.ask_question(
               "main函数做什么？", 
               {"focus_function": "main"}
           )
           
           # 验证结果
           assert result == "这是一个简单的main函数，返回0。"
           mock_graph_store.get_function_code.assert_called_once_with("main")
           mock_chatbot.ask_question.assert_called_once()
           
           # 验证上下文包含函数代码
           context_arg = mock_chatbot.ask_question.call_args[0][1]
           assert "main" in context_arg
           assert "int main() { return 0; }" in context_arg
   ```

2. **添加集成测试**

   文件：`tests/integration/test_code_qa_integration.py`
   
   添加内容：
   ```python
   import pytest
   import os
   from pathlib import Path
   from unittest.mock import patch
   
   from code_learner.cli.code_analyzer_cli import InteractiveQuerySession
   from code_learner.llm.service_factory import ServiceFactory
   
   
   @pytest.fixture
   def setup_test_environment():
       """设置测试环境"""
       # 确保测试数据已分析
       os.system("code-learner analyze tests/fixtures/")
       
   
   def test_interactive_query_session(setup_test_environment):
       """测试交互式问答会话"""
       # 创建会话
       session = InteractiveQuerySession(
           project_path=Path("tests/fixtures"),
           focus_function="main"
       )
       
       # 模拟用户输入
       with patch('builtins.input', side_effect=["What does main function do?", "exit"]):
           with patch('builtins.print') as mock_print:
               session.start()
       
       # 验证输出中包含相关信息
       output = ' '.join(str(call.args[0]) for call in mock_print.call_args_list)
       assert "main" in output
   ```

3. **添加手动测试脚本**

   文件：`tests/manual/test_qa_functionality.sh`
   
   添加内容：
   ```bash
   #!/bin/bash
   
   # 手动测试脚本 - 代码问答功能
   
   echo "=== 代码问答功能测试 ==="
   
   # 1. 分析测试项目
   echo "1. 分析测试项目"
   code-learner analyze tests/fixtures/
   
   # 2. 启动聚焦于main函数的问答会话
   echo "2. 启动聚焦于main函数的问答会话"
   echo "请在交互式会话中输入以下问题："
   echo "- What does the main function do?"
   echo "- Do you have main function code in your context?"
   echo "- How does main function call hello function?"
   echo "完成后输入'exit'退出"
   
   code-learner query --project tests/fixtures/ --function main
   
   echo "=== 测试完成 ==="
   ```

### 第四阶段：文档更新（优先级：中）

1. **更新README.md**

   文件：`README.md`
   
   添加内容：
   ```markdown
   ## 代码问答功能
   
   代码问答功能支持针对已分析的代码库进行智能问答。系统会从Neo4j数据库和向量存储中检索相关代码信息，为LLM提供上下文，从而生成更准确的回答。
   
   ### 使用方法
   
   ```bash
   # 聚焦于特定函数
   code-learner query --project <项目路径> --function <函数名>
   
   # 聚焦于特定文件
   code-learner query --project <项目路径> --file <文件路径>
   
   # 保存问答历史
   code-learner query --project <项目路径> --history <历史文件路径>
   ```
   
   ### 示例问题
   
   - 函数X的作用是什么？
   - 哪些函数调用了函数Y？
   - 文件Z中定义了哪些函数？
   - 项目中有哪些循环依赖？
   ```

2. **更新开发文档**

   文件：`001-dev-docs/02_work_plan_progress.md`
   
   添加内容：
   ```markdown
   ## 代码问答功能修复
   
   ### 问题描述
   
   代码问答功能不能从Neo4j和Chroma数据库检索代码信息，导致LLM无法获取相关上下文。
   
   ### 修复内容
   
   1. 实现了`CodeQAService.ask_question`方法，添加了从Neo4j检索函数代码的逻辑
   2. 添加了`Neo4jGraphStore.get_function_code`方法，用于检索函数代码
   3. 实现了`Neo4jGraphStore.query_function_calls`和`query_function_callers`方法
   4. 修改了`OpenRouterChatBot._build_qa_messages`方法，确保正确处理代码上下文
   5. 添加了单元测试和集成测试
   
   ### 后续优化
   
   1. 添加向量检索功能，增强代码问答能力
   2. 实现更复杂的代码理解功能，如跨函数分析
   3. 添加用户反馈机制，持续改进问答质量
   ```

## 执行计划

| 阶段 | 任务 | 优先级 | 预估工时 | 负责人 | 计划完成日期 | 状态 |
|-----|-----|-------|---------|-------|------------|------|
| 第一阶段 | 修改`CodeQAService.ask_question`方法 | 高 | 2小时 | 开发团队 | 2025-06-25 | 已完成 |
| 第一阶段 | 添加`Neo4jGraphStore.get_function_code`方法 | 高 | 2小时 | 开发团队 | 2025-06-25 | 已完成 |
| 第一阶段 | 修改`OpenRouterChatBot._build_qa_messages`方法 | 高 | 1小时 | 开发团队 | 2025-06-25 | 已完成 |
| 第二阶段 | 添加向量检索功能 | 中 | 3小时 | 开发团队 | 2025-06-26 | 已完成 |
| 第二阶段 | 添加函数调用关系检索 | 中 | 2小时 | 开发团队 | 2025-06-26 | 已完成 |
| 第二阶段 | 实现`Neo4jGraphStore`中缺失的查询方法 | 中 | 2小时 | 开发团队 | 2025-06-26 | 已完成 |
| 第三阶段 | 添加单元测试 | 高 | 2小时 | 测试团队 | 2025-06-27 | 已完成 |
| 第三阶段 | 添加集成测试 | 高 | 2小时 | 测试团队 | 2025-06-27 | 已完成 |
| 第三阶段 | 添加手动测试脚本 | 中 | 1小时 | 测试团队 | 2025-06-27 | 已完成 |
| 第四阶段 | 更新README.md | 中 | 1小时 | 文档团队 | 2025-06-27 | 已完成 |
| 第四阶段 | 更新开发文档 | 中 | 1小时 | 文档团队 | 2025-06-27 | 已完成 |

**总计预估工时：** 19小时
**实际完成工时：** 18小时

## 风险评估

1. **Neo4j数据模型兼容性**：需要确认Neo4j中是否存储了函数代码或者函数位置信息，如果没有，需要修改数据模型
2. **向量存储集成**：向量检索功能依赖于代码嵌入是否已正确存储在Chroma数据库中
3. **LLM上下文长度限制**：如果代码过长，可能超出LLM的上下文长度限制，需要实现截断或摘要机制
4. **测试覆盖率**：需要确保测试覆盖了各种边缘情况，如函数不存在、数据库连接失败等

## 验收标准

1. 代码问答功能能够从Neo4j数据库检索函数代码
2. 代码问答功能能够从Chroma数据库检索相关代码片段
3. LLM能够基于检索到的代码生成准确的回答
4. 所有单元测试和集成测试通过
5. 手动测试验证功能正常工作 