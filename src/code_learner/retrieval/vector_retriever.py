"""
向量检索器实现

基于Chroma向量数据库的语义相似度检索。
"""

import time
import logging
from typing import List, Dict, Any, Optional
from ..core.context_models import (
    ContextItem, 
    IntentAnalysis, 
    RetrievalConfig, 
    RetrievalResult,
    SourceType
)
from ..core.retriever_interfaces import IContextRetriever
from ..storage.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class VectorContextRetriever(IContextRetriever):
    """向量检索器
    
    使用向量数据库检索相似代码片段
    """
    
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embedding_engine: Any | None = None,
    ):
        """初始化向量检索器
        
        Args:
            vector_store: 向量存储实例
            embedding_engine: （可选）嵌入引擎实例；若为空可后续通过
                :py:meth:`configure_embedding_engine` 注入，保持向后兼容。
        """
        self.vector_store = vector_store
        self.embedding_engine = embedding_engine
        self.source_type = SourceType.VECTOR
        logger.info(
            "向量检索器初始化完成"
            + (
                f"，已注入嵌入引擎: {type(embedding_engine).__name__}"
                if embedding_engine
                else "，尚未配置嵌入引擎"
            )
        )
        
    def configure_embedding_engine(self, embedding_engine: Any) -> None:
        """配置嵌入引擎
        
        Args:
            embedding_engine: 嵌入引擎实例
        """
        self.embedding_engine = embedding_engine
        logger.info(f"向量检索器配置了嵌入引擎: {type(embedding_engine).__name__}")
    
    def retrieve(
        self, 
        query: str, 
        intent_analysis: IntentAnalysis, 
        config: RetrievalConfig
    ) -> RetrievalResult:
        """检索相似的代码片段
        
        Args:
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 检索配置
            
        Returns:
            检索结果
        """
        if not self.is_available():
            logger.warning(f"Vector store not available: {self.vector_store}")
            return RetrievalResult(
                items=[],
                source_type=self.source_type,
                query_time=0.0,
                total_candidates=0
            )
        
        start_time = time.time()
        
        try:
            # 如果有意图分析结果，使用多查询策略
            if intent_analysis and intent_analysis.keywords:
                context_items = self._multi_query_strategy(query, intent_analysis, config)
            else:
                # 否则使用单一查询
                context_items = self._single_query_strategy(query, config)
            
            query_time = time.time() - start_time
            
            logger.info(f"Vector retrieval completed: {len(context_items)} items in {query_time:.3f}s")
            
            return RetrievalResult(
                items=context_items,
                source_type=self.source_type,
                query_time=query_time,
                total_candidates=len(context_items)
            )
            
        except Exception as e:
            logger.error(f"Vector retrieval failed: {e}")
            return RetrievalResult(
                items=[],
                source_type=self.source_type,
                query_time=time.time() - start_time,
                total_candidates=0
            )
    
    def _single_query_strategy(self, query: str, config: RetrievalConfig) -> List[ContextItem]:
        """单一查询策略
        
        直接使用用户查询进行检索
        
        Args:
            query: 用户查询
            config: 检索配置
            
        Returns:
            上下文项列表
        """
        logger.info(f"执行单一查询策略: {query}")
        
        # 直接调用向量存储的相似度搜索
        results = self.vector_store.similarity_search(
            query=query,
            top_k=config.top_k,
            embedding_engine=self.embedding_engine
        )
        
        # 转换为ContextItem
        return self._process_search_results(results, config.min_relevance_score)
    
    def _multi_query_strategy(self, query: str, intent_analysis: IntentAnalysis, config: RetrievalConfig) -> List[ContextItem]:
        """多查询策略
        
        根据意图分析结果构建多个查询
        
        Args:
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 检索配置
            
        Returns:
            上下文项列表
        """
        logger.info("执行多查询策略")
        
        all_results = []
        
        # 1. 使用原始查询
        logger.info(f"查询1: 原始查询 - {query}")
        results1 = self.vector_store.similarity_search(
            query=query,
            top_k=max(3, config.top_k // 2),
            embedding_engine=self.embedding_engine
        )
        all_results.extend(results1)
        
        # 2. 使用关键词构建查询
        if intent_analysis.keywords:
            keywords_query = " ".join(intent_analysis.keywords)
            logger.info(f"查询2: 关键词查询 - {keywords_query}")
            results2 = self.vector_store.similarity_search(
                query=keywords_query,
                top_k=max(3, config.top_k // 2),
                embedding_engine=self.embedding_engine
            )
            all_results.extend(results2)
        
        # 3. 如果有函数名，专门查询函数
        function_names = intent_analysis.get_function_names()
        if function_names:
            function_query = " ".join(function_names)
            logger.info(f"查询3: 函数查询 - {function_query}")
            results3 = self.vector_store.similarity_search(
                query=function_query,
                top_k=max(2, config.top_k // 3),
                embedding_engine=self.embedding_engine
            )
            all_results.extend(results3)
        
        # 转换并去重结果
        context_items = self._deduplicate_and_convert(all_results, config.min_relevance_score)
        
        # 限制结果数量
        return context_items[:config.top_k]
    
    def _process_search_results(
        self, 
        results: List[Dict[str, Any]], 
        min_score: float = 0.0
    ) -> List[ContextItem]:
        """处理搜索结果并转换为ContextItem
        
        Args:
            results: 搜索结果
            min_score: 最小相关性分数阈值
            
        Returns:
            处理后的ContextItem列表
        """
        seen_content = set()
        context_items = []
        
        for result in results:
            content = result.get("content", "")
            score = result.get("score", 0.0)
            
            # 跳过重复内容和低分结果
            if content in seen_content or score < min_score:
                continue
            
            seen_content.add(content)
            
            # 转换为ContextItem
            context_item = ContextItem(
                content=content,
                source_type=self.source_type,
                relevance_score=score,
                metadata={
                    "chunk_id": result.get("id", ""),
                    "file_path": result.get("metadata", {}).get("file_path", ""),
                    "function_name": result.get("metadata", {}).get("function_name", ""),
                    "start_line": result.get("metadata", {}).get("start_line", 0),
                    "end_line": result.get("metadata", {}).get("end_line", 0),
                    "chunk_type": result.get("metadata", {}).get("type", "code")
                }
            )
            
            context_items.append(context_item)
        
        # 按相关性分数排序
        context_items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return context_items
    
    def _deduplicate_and_convert(
        self, 
        results: List[Dict[str, Any]], 
        min_score: float = 0.0
    ) -> List[ContextItem]:
        """去重并转换为ContextItem
        
        Args:
            results: Chroma检索结果
            min_score: 最小相关性分数阈值
            
        Returns:
            去重后的ContextItem列表
        """
        seen_content = set()
        context_items = []
        
        for result in results:
            content = result.get("content", "")
            score = result.get("score", 0.0)
            
            # 跳过重复内容和低分结果
            if content in seen_content or score < min_score:
                continue
            
            seen_content.add(content)
            
            # 转换为ContextItem
            context_item = ContextItem(
                content=content,
                source_type=self.source_type,
                relevance_score=score,
                metadata={
                    "chunk_id": result.get("id", ""),
                    "file_path": result.get("metadata", {}).get("file_path", ""),
                    "function_name": result.get("metadata", {}).get("function_name", ""),
                    "start_line": result.get("metadata", {}).get("start_line", 0),
                    "end_line": result.get("metadata", {}).get("end_line", 0),
                    "chunk_type": result.get("metadata", {}).get("type", "code")
                }
            )
            
            context_items.append(context_item)
        
        # 按相关性分数排序
        context_items.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return context_items
    
    def get_source_type(self) -> str:
        """获取检索器的源类型标识"""
        return self.source_type.value
    
    def is_available(self) -> bool:
        """检查检索器是否可用"""
        if not self.vector_store or not self.embedding_engine:
            return False
        
        try:
            # 简单的可用性检查
            return hasattr(self.vector_store, 'similarity_search') and hasattr(self.embedding_engine, 'embed_text')
        except Exception as e:
            logger.error(f"Vector retriever availability check failed: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取向量存储统计信息
        
        Returns:
            统计信息字典
        """
        try:
            # 这里需要根据ChromaVectorStore的实际API来实现
            # 暂时返回基本信息
            return {
                "source_type": self.get_source_type(),
                "available": self.is_available(),
                "collection_name": getattr(self.vector_store, 'collection_name', 'unknown')
            }
        except Exception as e:
            logger.error(f"Failed to get vector store statistics: {e}")
            return {
                "source_type": self.get_source_type(),
                "available": False,
                "error": str(e)
            } 