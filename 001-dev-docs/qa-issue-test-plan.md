# 代码问答功能修复测试计划

## 概述

本文档详细说明代码问答功能修复的测试策略和测试用例。测试计划基于[代码问答功能修复计划](code-repo-learner-qa-issue-fix-plan.md)和[实施计划](qa-issue-implementation-plan.md)文档，采用多层次测试策略，确保修复的质量和稳定性。

## 测试策略

### 测试层次

1. **单元测试**：验证各组件的独立功能
2. **集成测试**：验证组件间的交互
3. **端到端测试**：验证完整功能流程
4. **手动测试**：验证用户体验和边缘情况

### 测试环境

- **开发环境**：Ubuntu 24.04 LTS (WSL2)
- **Python版本**：3.11+
- **Neo4j版本**：5.26 Community Edition
- **测试数据**：预先准备的C语言测试项目

## 单元测试

### 1. `test_code_qa_service.py`

#### 测试用例1.1：`test_ask_question_with_function_context`

**目的**：验证带有函数上下文的问答功能

**步骤**：
1. 创建模拟对象：`graph_store`, `chatbot`, `factory`
2. 设置模拟返回值：函数代码、调用关系
3. 创建`CodeQAService`实例
4. 调用`ask_question`方法，传入问题和函数上下文
5. 验证返回结果和调用情况

**预期结果**：
- 返回正确的回答内容
- `get_function_code`方法被调用一次
- 传递给`chatbot.ask_question`的上下文包含函数代码

**代码**：
```python
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

#### 测试用例1.2：`test_ask_question_without_context`

**目的**：验证无上下文时的问答功能

**步骤**：
1. 创建模拟对象：`chatbot`, `factory`
2. 创建`CodeQAService`实例
3. 调用`ask_question`方法，不传入上下文
4. 验证返回结果和调用情况

**预期结果**：
- 返回正确的回答内容
- `chatbot.ask_question`被调用，但上下文为空

**代码**：
```python
def test_ask_question_without_context(self):
    """测试无上下文时的问答"""
    # 创建模拟对象
    mock_chatbot = MagicMock()
    mock_chatbot.ask_question.return_value.content = "这是一个回答。"
    
    mock_factory = MagicMock()
    mock_factory.get_chatbot.return_value = mock_chatbot
    
    # 创建服务实例
    service = CodeQAService(mock_factory)
    service._chatbot = mock_chatbot  # 直接设置属性，避免调用get_chatbot
    
    # 执行测试
    result = service.ask_question("这是一个问题")
    
    # 验证结果
    assert result == "这是一个回答。"
    mock_chatbot.ask_question.assert_called_once()
    
    # 验证上下文为空
    context_arg = mock_chatbot.ask_question.call_args[0][1]
    assert context_arg == ""
```

#### 测试用例1.3：`test_ask_question_with_invalid_function`

**目的**：验证无效函数名的处理

**步骤**：
1. 创建模拟对象：`graph_store`, `chatbot`, `factory`
2. 设置`get_function_code`返回`None`
3. 创建`CodeQAService`实例
4. 调用`ask_question`方法，传入无效函数名
5. 验证返回结果和调用情况

**预期结果**：
- 返回正确的回答内容
- `get_function_code`方法被调用一次
- 传递给`chatbot.ask_question`的上下文为空

**代码**：
```python
def test_ask_question_with_invalid_function(self):
    """测试无效函数名的处理"""
    # 创建模拟对象
    mock_graph_store = MagicMock()
    mock_graph_store.get_function_code.return_value = None
    mock_graph_store.query_function_calls.return_value = []
    mock_graph_store.query_function_callers.return_value = []
    
    mock_chatbot = MagicMock()
    mock_chatbot.ask_question.return_value.content = "未找到该函数。"
    
    mock_factory = MagicMock()
    mock_factory.get_graph_store.return_value = mock_graph_store
    mock_factory.get_chatbot.return_value = mock_chatbot
    
    # 创建服务实例
    service = CodeQAService(mock_factory)
    service._chatbot = mock_chatbot  # 直接设置属性，避免调用get_chatbot
    
    # 执行测试
    result = service.ask_question(
        "non_existent_function函数做什么？", 
        {"focus_function": "non_existent_function"}
    )
    
    # 验证结果
    assert result == "未找到该函数。"
    mock_graph_store.get_function_code.assert_called_once_with("non_existent_function")
    mock_chatbot.ask_question.assert_called_once()
    
    # 验证上下文为空
    context_arg = mock_chatbot.ask_question.call_args[0][1]
    assert "non_existent_function" not in context_arg or "未找到" in context_arg
