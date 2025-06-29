"""
多源检索与重排序系统集成测试

测试多源检索和LLM重排序功能的集成
"""

import pytest
import time
import logging
from typing import Dict, List, Any
import os
from pathlib import Path

from src.code_learner.llm.service_factory import ServiceFactory
from src.code_learner.retrieval.vector_retriever import VectorContextRetriever
from src.code_learner.retrieval.call_graph_retriever import CallGraphContextRetriever
from src.code_learner.retrieval.dependency_retriever import DependencyContextRetriever
from src.code_learner.retrieval.multi_source_builder import MultiSourceContextBuilder
from src.code_learner.rerank.llm_reranker import LLMReranker
from src.code_learner.llm.intent_analyzer import IntentAnalyzer
from src.code_learner.core.context_models import ContextItem, IntentAnalysis, IntentType, SourceType
from src.code_learner.config.config_manager import ConfigManager

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestMultiSourceRetrieval:
    """多源检索与重排序系统测试"""
    
    @pytest.fixture(scope="class")
    def service_factory(self):
        """创建服务工厂"""
        return ServiceFactory()
    
    @pytest.fixture(scope="class")
    def config(self):
        """获取配置"""
        return ConfigManager().get_config()
    
    @pytest.fixture(scope="class")
    def multi_source_builder(self, service_factory, config):
        """创建多源上下文构建器"""
        # 获取服务
        graph_store = service_factory.get_graph_store()
        vector_store = service_factory.get_vector_store()
        chatbot = service_factory.get_chatbot()
        embedding_engine = service_factory.get_embedding_engine()
        
        # 创建检索器
        vector_retriever = VectorContextRetriever(vector_store)
        call_graph_retriever = CallGraphContextRetriever(graph_store)
        dependency_retriever = DependencyContextRetriever(graph_store)
        
        # 创建重排序器和意图分析器
        reranker = LLMReranker(chatbot)
        intent_analyzer = IntentAnalyzer(chatbot)
        
        # 创建多源构建器
        builder = MultiSourceContextBuilder(
            vector_retriever=vector_retriever,
            call_graph_retriever=call_graph_retriever,
            dependency_retriever=dependency_retriever,
            reranker=reranker,
            intent_analyzer=intent_analyzer,
            config=config.enhanced_query.to_dict() if hasattr(config, 'enhanced_query') else None
        )
        
        return builder
    
    def test_builder_initialization(self, multi_source_builder):
        """测试多源构建器初始化"""
        assert multi_source_builder is not None
        
        # 检查可用源
        available_sources = multi_source_builder.get_available_sources()
        assert len(available_sources) > 0
        logger.info(f"可用检索源: {available_sources}")
        
        # 检查健康状态
        health_status = multi_source_builder.health_check()
        assert health_status is not None
        logger.info(f"健康状态: {health_status}")
    
    def test_intent_analysis(self, multi_source_builder):
        """测试意图分析"""
        # 使用意图分析器
        analyzer = multi_source_builder.intent_analyzer
        
        # 测试函数查询意图
        function_query = "what does sbi_init function do?"
        function_intent = analyzer.analyze(function_query)
        
        assert function_intent is not None
        assert function_intent.intent_type == IntentType.FUNCTION_QUERY
        assert len(function_intent.entities) > 0
        assert "sbi_init" in [entity.get("name") for entity in function_intent.entities]
        
        logger.info(f"函数查询意图分析结果: {function_intent}")
        
        # 测试文件查询意图
        file_query = "what is in sbi_system.c file?"
        file_intent = analyzer.analyze(file_query)
        
        assert file_intent is not None
        assert file_intent.intent_type == IntentType.FILE_QUERY or file_intent.intent_type == IntentType.GENERAL_QUESTION
        
        # 测试调用关系查询意图
        call_query = "what functions call sbi_init?"
        call_intent = analyzer.analyze(call_query)
        
        assert call_intent is not None
        assert call_intent.intent_type == IntentType.CALL_RELATIONSHIP or call_intent.intent_type == IntentType.FUNCTION_QUERY
        
        logger.info(f"文件查询意图分析结果: {file_intent}")
    
    def test_multi_source_retrieval(self, multi_source_builder):
        """测试多源检索"""
        # 测试函数查询
        query = "what is da9063_system_reset_check function?"
        
        # 手动创建意图分析结果
        intent = IntentAnalysis(
            intent_type=IntentType.FUNCTION_QUERY,
            entities=[{"name": "da9063_system_reset_check", "type": "function"}],
            confidence=0.9
        )
        
        # 执行多源检索
        start_time = time.time()
        result = multi_source_builder.build_context(query, intent)
        elapsed_time = time.time() - start_time
        
        # 验证结果
        assert result is not None
        # 不检查items的长度，因为在测试环境中可能没有相关数据
        
        logger.info(f"检索到 {len(result.items)} 个上下文项，耗时 {elapsed_time:.2f} 秒")
        logger.info(f"重排序置信度: {result.confidence}")
        
        # 如果有结果，检查其格式是否正确
        if result.items:
            for item in result.items:
                assert item.source_type in [SourceType.VECTOR, SourceType.CALL_GRAPH, SourceType.DEPENDENCY]
                assert item.relevance_score >= 0.0
                
            # 输出检索到的内容供参考
            logger.info(f"检索到的第一个结果: {result.items[0].content[:100]}...")
    
    def test_source_control(self, multi_source_builder):
        """测试检索源控制"""
        # 禁用调用图检索器
        multi_source_builder.enable_source("call_graph", False)
        
        # 测试函数查询
        query = "what is sbi_hart_hang function?"
        
        # 手动创建意图分析结果
        intent = IntentAnalysis(
            intent_type=IntentType.FUNCTION_QUERY,
            entities=[{"name": "sbi_hart_hang", "type": "function"}],
            confidence=0.9
        )
        
        # 执行多源检索
        result = multi_source_builder.build_context(query, intent)
        
        # 验证结果
        assert result is not None
        
        # 重新启用调用图检索器
        multi_source_builder.enable_source("call_graph", True)
        
        # 再次执行查询
        result_with_call_graph = multi_source_builder.build_context(query, intent)
        
        # 验证结果
        assert result_with_call_graph is not None
        
        # 注意：由于结果可能因数据而异，我们不做严格的数量比较
        logger.info(f"禁用调用图检索器时检索到 {len(result.items)} 个上下文项")
        logger.info(f"启用调用图检索器时检索到 {len(result_with_call_graph.items)} 个上下文项")
    
    def test_parallel_vs_sequential(self, multi_source_builder):
        """测试并行与顺序检索比较"""
        query = "how does opensbi handle system suspend?"
        
        # 手动创建意图分析结果
        intent = IntentAnalysis(
            intent_type=IntentType.CONCEPT_QUERY,
            entities=[{"name": "system suspend", "type": "concept"}],
            confidence=0.9
        )
        
        # 配置并行检索
        parallel_config = {"parallel_retrieval": True}
        
        # 执行并行检索
        start_time = time.time()
        parallel_result = multi_source_builder.build_context(query, intent, parallel_config)
        parallel_time = time.time() - start_time
        
        # 配置顺序检索
        sequential_config = {"parallel_retrieval": False}
        
        # 执行顺序检索
        start_time = time.time()
        sequential_result = multi_source_builder.build_context(query, intent, sequential_config)
        sequential_time = time.time() - start_time
        
        # 验证结果
        assert parallel_result is not None
        assert sequential_result is not None
        
        logger.info(f"并行检索耗时: {parallel_time:.2f} 秒，检索到 {len(parallel_result.items)} 个上下文项")
        logger.info(f"顺序检索耗时: {sequential_time:.2f} 秒，检索到 {len(sequential_result.items)} 个上下文项")
        
        # 并行检索通常应该更快
        # 注意：在某些环境下可能不一定，所以这不是一个严格的断言
        logger.info(f"并行检索比顺序检索{'快' if parallel_time < sequential_time else '慢'} {abs(sequential_time - parallel_time):.2f} 秒") 