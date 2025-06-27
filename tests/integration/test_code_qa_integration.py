"""
代码问答功能集成测试

测试代码问答功能的端到端流程：
- 函数上下文检索
- 文件上下文检索
- 向量检索
"""
import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import tempfile

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.code_learner.llm.code_qa_service import CodeQAService
from src.code_learner.llm.service_factory import ServiceFactory
from src.code_learner.core.data_models import ChatResponse


class TestCodeQAIntegration:
    """代码问答功能集成测试"""
    
    @pytest.fixture
    def mock_services(self):
        """模拟服务"""
        # 模拟聊天机器人
        mock_chatbot = MagicMock()
        mock_response = ChatResponse(
            content="这是集成测试回答",
            model="test-model",
            usage={"prompt_tokens": 10, "completion_tokens": 20},
            metadata={"response_time": 0.1}
        )
        mock_chatbot.ask_question.return_value = mock_response
        
        # 模拟图存储
        mock_graph_store = MagicMock()
        mock_graph_store.get_function_code.return_value = "int test_function() { return 0; }"
        mock_graph_store.query_function_calls.return_value = ["called_func1", "called_func2"]
        mock_graph_store.query_function_callers.return_value = ["caller_func1", "caller_func2"]
        
        # 模拟服务工厂
        mock_factory = MagicMock()
        mock_factory.get_chatbot.return_value = mock_chatbot
        mock_factory.get_graph_store.return_value = mock_graph_store
        
        return {
            "factory": mock_factory,
            "chatbot": mock_chatbot,
            "graph_store": mock_graph_store
        }
    
    def test_query_with_function_focus(self, mock_services):
        """测试聚焦于函数的问答"""
        # 创建服务
        service = CodeQAService(mock_services["factory"])
        
        # 调用方法
        result = service.ask_question("这个函数是做什么的？", {"focus_function": "test_function"})
        
        # 验证结果
        assert result == "这是集成测试回答"
        
        # 验证图存储调用
        mock_services["graph_store"].get_function_code.assert_called_once_with("test_function")
        mock_services["graph_store"].query_function_calls.assert_called_once_with("test_function")
        mock_services["graph_store"].query_function_callers.assert_called_once_with("test_function")
        
        # 验证聊天机器人调用
        mock_services["chatbot"].ask_question.assert_called_once()
        args, kwargs = mock_services["chatbot"].ask_question.call_args
        assert args[0] == "这个函数是做什么的？"
        context = args[1]  # 上下文作为第二个参数
        assert "函数 'test_function' 的代码" in context
    
    def test_query_with_file_focus(self, mock_services):
        """测试聚焦于文件的问答"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.c') as temp_file:
            temp_file.write("int main() { return 0; }")
            temp_file_path = temp_file.name
        
        try:
            # 创建服务
            service = CodeQAService(mock_services["factory"])
            
            # 调用方法
            result = service.ask_question("这个文件是做什么的？", {"focus_file": temp_file_path})
            
            # 验证结果
            assert result == "这是集成测试回答"
            
            # 验证聊天机器人调用
            mock_services["chatbot"].ask_question.assert_called_once()
            args, kwargs = mock_services["chatbot"].ask_question.call_args
            assert args[0] == "这个文件是做什么的？"
            context = args[1]  # 上下文作为第二个参数
            assert "文件" in context
            assert "int main() { return 0; }" in context
            
        finally:
            # 清理临时文件
            os.unlink(temp_file_path)
    
    def test_interactive_query_session(self, mock_services):
        """测试交互式问答会话"""
        # 创建服务
        service = CodeQAService(mock_services["factory"])
        
        # 第一个问题
        result1 = service.ask_question("这个函数是做什么的？", {"focus_function": "test_function"})
        assert result1 == "这是集成测试回答"
        
        # 第二个问题
        result2 = service.ask_question("这个函数有什么问题？", {"focus_function": "test_function"})
        assert result2 == "这是集成测试回答"
        
        # 验证调用次数
        assert mock_services["chatbot"].ask_question.call_count == 2
        assert mock_services["graph_store"].get_function_code.call_count == 2 