```

#### 测试用例1.4：`test_build_code_context`

**目的**：验证代码上下文构建功能

**步骤**：
1. 创建模拟对象：`graph_store`, `factory`
2. 设置模拟返回值：函数代码、调用关系
3. 创建`CodeQAService`实例
4. 调用`_build_code_context`方法
5. 验证返回的上下文内容

**预期结果**：
- 返回的上下文包含函数代码和调用关系

**代码**：
```python
def test_build_code_context(self):
    """测试代码上下文构建"""
    # 创建模拟对象
    mock_graph_store = MagicMock()
    mock_graph_store.get_function_code.return_value = "int main() { return 0; }"
    mock_graph_store.query_function_calls.return_value = ["printf", "exit"]
    mock_graph_store.query_function_callers.return_value = []
    
    mock_factory = MagicMock()
    mock_factory.get_graph_store.return_value = mock_graph_store
    
    # 创建服务实例
    service = CodeQAService(mock_factory)
    
    # 执行测试
    context = service._build_code_context(
        "main函数做什么？", 
        {"focus_function": "main"}
    )
    
    # 验证结果
    assert "main" in context
    assert "int main() { return 0; }" in context
    assert "printf" in context
    assert "exit" in context
```

### 2. `test_neo4j_store.py`

#### 测试用例2.1：`test_get_function_code_with_stored_code`

**目的**：验证从存储的代码获取函数代码

**步骤**：
1. 创建模拟Neo4j会话和结果
2. 设置模拟返回值：存储的函数代码
3. 调用`get_function_code`方法
4. 验证返回结果

**预期结果**：
- 返回正确的函数代码
- Neo4j查询被正确执行

**代码**：
```python
def test_get_function_code_with_stored_code(self):
    """测试从存储的代码获取函数代码"""
    # 创建模拟对象
    mock_record = MagicMock()
    mock_record.get.side_effect = lambda key: {
        "code": "int main() { return 0; }",
        "file_path": "/path/to/file.c",
        "start_line": 1,
        "end_line": 3
    }.get(key)
    
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    
    mock_session = MagicMock()
    mock_session.run.return_value = mock_result
    
    mock_driver = MagicMock()
    mock_driver.__enter__.return_value = mock_session
    
    # 创建Neo4jGraphStore实例
    store = Neo4jGraphStore()
    store.driver = MagicMock()
    store.driver.session.return_value = mock_driver
    
    # 执行测试
    result = store.get_function_code("main")
    
    # 验证结果
    assert result == "int main() { return 0; }"
    mock_session.run.assert_called_once()
    query_arg = mock_session.run.call_args[0][0]
    assert "MATCH" in query_arg
    assert "Function" in query_arg
```

#### 测试用例2.2：`test_get_function_code_from_file`

**目的**：验证从文件获取函数代码

**步骤**：
1. 创建模拟Neo4j会话和结果
2. 设置模拟返回值：函数位置信息（无存储代码）
3. 模拟文件读取
4. 调用`get_function_code`方法
5. 验证返回结果

**预期结果**：
- 返回从文件读取的函数代码
- Neo4j查询和文件读取被正确执行

**代码**：
```python
def test_get_function_code_from_file(self):
    """测试从文件获取函数代码"""
    # 创建模拟对象
    mock_record = MagicMock()
    mock_record.get.side_effect = lambda key: {
        "code": None,
        "file_path": "/path/to/file.c",
        "start_line": 1,
        "end_line": 3
    }.get(key)
    
    mock_result = MagicMock()
    mock_result.single.return_value = mock_record
    
    mock_session = MagicMock()
    mock_session.run.return_value = mock_result
    
    mock_driver = MagicMock()
    mock_driver.__enter__.return_value = mock_session
    
    # 创建Neo4jGraphStore实例
    store = Neo4jGraphStore()
    store.driver = MagicMock()
    store.driver.session.return_value = mock_driver
    
    # 模拟文件读取
    with patch("builtins.open", mock_open(read_data="int main() {\n    return 0;\n}\n")) as mock_file:
        # 执行测试
        result = store.get_function_code("main")
    
    # 验证结果
    assert result == "int main() {\n    return 0;\n}\n"
    mock_session.run.assert_called_once()
    mock_file.assert_called_once_with("/path/to/file.c", "r")
