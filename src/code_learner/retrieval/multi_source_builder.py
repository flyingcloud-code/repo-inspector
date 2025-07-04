"""
多源上下文构建器实现

简化版本，遵循KISS原则 - 只做核心功能：并行检索+重排序
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

from ..core.context_models import ContextItem
from ..core.retriever_interfaces import IReranker
from .vector_retriever import VectorContextRetriever
from .graph_retriever import GraphContextRetriever
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class MultiSourceContextBuilder:
    """多源上下文构建器（简化版）
    
    核心功能：
    1. 并行检索（Vector + Graph）
    2. 去重
    3. LLM重排序
    """
    
    def __init__(self, project_id: str, reranker: IReranker):
        """初始化多源构建器"""
        self.config = ConfigManager()
        self.reranker = reranker
        
        # 简单初始化两个检索器，并传入项目ID
        self.vector_retriever = VectorContextRetriever(project_id=project_id)
        self.graph_retriever = GraphContextRetriever(project_id=project_id)
        
        logger.info("MultiSourceContextBuilder initialized (simple version)")
        
    def build_context(self, query: str, intent: Dict[str, Any]) -> List[ContextItem]:
        """构建多源上下文
        
        Args:
            query: 用户查询
            intent: 意图分析结果
            
        Returns:
            List[ContextItem]: 重排序后的上下文项
        """
        all_items = []
        
        # 1. 并行检索
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 提交检索任务
            vector_future = executor.submit(self._safe_retrieve, self.vector_retriever, query, intent)
            graph_future = executor.submit(self._safe_retrieve, self.graph_retriever, query, intent)
            
            # 收集结果
            vector_results = vector_future.result()
            graph_results = graph_future.result()
            
            if vector_results:
                all_items.extend(vector_results)
                logger.info(f"Vector retrieval: {len(vector_results)} items")
            
            if graph_results:
                all_items.extend(graph_results)
                logger.info(f"Graph retrieval: {len(graph_results)} items")
        
        # 2. 去重（简单的内容去重）
        seen_content = set()
        deduplicated_items = []
        for item in all_items:
            if item.content not in seen_content:
                deduplicated_items.append(item)
                seen_content.add(item.content)
        
        # 3. LLM重排序
        config = self.config.get_config()
        final_top_k = config.enhanced_query.final_top_k
        
        if len(deduplicated_items) <= final_top_k:
            reranked_items = deduplicated_items
        else:
            reranked_items = self.reranker.rerank(query, deduplicated_items, final_top_k)
        
        logger.info(f"Context built: {len(all_items)} → {len(deduplicated_items)} → {len(reranked_items)} items")
        
        return reranked_items
    
    def _safe_retrieve(self, retriever, query: str, intent: Dict[str, Any]) -> List[ContextItem]:
        """安全的检索调用"""
        try:
            if not retriever.is_available():
                logger.warning(f"{retriever.__class__.__name__} not available")
                return []
            
            return retriever.retrieve(query, intent)
        except Exception as e:
            logger.error(f"{retriever.__class__.__name__} failed: {e}")
            return [] 