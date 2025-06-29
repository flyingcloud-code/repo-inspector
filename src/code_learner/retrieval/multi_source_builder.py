"""
多源上下文构建器实现

协调多个检索器，构建最终的重排序上下文。
"""

import time
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from ..core.context_models import (
    ContextItem, 
    IntentAnalysis, 
    RetrievalConfig, 
    RetrievalResult,
    RerankResult,
    SourceType
)
from ..core.retriever_interfaces import (
    IContextRetriever, 
    IReranker, 
    IIntentAnalyzer,
    IMultiSourceBuilder
)
from ..llm.chatbot import OpenRouterChatBot

logger = logging.getLogger(__name__)


class MultiSourceContextBuilder(IMultiSourceBuilder):
    """多源上下文构建器
    
    协调Vector、CallGraph、Dependency检索器，
    并使用LLM进行统一重排序。
    """
    
    def __init__(
        self,
        vector_retriever: IContextRetriever,
        call_graph_retriever: IContextRetriever,
        dependency_retriever: IContextRetriever,
        reranker: IReranker,
        intent_analyzer: Any,
        config: Optional[Dict[str, Any]] = None
    ):
        """初始化多源上下文构建器
        
        Args:
            vector_retriever: 向量检索器
            call_graph_retriever: 调用图检索器
            dependency_retriever: 依赖检索器
            reranker: 重排序器
            intent_analyzer: 意图分析器
            config: 配置
        """
        self.retrievers = {
            "vector": vector_retriever,
            "call_graph": call_graph_retriever,
            "dependency": dependency_retriever
        }
        self.reranker = reranker
        self.intent_analyzer = intent_analyzer
        
        # ---------- 加载默认配置 ----------
        if config is not None:
            self.config = config
        else:
            # 尝试从全局ConfigManager读取enhanced_query配置
            try:
                from ..config.config_manager import ConfigManager  # 延迟导入避免循环依赖
                cfg_mgr = ConfigManager()
                enhanced_cfg = cfg_mgr.get_config().enhanced_query  # EnhancedQueryConfig 实例
                self.config = enhanced_cfg.to_dict() if hasattr(enhanced_cfg, "to_dict") else self._get_default_config()
                logger.info("🛠️  MultiSourceContextBuilder 默认配置来自 ConfigManager.enhanced_query")
            except Exception as e:
                logger.warning(f"Failed to load enhanced_query config from ConfigManager, fallback to hard-coded defaults: {e}")
                self.config = self._get_default_config()
        
        # 如果向量检索器支持配置嵌入引擎，则配置它
        if hasattr(vector_retriever, 'configure_embedding_engine'):
            # 从ServiceFactory获取嵌入引擎
            from ..llm.service_factory import ServiceFactory
            embedding_engine = ServiceFactory().get_embedding_engine()
            vector_retriever.configure_embedding_engine(embedding_engine)
            logger.info("已为向量检索器配置嵌入引擎")
        
        logger.info(f"多源上下文构建器初始化完成，配置了{len(self.retrievers)}个检索器")
        
    def build_context(
        self, 
        query: str, 
        intent_analysis: Optional[IntentAnalysis] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> RerankResult:
        """构建多源上下文
        
        Args:
            query: 用户查询
            intent_analysis: 可选的意图分析结果
            config: 可选的配置覆盖
            
        Returns:
            最终的重排序结果
        """
        start_time = time.time()
        
        # 合并配置
        effective_config = self._merge_config(config)
        
        try:
            # 如果没有提供意图分析，则进行分析
            if intent_analysis is None:
                intent_analysis = self.intent_analyzer.analyze(query)
                logger.info(f"Intent analysis: {intent_analysis.intent_type}, entities: {intent_analysis.entities}")
            
            # 并行执行多源检索
            all_context_items = []
            if effective_config.get("parallel_retrieval", True):
                all_context_items = self._parallel_retrieve(query, intent_analysis, effective_config)
            else:
                all_context_items = self._sequential_retrieve(query, intent_analysis, effective_config)
            
            # 如果没有检索到任何结果
            if not all_context_items:
                logger.warning("No context items retrieved from any source")
                return RerankResult(
                    items=[],
                    rerank_time=time.time() - start_time,
                    original_count=0,
                    confidence=0.0
                )
            
            logger.info(f"Retrieved {len(all_context_items)} total items from {len(self._get_active_sources())} sources")
            
            # 使用LLM进行重排序
            final_top_k = effective_config.get("final_top_k", 5)
            rerank_result = self.reranker.rerank(query, all_context_items, final_top_k)
            
            # 基于缺失源数量调整置信度
            all_sources = set(self.retrievers.keys())
            active_sources = set(self._get_active_sources())
            missing_sources = all_sources - active_sources
            if missing_sources:
                penalty = 0.1 * len(missing_sources)
                rerank_result.confidence = max(0.0, rerank_result.confidence - penalty)
                rerank_result.metadata = {
                    "missing_sources": list(missing_sources)
                }
            
            # 更新总时间
            total_time = time.time() - start_time
            rerank_result.rerank_time = total_time
            
            logger.info(f"Multi-source context building completed: {len(rerank_result.items)} final items in {total_time:.3f}s")
            
            return rerank_result
            
        except Exception as e:
            logger.error(f"Multi-source context building failed: {e}")
            return RerankResult(
                items=[],
                rerank_time=time.time() - start_time,
                original_count=0,
                confidence=0.0
            )
    
    def _parallel_retrieve(
        self, 
        query: str, 
        intent_analysis: IntentAnalysis,
        config: Dict[str, Any]
    ) -> List[ContextItem]:
        """并行执行多源检索
        
        Args:
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 配置字典
            
        Returns:
            所有检索结果的合并列表
        """
        all_items = []
        timeout = config.get("timeout_seconds", 30)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 提交所有检索任务
            futures = {}
            for source_name, retriever in self.retrievers.items():
                if self._is_source_enabled(source_name, config):
                    retrieval_config = self._build_retrieval_config(source_name, config)
                    future = executor.submit(
                        self._safe_retrieve, 
                        retriever, 
                        query, 
                        intent_analysis, 
                        retrieval_config
                    )
                    futures[future] = source_name
            
            # 收集结果
            for future in as_completed(futures, timeout=timeout):
                source_name = futures[future]
                try:
                    result = future.result()
                    if result and result.items:
                        all_items.extend(result.items)
                        logger.info(f"{source_name} retrieval: {len(result.items)} items in {result.query_time:.3f}s")
                    else:
                        logger.warning(f"{source_name} retrieval returned no results")
                except Exception as e:
                    logger.error(f"{source_name} retrieval failed: {e}")
        
        return all_items
    
    def _sequential_retrieve(
        self, 
        query: str, 
        intent_analysis: IntentAnalysis,
        config: Dict[str, Any]
    ) -> List[ContextItem]:
        """顺序执行多源检索
        
        Args:
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 配置字典
            
        Returns:
            所有检索结果的合并列表
        """
        all_items = []
        
        for source_name, retriever in self.retrievers.items():
            if self._is_source_enabled(source_name, config):
                try:
                    retrieval_config = self._build_retrieval_config(source_name, config)
                    result = self._safe_retrieve(retriever, query, intent_analysis, retrieval_config)
                    
                    if result and result.items:
                        all_items.extend(result.items)
                        logger.info(f"{source_name} retrieval: {len(result.items)} items in {result.query_time:.3f}s")
                    else:
                        logger.warning(f"{source_name} retrieval returned no results")
                        
                except Exception as e:
                    logger.error(f"{source_name} retrieval failed: {e}")
        
        return all_items
    
    def _safe_retrieve(
        self,
        retriever: IContextRetriever,
        query: str,
        intent_analysis: IntentAnalysis,
        config: RetrievalConfig
    ) -> Optional[RetrievalResult]:
        """安全的检索调用，包含错误处理
        
        Args:
            retriever: 检索器实例
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 检索配置
            
        Returns:
            检索结果或None
        """
        try:
            if not retriever.is_available():
                logger.warning(f"Retriever {retriever.get_source_type()} is not available")
                return None
            
            return retriever.retrieve(query, intent_analysis, config)
            
        except Exception as e:
            logger.error(f"Retriever {retriever.get_source_type()} failed: {e}")
            return None
    
    def _is_source_enabled(self, source_name: str, config: Dict[str, Any]) -> bool:
        """检查指定源是否启用"""
        sources_config = config.get("sources", {})
        source_config = sources_config.get(source_name, {})
        return source_config.get("enable", True)
    
    def _build_retrieval_config(self, source_name: str, config: Dict[str, Any]) -> RetrievalConfig:
        """构建检索配置"""
        sources_config = config.get("sources", {})
        source_config = sources_config.get(source_name, {})
        
        return RetrievalConfig(
            top_k=source_config.get("top_k", 5),
            enable_parallel=config.get("parallel_retrieval", True),
            timeout_seconds=config.get("timeout_seconds", 30),
            min_relevance_score=source_config.get("min_relevance_score", 0.0)
        )
    
    def _merge_config(self, override_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """合并配置"""
        effective_config = self.config.copy()
        if override_config:
            effective_config.update(override_config)
        return effective_config
    
    def _get_active_sources(self) -> List[str]:
        """获取活跃的检索源列表"""
        active_sources = []
        for source_name, retriever in self.retrievers.items():
            if self._is_source_enabled(source_name, self.config) and retriever.is_available():
                active_sources.append(source_name)
        return active_sources
    
    def get_available_sources(self) -> List[str]:
        """获取可用的检索源列表"""
        available_sources = []
        for source_name, retriever in self.retrievers.items():
            if retriever.is_available():
                available_sources.append(source_name)
        return available_sources
    
    def health_check(self) -> Dict[str, bool]:
        """检查各组件的健康状态"""
        health_status = {}
        
        # 检查检索器状态
        for source_name, retriever in self.retrievers.items():
            health_status[f"retriever_{source_name}"] = retriever.is_available()
        
        # 检查重排序器状态
        health_status["reranker"] = self.reranker.is_available()
        
        # 检查意图分析器状态（如果有的话）
        if hasattr(self.intent_analyzer, 'is_available'):
            health_status["intent_analyzer"] = self.intent_analyzer.is_available()
        else:
            health_status["intent_analyzer"] = True  # 假设可用
        
        return health_status
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "builder_type": "multi_source",
            "total_sources": len(self.retrievers),
            "available_sources": len(self.get_available_sources()),
            "config": self.config.copy(),
            "health": self.health_check()
        }
        
        # 添加各检索器的统计信息
        for source_name, retriever in self.retrievers.items():
            if hasattr(retriever, 'get_statistics'):
                stats[f"{source_name}_stats"] = retriever.get_statistics()
        
        # 添加重排序器统计信息
        if hasattr(self.reranker, 'get_statistics'):
            stats["reranker_stats"] = self.reranker.get_statistics()
        
        return stats
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "sources": {
                "vector": {
                    "enable": True,
                    "top_k": 5,
                    "min_relevance_score": 0.0
                },
                "call_graph": {
                    "enable": True,
                    "top_k": 5,
                    "min_relevance_score": 0.0
                },
                "dependency": {
                    "enable": True,
                    "top_k": 5,
                    "min_relevance_score": 0.0
                }
            },
            "final_top_k": 5,
            "parallel_retrieval": True,
            "timeout_seconds": 30
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """更新配置"""
        self.config.update(new_config)
        logger.info("Multi-source builder configuration updated")
    
    def enable_source(self, source_name: str, enabled: bool = True) -> None:
        """启用或禁用指定的检索源"""
        if source_name in self.retrievers:
            if "sources" not in self.config:
                self.config["sources"] = {}
            if source_name not in self.config["sources"]:
                self.config["sources"][source_name] = {}
            
            self.config["sources"][source_name]["enable"] = enabled
            logger.info(f"Source {source_name} {'enabled' if enabled else 'disabled'}")
        else:
            logger.warning(f"Unknown source: {source_name}")
    
    def set_top_k(self, source_name: str, top_k: int) -> None:
        """设置指定源的top-k参数"""
        if source_name in self.retrievers:
            if "sources" not in self.config:
                self.config["sources"] = {}
            if source_name not in self.config["sources"]:
                self.config["sources"][source_name] = {}
            
            self.config["sources"][source_name]["top_k"] = top_k
            logger.info(f"Source {source_name} top_k set to {top_k}")
        else:
            logger.warning(f"Unknown source: {source_name}") 