```

#### 测试用例2.3：`test_get_function_code_not_found`

**目的**：验证函数不存在的情况

**步骤**：
1. 创建模拟Neo4j会话和结果
2. 设置模拟返回值：None（函数不存在）
3. 调用`get_function_code`方法
4. 验证返回结果

**预期结果**：
- 返回None
- Neo4j查询被正确执行
- 记录警告日志

**代码**：
```python
def test_get_function_code_not_found(self):
    """测试函数不存在的情况"""
    # 创建模拟对象
    mock_result = MagicMock()
    mock_result.single.return_value = None
    
    mock_session = MagicMock()
    mock_session.run.return_value = mock_result
    
    mock_driver = MagicMock()
    mock_driver.__enter__.return_value = mock_session
    
    # 创建Neo4jGraphStore实例
    store = Neo4jGraphStore()
    store.driver = MagicMock()
    store.driver.session.return_value = mock_driver
    
    # 执行测试
    with self.assertLogs(level="WARNING") as log:
        result = store.get_function_code("non_existent_function")
    
    # 验证结果
    assert result is None
    mock_session.run.assert_called_once()
    assert any("未找到" in msg for msg in log.output)
```

## 集成测试

### 1. `test_code_qa_integration.py`

#### 测试用例3.1：`test_interactive_query_session`

**目的**：验证交互式问答会话的端到端功能

**步骤**：
1. 设置测试环境：分析测试项目
2. 创建`InteractiveQuerySession`实例
3. 模拟用户输入和输出
4. 启动会话
5. 验证输出结果

**预期结果**：
- 会话正常运行
- 输出中包含函数信息

**代码**：
```python
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

#### 测试用例3.2：`test_query_with_function_focus`

**目的**：验证聚焦于函数的问答功能

**步骤**：
1. 设置测试环境：分析测试项目
2. 创建`CodeQAService`实例
3. 调用`ask_question`方法，传入函数上下文
4. 验证返回结果

**预期结果**：
- 返回包含函数信息的回答
- 回答中包含函数代码或相关信息

**代码**：
```python
def test_query_with_function_focus(setup_test_environment):
    """测试聚焦于函数的问答"""
    # 创建服务实例
    factory = ServiceFactory()
    service = CodeQAService(factory)
    
    # 执行测试
    result = service.ask_question(
        "What does main function do?",
        {"focus_function": "main", "project_path": "tests/fixtures"}
    )
    
    # 验证结果
    assert result is not None
    assert len(result) > 0
    assert "main" in result.lower()
```

#### 测试用例3.3：`test_vector_search_integration`

**目的**：验证向量检索集成功能

**步骤**：
1. 设置测试环境：分析测试项目并生成向量嵌入
2. 创建`CodeQAService`实例
3. 调用`ask_question`方法，传入需要向量检索的问题
4. 验证返回结果

**预期结果**：
- 返回包含相关代码片段的回答
- 向量检索功能正常工作

**代码**：
```python
def test_vector_search_integration(setup_test_environment):
    """测试向量检索集成"""
    # 创建服务实例
    factory = ServiceFactory()
    service = CodeQAService(factory)
    
    # 确保向量存储已初始化
    vector_store = factory.create_vector_store()
    
    # 执行测试
    result = service.ask_question(
        "How are printf functions used in the code?",
        {"project_path": "tests/fixtures"}
    )
    
    # 验证结果
    assert result is not None
    assert len(result) > 0
    # 由于向量检索结果可能变化，这里只做基本验证
    assert "printf" in result.lower() or "print" in result.lower()
```

