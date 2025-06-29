"""
增强查询配置集成测试

测试EnhancedQueryConfig配置功能
"""

import pytest
import logging
from typing import Dict, Any
import os
from pathlib import Path

from src.code_learner.config.config_manager import ConfigManager
from src.code_learner.core.data_models import EnhancedQueryConfig
from src.code_learner.llm.service_factory import ServiceFactory

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEnhancedQueryConfig:
    """增强查询配置测试"""
    
    @pytest.fixture(scope="class")
    def config_manager(self):
        """创建配置管理器"""
        return ConfigManager()
    
    @pytest.fixture(scope="class")
    def service_factory(self):
        """创建服务工厂"""
        return ServiceFactory()
    
    def test_enhanced_query_config_exists(self, config_manager):
        """测试增强查询配置是否存在"""
        config = config_manager.get_config()
        
        # 验证配置存在
        assert hasattr(config, 'enhanced_query')
        assert isinstance(config.enhanced_query, EnhancedQueryConfig)
        
        logger.info(f"增强查询配置: {config.enhanced_query}")
    
    def test_enhanced_query_config_values(self, config_manager):
        """测试增强查询配置的值"""
        config = config_manager.get_config()
        enhanced_query = config.enhanced_query
        
        # 验证基本配置
        assert hasattr(enhanced_query, 'final_top_k')
        assert isinstance(enhanced_query.final_top_k, int)
        assert enhanced_query.final_top_k > 0
        
        assert hasattr(enhanced_query, 'parallel_retrieval')
        assert isinstance(enhanced_query.parallel_retrieval, bool)
        
        assert hasattr(enhanced_query, 'timeout_seconds')
        assert isinstance(enhanced_query.timeout_seconds, int)
        assert enhanced_query.timeout_seconds > 0
        
        # 验证源配置
        assert hasattr(enhanced_query, 'sources')
        assert isinstance(enhanced_query.sources, dict)
        
        # 验证每个源的配置
        for source_name, source_config in enhanced_query.sources.items():
            assert 'enable' in source_config
            assert isinstance(source_config['enable'], bool)
            
            assert 'top_k' in source_config
            assert isinstance(source_config['top_k'], int)
            assert source_config['top_k'] > 0
            
            assert 'min_relevance_score' in source_config
            assert isinstance(source_config['min_relevance_score'], float)
            assert 0.0 <= source_config['min_relevance_score'] <= 1.0
    
    def test_enhanced_query_config_to_dict(self, config_manager):
        """测试增强查询配置的to_dict方法"""
        config = config_manager.get_config()
        enhanced_query = config.enhanced_query
        
        # 转换为字典
        config_dict = enhanced_query.to_dict()
        
        # 验证字典结构
        assert isinstance(config_dict, dict)
        assert 'final_top_k' in config_dict
        assert 'parallel_retrieval' in config_dict
        assert 'timeout_seconds' in config_dict
        assert 'sources' in config_dict
        
        # 验证源配置
        for source_name, source_config in config_dict['sources'].items():
            assert 'enable' in source_config
            assert 'top_k' in source_config
            assert 'min_relevance_score' in source_config
    
    def test_enhanced_query_config_from_dict(self):
        """测试从字典创建增强查询配置"""
        # 创建测试配置字典
        test_config = {
            'final_top_k': 7,
            'parallel_retrieval': True,
            'timeout_seconds': 45,
            'sources': {
                'vector': {
                    'enable': True,
                    'top_k': 10,
                    'min_relevance_score': 0.5
                },
                'call_graph': {
                    'enable': False,
                    'top_k': 5,
                    'min_relevance_score': 0.7
                }
            }
        }
        
        # 从字典创建配置
        enhanced_query = EnhancedQueryConfig.from_dict(test_config)
        
        # 验证配置值
        assert enhanced_query.final_top_k == 7
        assert enhanced_query.parallel_retrieval is True
        assert enhanced_query.timeout_seconds == 45
        
        # 验证源配置
        assert 'vector' in enhanced_query.sources
        assert enhanced_query.sources['vector']['enable'] is True
        assert enhanced_query.sources['vector']['top_k'] == 10
        assert enhanced_query.sources['vector']['min_relevance_score'] == 0.5
        
        assert 'call_graph' in enhanced_query.sources
        assert enhanced_query.sources['call_graph']['enable'] is False
    
    def test_enhanced_query_config_default_values(self):
        """测试增强查询配置的默认值"""
        # 创建空配置
        enhanced_query = EnhancedQueryConfig()
        
        # 验证默认值
        assert enhanced_query.final_top_k == 5  # 默认值应为5
        assert enhanced_query.parallel_retrieval is True  # 默认应为True
        assert enhanced_query.timeout_seconds == 30  # 默认应为30秒
        
        # 验证默认源配置
        assert 'vector' in enhanced_query.sources
        assert 'call_graph' in enhanced_query.sources
        assert 'dependency' in enhanced_query.sources
        
        # 验证每个源的默认配置
        for source_name, source_config in enhanced_query.sources.items():
            assert source_config['enable'] is True
            assert source_config['top_k'] == 5
            assert source_config['min_relevance_score'] == 0.0
    
    def test_multi_source_builder_uses_config(self, service_factory, config_manager):
        """测试多源构建器使用配置"""
        from src.code_learner.retrieval.multi_source_builder import MultiSourceContextBuilder
        
        config = config_manager.get_config()
        
        # 获取服务 - 仅获取图存储，避免向量存储错误
        graph_store = service_factory.get_graph_store()
        
        # 创建检索器 - 仅创建图相关检索器
        from src.code_learner.retrieval.call_graph_retriever import CallGraphContextRetriever
        from src.code_learner.retrieval.dependency_retriever import DependencyContextRetriever
        from src.code_learner.rerank.llm_reranker import LLMReranker
        from src.code_learner.llm.intent_analyzer import IntentAnalyzer
        
        # 模拟向量检索器
        class MockVectorRetriever:
            def __init__(self):
                pass
                
            def get_source_type(self):
                return "vector"
                
            def is_available(self):
                return False
                
            def retrieve(self, *args, **kwargs):
                return None
        
        # 获取其他服务
        chatbot = service_factory.get_chatbot()
        
        # 创建检索器
        vector_retriever = MockVectorRetriever()
        call_graph_retriever = CallGraphContextRetriever(graph_store)
        dependency_retriever = DependencyContextRetriever(graph_store)
        reranker = LLMReranker(chatbot)
        intent_analyzer = IntentAnalyzer(chatbot)
        
        # 使用配置创建多源构建器
        builder = MultiSourceContextBuilder(
            vector_retriever=vector_retriever,
            call_graph_retriever=call_graph_retriever,
            dependency_retriever=dependency_retriever,
            reranker=reranker,
            intent_analyzer=intent_analyzer,
            config=config.enhanced_query.to_dict()
        )
        
        # 验证构建器配置
        assert builder.config is not None
        assert 'final_top_k' in builder.config
        assert 'sources' in builder.config
        
        # 验证源配置
        for source_name in ['vector', 'call_graph', 'dependency']:
            assert source_name in builder.config['sources']
            
        logger.info(f"多源构建器配置: {builder.config}")
        
        # 获取构建器统计信息
        stats = builder.get_statistics()
        assert stats is not None
        assert 'config' in stats
        
        logger.info(f"多源构建器统计信息: {stats}") 