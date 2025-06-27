"""
测试代码问答服务

验证代码问答服务的功能：
- 问题回答
- 代码摘要生成
- 函数上下文检索
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from typing import Dict, Any, Optional
import tempfile

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.code_learner.llm.code_qa_service import CodeQAService
from src.code_learner.core.data_models import ChatResponse
from src.code_learner.core.exceptions import ServiceError


class TestCodeQAService:
    """测试代码问答服务"""

    @pytest.fixture
    def mock_service_factory(self):
        """模拟服务工厂"""
        mock_factory = Mock()
        
        # 模拟聊天机器人
        mock_chatbot = Mock()
        mock_response = ChatResponse(
            content="这是测试回答",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            metadata={"response_time": 0.1}
        )
        mock_chatbot.ask_question.return_value = mock_response
        mock_chatbot.generate_summary.return_value = mock_response
        mock_factory.get_chatbot.return_value = mock_chatbot
        
        # 模拟图存储
        mock_graph_store = Mock()
        mock_graph_store.get_function_code.return_value = "int test_function() { return 0; }"
        mock_graph_store.query_function_calls.return_value = ["called_func1", "called_func2"]
        mock_graph_store.query_function_callers.return_value = ["caller_func1", "caller_func2"]
        mock_factory.get_graph_store.return_value = mock_graph_store
        
        # 模拟向量存储
        mock_vector_store = Mock()
        mock_factory.create_vector_store.return_value = mock_vector_store
        
        # 模拟嵌入引擎
        mock_embedding_engine = Mock()
        mock_factory.get_embedding_engine.return_value = mock_embedding_engine
        
        return mock_factory

    def test_ask_question_without_context(self, mock_service_factory):
        """测试无上下文问答"""
        # 创建服务
        service = CodeQAService(mock_service_factory)
        
        # 调用方法
        result = service.ask_question("这是一个测试问题")
        
        # 验证结果
        assert result == "这是测试回答"
        mock_service_factory.get_chatbot.return_value.ask_question.assert_called_once()
        args, kwargs = mock_service_factory.get_chatbot.return_value.ask_question.call_args
        assert args[0] == "这是一个测试问题"
        assert args[1] == ""  # 空上下文

    def test_ask_question_with_function_context(self, mock_service_factory):
        """测试带函数上下文问答"""
        # 创建服务
        service = CodeQAService(mock_service_factory)
        
        # 调用方法
        result = service.ask_question("这是一个测试问题", {"focus_function": "test_function"})
        
        # 验证结果
        assert result == "这是测试回答"
        
        # 验证图存储调用
        mock_service_factory.get_graph_store.return_value.get_function_code.assert_called_once_with("test_function")
        mock_service_factory.get_graph_store.return_value.query_function_calls.assert_called_once_with("test_function")
        mock_service_factory.get_graph_store.return_value.query_function_callers.assert_called_once_with("test_function")
        
        # 验证聊天机器人调用
        mock_service_factory.get_chatbot.return_value.ask_question.assert_called_once()
        args, kwargs = mock_service_factory.get_chatbot.return_value.ask_question.call_args
        assert args[0] == "这是一个测试问题"
        context = args[1]  # 上下文作为第二个参数
        assert "函数 'test_function' 的代码" in context
        assert "int test_function() { return 0; }" in context
        assert "调用 'test_function' 的函数" in context
        assert "'test_function' 调用的函数" in context

    def test_ask_question_with_file_context(self, mock_service_factory):
        """测试带文件上下文问答"""
        # 创建服务
        service = CodeQAService(mock_service_factory)
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.c') as temp_file:
            temp_file.write("int main() { return 0; }")
            temp_file_path = temp_file.name
        
        try:
            # 调用方法
            result = service.ask_question("这是一个测试问题", {"focus_file": temp_file_path})
            
            # 验证结果
            assert result == "这是测试回答"
            
            # 验证聊天机器人调用
            mock_service_factory.get_chatbot.return_value.ask_question.assert_called_once()
            args, kwargs = mock_service_factory.get_chatbot.return_value.ask_question.call_args
            assert args[0] == "这是一个测试问题"
            context = args[1]  # 上下文作为第二个参数
            assert "文件" in context
            assert "int main() { return 0; }" in context
            
        finally:
            # 清理临时文件
            os.unlink(temp_file_path)

    def test_ask_question_with_invalid_function(self, mock_service_factory):
        """测试无效函数名问答"""
        # 创建服务
        service = CodeQAService(mock_service_factory)
        
        # 模拟函数不存在
        mock_service_factory.get_graph_store.return_value.get_function_code.return_value = None
        # 确保调用关系也为空
        mock_service_factory.get_graph_store.return_value.query_function_calls.return_value = []
        mock_service_factory.get_graph_store.return_value.query_function_callers.return_value = []
        
        # 调用方法
        result = service.ask_question("这是一个测试问题", {"focus_function": "nonexistent_function"})
        
        # 验证结果
        assert result == "这是测试回答"
        
        # 验证图存储调用
        mock_service_factory.get_graph_store.return_value.get_function_code.assert_called_once_with("nonexistent_function")
        
        # 验证聊天机器人调用
        mock_service_factory.get_chatbot.return_value.ask_question.assert_called_once()
        args, kwargs = mock_service_factory.get_chatbot.return_value.ask_question.call_args
        assert args[0] == "这是一个测试问题"
        # 当函数不存在时，上下文应该为空
        assert args[1] == "" or args[1].strip() == ""

    def test_ask_question_error_handling(self, mock_service_factory):
        """测试错误处理"""
        # 创建服务
        service = CodeQAService(mock_service_factory)
        
        # 模拟异常
        mock_service_factory.get_chatbot.return_value.ask_question.side_effect = Exception("测试异常")
        
        # 验证异常处理
        with pytest.raises(ServiceError) as excinfo:
            service.ask_question("这是一个测试问题")
        
        assert "Failed to answer question" in str(excinfo.value)

    def test_generate_code_summary(self, mock_service_factory):
        """测试代码摘要生成"""
        # 创建服务
        service = CodeQAService(mock_service_factory)
        
        # 调用方法
        result = service.generate_code_summary("int test() { return 0; }")
        
        # 验证结果
        assert result == "这是测试回答"
        mock_service_factory.get_chatbot.return_value.generate_summary.assert_called_once()


def mock_open(read_data=""):
    """模拟文件打开操作"""
    mock = MagicMock(spec=open)
    handle = MagicMock()
    handle.__enter__.return_value.read.return_value = read_data
    handle.__enter__.return_value.readlines.return_value = read_data.splitlines(True)
    mock.return_value = handle
    return mock 