## 手动测试

### 1. `test_qa_functionality.sh`

**目的**：提供手动测试脚本，验证代码问答功能的端到端体验

**内容**：
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

### 2. 手动验证清单

**目的**：提供手动测试的验证清单，确保功能正常工作

**验证项**：
1. 代码问答功能能够从Neo4j数据库检索函数代码
   - 检查回答中是否包含函数代码
   - 检查回答是否基于实际代码而非通用知识

2. 代码问答功能能够从Chroma数据库检索相关代码片段
   - 检查回答中是否包含相关代码片段
   - 检查回答是否与问题相关

3. 代码问答功能能够提供函数调用关系
   - 检查回答中是否包含调用者和被调用者信息
   - 检查调用关系是否准确

4. 代码问答功能在各种情况下都能正常工作
   - 函数存在且有代码
   - 函数存在但需要从文件读取代码
   - 函数不存在
   - 无上下文信息

## 测试执行计划

| 测试阶段 | 测试内容 | 负责人 | 计划日期 | 前置条件 |
|---------|---------|-------|---------|---------|
| 单元测试 | `test_code_qa_service.py` | 张工 | 2025-06-29 | 代码修改完成 |
| 单元测试 | `test_neo4j_store.py` | 李工 | 2025-06-29 | 代码修改完成 |
| 集成测试 | `test_code_qa_integration.py` | 李工 | 2025-07-01 | 单元测试通过 |
| 手动测试 | `test_qa_functionality.sh` | 王工 | 2025-07-02 | 集成测试通过 |
| 验收测试 | 验证清单 | 产品经理 | 2025-07-03 | 手动测试通过 |

## 测试报告模板

### 单元测试报告

```
# 单元测试报告

## 测试概述
- 测试日期：[日期]
- 测试人员：[姓名]
- 测试模块：[模块名]
- 测试用例总数：[数量]
- 通过用例数：[数量]
- 失败用例数：[数量]

## 测试结果详情
[详细测试结果]

## 问题与修复
[发现的问题及修复情况]

## 结论
[测试结论]
```

### 集成测试报告

```
# 集成测试报告

## 测试概述
- 测试日期：[日期]
- 测试人员：[姓名]
- 测试范围：[描述]
- 测试用例总数：[数量]
- 通过用例数：[数量]
- 失败用例数：[数量]

## 测试结果详情
[详细测试结果]

## 问题与修复
[发现的问题及修复情况]

## 结论
[测试结论]
```

### 验收测试报告

```
# 验收测试报告

## 测试概述
- 测试日期：[日期]
- 测试人员：[姓名]
- 测试范围：[描述]
- 验证项总数：[数量]
- 通过项数：[数量]
- 失败项数：[数量]

## 测试结果详情
[详细测试结果]

## 问题与修复
[发现的问题及修复情况]

## 用户反馈
[用户反馈意见]

## 结论
[测试结论]
```

## 测试覆盖率目标

- **单元测试覆盖率**：>90%
- **集成测试覆盖率**：>80%
- **功能覆盖率**：100%（所有功能点都有测试用例）

## 测试环境准备

1. **测试数据准备**：
   - 创建包含各种C语言函数的测试项目
   - 确保测试项目包含不同类型的函数（简单函数、复杂函数、有调用关系的函数）

2. **环境配置**：
   - 安装Neo4j数据库并配置测试实例
   - 安装Chroma数据库并配置测试实例
   - 配置测试环境变量（API密钥等）

3. **测试工具**：
   - pytest：单元测试和集成测试
   - pytest-cov：测试覆盖率分析
   - pytest-mock：模拟对象

## 测试自动化

1. **CI/CD集成**：
   - 在GitHub Actions中配置自动化测试
   - 每次提交代码时自动运行单元测试
   - 每次合并请求时自动运行集成测试

2. **测试报告生成**：
   - 配置pytest-html生成HTML测试报告
   - 配置pytest-cov生成覆盖率报告

## 结论

本测试计划提供了全面的测试策略和测试用例，覆盖了代码问答功能修复的各个方面。通过执行这些测试，可以确保修复的质量和稳定性，防止回归问题的出现。 