"""
向量检索集成测试

测试代码嵌入和向量检索的端到端流程：
- 代码分块
- 嵌入生成
- 向量存储
- 相似度搜索
- 代码问答服务集成
"""
import pytest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.code_learner.llm.code_chunker import CodeChunker
from src.code_learner.llm.code_embedder import CodeEmbedder
from src.code_learner.llm.embedding_engine import JinaEmbeddingEngine
from src.code_learner.llm.vector_store import ChromaVectorStore
from src.code_learner.llm.code_qa_service import CodeQAService
from src.code_learner.llm.service_factory import ServiceFactory
from src.code_learner.core.data_models import ChatResponse


class TestVectorSearchIntegration:
    """向量检索集成测试"""
    
    @pytest.fixture
    def temp_code_file(self):
        """创建临时代码文件"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.c') as temp_file:
            temp_file.write("""
            /**
             * 计算斐波那契数列
             * 
             * 使用递归方法计算斐波那契数列的第n个数
             */
            int fibonacci(int n) {
                if (n <= 1) {
                    return n;
                }
                return fibonacci(n - 1) + fibonacci(n - 2);
            }
            
            /**
             * 计算阶乘
             * 
             * 使用递归方法计算n的阶乘
             */
            int factorial(int n) {
                if (n <= 1) {
                    return 1;
                }
                return n * factorial(n - 1);
            }
            """)
            temp_file_path = temp_file.name
        
        yield temp_file_path
        
        # 清理临时文件
        os.unlink(temp_file_path)
    
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
        
        # 模拟服务工厂
        mock_factory = MagicMock()
        mock_factory.get_chatbot.return_value = mock_chatbot
        mock_factory.get_graph_store.return_value = mock_graph_store
        
        return {
            "factory": mock_factory,
            "chatbot": mock_chatbot,
            "graph_store": mock_graph_store
        }
    
    @pytest.fixture
    def embedded_file(self, temp_code_file):
        """嵌入临时文件"""
        # 创建嵌入器
        embedder = CodeEmbedder(
            batch_size=10,
            collection_name="test_integration_embeddings"
        )
        
        # 处理文件
        success = embedder.process_file(temp_code_file, force_update=True)
        
        if not success:
            pytest.skip("嵌入文件失败，跳过测试")
        
        return temp_code_file
    
    def test_code_chunking(self, temp_code_file):
        """测试代码分块"""
        # 创建分块器
        chunker = CodeChunker()
        
        # 分块
        chunks = chunker.chunk_file(temp_code_file)
        
        # 验证结果
        assert len(chunks) > 0
        assert any(chunk.function_name == "fibonacci" for chunk in chunks)
        assert any(chunk.function_name == "factorial" for chunk in chunks)
    
    def test_vector_search(self, embedded_file):
        """测试向量搜索"""
        # 创建嵌入引擎
        embedding_engine = JinaEmbeddingEngine()
        
        # 创建向量存储
        vector_store = ChromaVectorStore()
        
        # 生成查询向量
        query = "如何计算斐波那契数列"
        query_vector = embedding_engine.encode_text(query)
        
        # 搜索
        results = vector_store.search_similar(
            query_vector=query_vector,
            top_k=2,
            collection_name="test_integration_embeddings"
        )
        
        # 验证结果
        assert len(results) > 0
        # 第一个结果应该与斐波那契相关
        assert "fibonacci" in results[0]["document"].lower()
    
    @patch('src.code_learner.llm.code_qa_service.JinaEmbeddingEngine')
    def test_qa_service_with_vector_search(self, mock_embedding_engine, mock_services, embedded_file):
        """测试代码问答服务与向量检索集成"""
        # 设置模拟嵌入引擎
        mock_engine_instance = MagicMock()
        mock_embedding_engine.return_value = mock_engine_instance
        mock_engine_instance.encode_text.return_value = [0.1] * 768  # 模拟嵌入向量
        
        # 创建向量存储
        vector_store = ChromaVectorStore()
        mock_services["factory"].get_vector_store.return_value = vector_store
        
        # 创建代码问答服务
        service = CodeQAService(mock_services["factory"])
        service.embedding_engine = mock_engine_instance
        service.vector_store = vector_store
        
        # 调用方法
        question = "如何计算斐波那契数列"
        result = service.ask_question(question)
        
        # 验证结果
        assert result == "这是集成测试回答"
        
        # 验证聊天机器人调用
        mock_services["chatbot"].ask_question.assert_called_once()
        args, kwargs = mock_services["chatbot"].ask_question.call_args
        assert args[0] == question
        context = args[1]  # 上下文作为第二个参数
        
        # 上下文应该包含向量检索结果
        assert "相关代码片段" in context 