"""
LLM重排序功能集成测试

测试LLM重排序器的功能和性能
"""

import pytest
import time
import logging
from typing import Dict, List, Any
import os
from pathlib import Path

from src.code_learner.llm.service_factory import ServiceFactory
from src.code_learner.rerank.llm_reranker import LLMReranker
from src.code_learner.core.context_models import ContextItem, RerankResult

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLLMReranker:
    """LLM重排序器集成测试"""
    
    @pytest.fixture(scope="class")
    def service_factory(self):
        """创建服务工厂"""
        return ServiceFactory()
    
    @pytest.fixture(scope="class")
    def reranker(self, service_factory):
        """创建LLM重排序器"""
        chatbot = service_factory.get_chatbot()
        return LLMReranker(chatbot)
    
    @pytest.fixture
    def mock_context_items(self):
        """创建模拟的上下文项"""
        items = [
            ContextItem(
                content="""
                void sbi_system_suspend_set_device(struct sbi_scratch *scratch,
                                                void *suspend_fw_base)
                {
                    struct sbi_system_suspend_device *suspend_dev;

                    suspend_dev = sbi_scratch_offset_ptr(scratch, suspend_dev_offset);
                    suspend_dev->suspend_fw_base = suspend_fw_base;
                }
                """,
                source_type="call_graph",
                relevance_score=0.85,
                metadata={
                    "type": "function", 
                    "name": "sbi_system_suspend_set_device",
                    "file_path": "lib/sbi/sbi_system.c"
                }
            ),
            ContextItem(
                content="""
                int sbi_system_suspend_handler(struct sbi_scratch *scratch,
                                            u32 remote_hart_id,
                                            u64 suspend_type, u64 resume_addr,
                                            u64 opaque)
                {
                    struct sbi_system_suspend_device *suspend_dev;
                    void (*suspend_fw_func)(u32 hartid, u64 suspend_type,
                                        u64 resume_addr, u64 opaque) = NULL;

                    suspend_dev = sbi_scratch_offset_ptr(scratch, suspend_dev_offset);
                    if (!suspend_dev || !suspend_dev->suspend_fw_base)
                        return SBI_ENODEV;
                    
                    suspend_fw_func = suspend_dev->suspend_fw_base;
                    suspend_fw_func(remote_hart_id, suspend_type, resume_addr, opaque);
                    
                    return 0;
                }
                """,
                source_type="call_graph",
                relevance_score=0.75,
                metadata={
                    "type": "function", 
                    "name": "sbi_system_suspend_handler",
                    "file_path": "lib/sbi/sbi_system.c"
                }
            ),
            ContextItem(
                content="""
                void sbi_system_suspend_init(struct sbi_scratch *scratch,
                                        void *suspend_fw_base)
                {
                    /* Initialize suspend device */
                    sbi_system_suspend_set_device(scratch, suspend_fw_base);
                }
                """,
                source_type="call_graph",
                relevance_score=0.65,
                metadata={
                    "type": "function", 
                    "name": "sbi_system_suspend_init",
                    "file_path": "lib/sbi/sbi_system.c"
                }
            ),
            ContextItem(
                content="""
                # OpenSBI Suspend/Resume功能

                OpenSBI提供了系统挂起和恢复功能，主要通过以下函数实现：

                - sbi_system_suspend_set_device：设置挂起设备
                - sbi_system_suspend_handler：处理挂起请求
                - sbi_system_suspend_init：初始化挂起功能

                这些函数位于lib/sbi/sbi_system.c文件中。
                """,
                source_type="vector",
                relevance_score=0.60,
                metadata={
                    "type": "document", 
                    "name": "suspend.md",
                    "file_path": "docs/suspend.md"
                }
            ),
            ContextItem(
                content="""
                struct sbi_system_suspend_device {
                    void *suspend_fw_base;
                };
                """,
                source_type="vector",
                relevance_score=0.55,
                metadata={
                    "type": "struct", 
                    "name": "sbi_system_suspend_device",
                    "file_path": "include/sbi/sbi_system.h"
                }
            ),
        ]
        return items
    
    def test_reranker_initialization(self, reranker):
        """测试重排序器初始化"""
        assert reranker is not None
        assert reranker.is_available()
    
    def test_basic_reranking(self, reranker, mock_context_items):
        """测试基本重排序功能"""
        query = "what is sbi_system_suspend_set_device function?"
        
        # 执行重排序
        start_time = time.time()
        result = reranker.rerank(query, mock_context_items, top_k=3)
        elapsed_time = time.time() - start_time
        
        # 验证结果
        assert result is not None
        assert isinstance(result, RerankResult)
        assert len(result.items) == 3  # 应该返回top_k=3个结果
        assert result.original_count == len(mock_context_items)
        assert result.rerank_time > 0
        
        logger.info(f"重排序耗时: {elapsed_time:.2f} 秒")
        logger.info(f"重排序置信度: {result.confidence}")
        
        # 验证第一个结果应该包含查询的函数名
        assert "sbi_system_suspend_set_device" in result.items[0].content
    
    def test_top_k_limit(self, reranker, mock_context_items):
        """测试top_k限制"""
        query = "what is system suspend in OpenSBI?"
        
        # 使用不同的top_k值
        top_k_values = [1, 2, 3, 5]
        
        for top_k in top_k_values:
            result = reranker.rerank(query, mock_context_items, top_k=top_k)
            
            # 验证结果数量
            assert len(result.items) == min(top_k, len(mock_context_items))
            logger.info(f"top_k={top_k}, 返回 {len(result.items)} 个结果")
    
    def test_empty_context(self, reranker):
        """测试空上下文处理"""
        query = "what is sbi_system_suspend_set_device?"
        empty_items = []
        
        # 执行重排序
        result = reranker.rerank(query, empty_items)
        
        # 验证结果
        assert result is not None
        assert len(result.items) == 0
        assert result.original_count == 0
    
    def test_single_item_context(self, reranker, mock_context_items):
        """测试单个项目的上下文处理"""
        query = "what is sbi_system_suspend_set_device?"
        single_item = [mock_context_items[0]]
        
        # 执行重排序
        result = reranker.rerank(query, single_item)
        
        # 验证结果
        assert result is not None
        assert len(result.items) == 1
        assert result.original_count == 1
        assert result.confidence == 1.0  # 单个项目应该有最高置信度
    
    def test_prompt_templates(self, reranker, mock_context_items):
        """测试不同的prompt模板"""
        query = "what is sbi_system_suspend_set_device function?"
        
        # 测试默认模板
        reranker.set_prompt_template("default")
        default_result = reranker.rerank(query, mock_context_items, top_k=3)
        
        # 测试函数分析模板
        reranker.set_prompt_template("function_analysis")
        function_result = reranker.rerank(query, mock_context_items, top_k=3)
        
        # 验证结果
        assert default_result is not None
        assert function_result is not None
        
        logger.info(f"默认模板返回 {len(default_result.items)} 个结果")
        logger.info(f"函数分析模板返回 {len(function_result.items)} 个结果")
        
        # 重置为默认模板
        reranker.set_prompt_template("default") 