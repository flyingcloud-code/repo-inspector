"""
Story 1.4 验收测试

测试向量嵌入和Q&A功能的完整集成
使用真实API，不使用mock - 按用户要求
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from typing import List

from src.code_learner.llm import (
    JinaEmbeddingEngine,
    ChromaVectorStore, 
    OpenRouterChatBot,
    LLMServiceFactory,
    CodeQAService
)
from src.code_learner.core.data_models import Function
from src.code_learner.config.config_manager import ConfigManager


class TestStory14Acceptance:
    """Story 1.4 向量嵌入和Q&A验收测试"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """设置测试环境"""
        # 创建临时目录用于测试
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.temp_dir) / "test_data"
        self.test_data_dir.mkdir(exist_ok=True)
        
        # 检查必要的环境变量
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.openrouter_api_key:
            pytest.skip("需要设置 OPENROUTER_API_KEY 环境变量")
        
        yield
        
        # 清理测试环境
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_functions(self) -> List[Function]:
        """创建测试用的函数对象"""
        return [
            Function(
                name="main",
                file_path="test/main.c",
                start_line=1,
                end_line=10,
                code="""int main() {
    printf("Hello World\\n");
    return 0;
}"""
            ),
            Function(
                name="add_numbers",
                file_path="test/math.c", 
                start_line=5,
                end_line=8,
                code="""int add_numbers(int a, int b) {
    return a + b;
}"""
            ),
            Function(
                name="fibonacci",
                file_path="test/fib.c",
                start_line=1,
                end_line=12,
                code="""int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n-1) + fibonacci(n-2);
}"""
            )
        ]
    
    def test_embedding_engine_real_api(self):
        """测试嵌入引擎 - 真实API"""
        # 创建嵌入引擎
        engine = JinaEmbeddingEngine()
        
        # 加载模型
        success = engine.load_model("jinaai/jina-embeddings-v2-base-code")
        assert success, "嵌入模型加载失败"
        
        # 测试文本编码
        test_text = "int main() { return 0; }"
        embedding = engine.encode_text(test_text)
        
        assert isinstance(embedding, list), "嵌入结果应该是列表"
        assert len(embedding) > 0, "嵌入向量不能为空"
        assert all(isinstance(x, float) for x in embedding), "嵌入向量元素应该是浮点数"
        
        # 测试函数编码
        test_function = self.create_test_functions()[0]
        embedding_data = engine.encode_function(test_function)
        
        assert embedding_data.id is not None, "嵌入数据ID不能为空"
        assert embedding_data.text is not None, "嵌入数据文本不能为空"
        assert len(embedding_data.embedding) > 0, "嵌入向量不能为空"
        assert "function_name" in embedding_data.metadata, "元数据应包含函数名"
        
        # 测试批量编码
        texts = ["int x = 1;", "void func() {}", "return value;"]
        batch_embeddings = engine.encode_batch(texts)
        
        assert len(batch_embeddings) == len(texts), "批量编码结果数量应匹配"
        assert all(len(emb) > 0 for emb in batch_embeddings), "所有嵌入向量都不能为空"
    
    def test_vector_store_real_storage(self):
        """测试向量存储 - 真实存储"""
        # 创建向量存储（使用临时目录）
        chroma_dir = self.test_data_dir / "chroma"
        store = ChromaVectorStore(persist_directory=str(chroma_dir))
        
        # 创建集合
        collection_name = "test_collection"
        success = store.create_collection(collection_name)
        assert success, "集合创建失败"
        
        # 准备测试数据
        engine = JinaEmbeddingEngine()
        engine.load_model("jinaai/jina-embeddings-v2-base-code")
        
        test_functions = self.create_test_functions()
        embedding_data_list = []
        
        for func in test_functions:
            embedding_data = engine.encode_function(func)
            embedding_data_list.append(embedding_data)
        
        # 添加嵌入数据
        success = store.add_embeddings(embedding_data_list)
        assert success, "嵌入数据添加失败"
        
        # 测试搜索
        query_text = "main function that prints hello"
        query_vector = engine.encode_text(query_text)
        
        results = store.search_similar(query_vector, top_k=2, collection_name=collection_name)
        
        assert len(results) > 0, "搜索应该返回结果"
        assert all("similarity" in result for result in results), "结果应包含相似度"
        assert all(result["similarity"] >= 0 for result in results), "相似度应该非负"
        
        # 验证持久化存储
        assert chroma_dir.exists(), "Chroma存储目录应该存在"
        
        # 测试集合信息
        info = store.get_collection_info(collection_name)
        assert info["count"] == len(test_functions), f"集合应包含 {len(test_functions)} 个向量"
    
    def test_chatbot_real_api(self):
        """测试聊天机器人 - 真实API"""
        # 创建聊天机器人
        chatbot = OpenRouterChatBot(self.openrouter_api_key)
        
        # 初始化聊天机器人
        success = chatbot.initialize(self.openrouter_api_key, "google/gemini-2.0-flash-001")
        assert success, "聊天机器人初始化失败"
        
        # 测试问答功能
        question = "这个C语言函数做什么？"
        context = "int add(int a, int b) { return a + b; }"
        
        response = chatbot.ask_question(question, context)
        
        assert response.content is not None, "回答内容不能为空"
        assert len(response.content) > 0, "回答内容不能为空字符串"
        assert response.model is not None, "响应应包含模型信息"
        assert "usage" in response.__dict__, "响应应包含使用统计"
        
        # 测试代码摘要功能 - 用户明确要求的功能
        code_content = """
        int fibonacci(int n) {
            if (n <= 1) return n;
            return fibonacci(n-1) + fibonacci(n-2);
        }
        """
        
        summary_response = chatbot.generate_summary(code_content, "test_fib.c")
        
        assert summary_response.content is not None, "摘要内容不能为空"
        assert len(summary_response.content) > 0, "摘要内容不能为空字符串"
        assert "fibonacci" in summary_response.content.lower() or "斐波那契" in summary_response.content, "摘要应该包含函数相关内容"
    
    def test_service_factory_real_services(self):
        """测试服务工厂 - 真实服务"""
        # 创建配置管理器
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # 设置临时配置
        config.vector_store.chroma_persist_directory = str(self.test_data_dir / "chroma")
        
        # 创建服务工厂
        factory = LLMServiceFactory(config_manager)
        
        # 测试创建所有服务
        services = factory.create_all_services()
        
        assert "embedding_engine" in services, "应该包含嵌入引擎"
        assert "vector_store" in services, "应该包含向量存储"
        assert "chatbot" in services, "应该包含聊天机器人"
        
        # 验证服务可用性
        embedding_engine = services["embedding_engine"]
        assert hasattr(embedding_engine, "encode_text"), "嵌入引擎应有encode_text方法"
        
        vector_store = services["vector_store"]
        assert hasattr(vector_store, "search_similar"), "向量存储应有search_similar方法"
        
        chatbot = services["chatbot"]
        assert hasattr(chatbot, "ask_question"), "聊天机器人应有ask_question方法"
        assert hasattr(chatbot, "generate_summary"), "聊天机器人应有generate_summary方法"
        
        # 测试服务状态
        status = factory.get_services_status()
        assert all(service_status.get("status") != "not_created" for service_status in status.values()), "所有服务都应该已创建"
    
    def test_code_qa_service_integration(self):
        """测试代码问答服务集成 - 端到端测试"""
        # 创建配置管理器
        config_manager = ConfigManager()
        config = config_manager.get_config()
        config.vector_store.chroma_persist_directory = str(self.test_data_dir / "chroma")
        
        # 创建代码问答服务
        qa_service = CodeQAService(LLMServiceFactory(config_manager))
        
        # 测试服务可用性（延迟加载）
        assert qa_service.embedding_engine is not None, "嵌入引擎应该可用"
        assert qa_service.vector_store is not None, "向量存储应该可用"
        assert qa_service.chatbot is not None, "聊天机器人应该可用"
        
        # 测试代码问答功能
        question = "如何实现一个简单的加法函数？"
        answer = qa_service.ask_code_question(question)
        
        assert isinstance(answer, str), "回答应该是字符串"
        assert len(answer) > 0, "回答不能为空"
        
        # 测试代码摘要功能 - 用户明确要求的功能
        code_content = """
        #include <stdio.h>
        
        int main() {
            printf("Hello, World!\\n");
            return 0;
        }
        """
        
        summary = qa_service.generate_code_summary(code_content, "hello.c")
        
        assert isinstance(summary, str), "摘要应该是字符串"
        assert len(summary) > 0, "摘要不能为空"
        assert "main" in summary.lower() or "hello" in summary.lower(), "摘要应该包含相关内容"
    
    def test_repo_level_processing_capability(self):
        """测试repo级别处理能力"""
        # 创建更多测试函数模拟repo级别
        test_functions = []
        
        # 模拟OpenSBI项目的一些函数
        opensbi_functions = [
            ("sbi_init", "lib/sbi/sbi_init.c", "void sbi_init(struct sbi_scratch *scratch) { /* init code */ }"),
            ("sbi_trap_handler", "lib/sbi/sbi_trap.c", "int sbi_trap_handler(struct sbi_trap_regs *regs) { /* trap handling */ }"),
            ("sbi_console_putc", "lib/sbi/sbi_console.c", "void sbi_console_putc(char ch) { /* console output */ }"),
            ("sbi_timer_init", "lib/sbi/sbi_timer.c", "int sbi_timer_init() { /* timer initialization */ }"),
            ("sbi_ipi_send", "lib/sbi/sbi_ipi.c", "int sbi_ipi_send(u32 target_cpu) { /* send IPI */ }")
        ]
        
        for i, (name, file_path, code) in enumerate(opensbi_functions):
            func = Function(
                name=name,
                file_path=file_path,
                start_line=i * 10 + 1,
                end_line=i * 10 + 5,
                code=code
            )
            test_functions.append(func)
        
        # 测试批量处理能力
        config_manager = ConfigManager()
        config = config_manager.get_config()
        config.vector_store.chroma_persist_directory = str(self.test_data_dir / "chroma_repo")
        
        qa_service = CodeQAService(LLMServiceFactory(config_manager))
        
        # 测试批量编码（模拟repo级别处理）
        texts = [func.code for func in test_functions]
        embeddings = qa_service.embedding_engine.encode_batch(texts)
        
        assert len(embeddings) == len(test_functions), "批量编码结果数量应匹配"
        assert all(len(emb) > 0 for emb in embeddings), "所有嵌入向量都不能为空"
        
        # 验证性能要求：批量处理应该在合理时间内完成
        # 注意：这里不设置严格的时间限制，因为网络和模型加载时间可能变化
        
        print(f"✅ 成功处理 {len(test_functions)} 个函数的批量嵌入")
        print(f"📊 嵌入维度: {len(embeddings[0]) if embeddings else 0}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 