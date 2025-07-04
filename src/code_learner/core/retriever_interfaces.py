"""
检索器和重排序器接口定义

定义多源检索系统中各组件的抽象接口，
遵循SOLID原则中的接口隔离和依赖倒置。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

from .context_models import ContextItem, IntentAnalysis, RerankResult


class IContextRetriever(ABC):
    """
    Interface for all context retrieval components.
    
    This ensures that each retriever (e.g., for vector search, graph search)
    can be called in a standardized way by the main context builder.
    """
    @abstractmethod
    def retrieve(self, query: str, intent: Dict[str, Any]) -> List[ContextItem]:
        """
        Retrieves context relevant to the query and intent.
        
        Args:
            query: The user's original query string.
            intent: A dictionary representing the analyzed intent of the query,
                    which can be used to guide the retrieval process.
            
        Returns:
            A list of ContextItem objects, or an empty list if no
            relevant context is found.
        """
        pass
    
    @abstractmethod
    def get_source_type(self) -> str:
        """获取检索器的源类型标识"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查检索器是否可用（例如数据库连接是否正常）"""
        pass


class IReranker(ABC):
    """
    Interface for a reranking component.
    
    This standardizes the process of taking a list of context items
    and re-ordering them based on their relevance to the original query.
    """
    @abstractmethod
    def rerank(self, query: str, items: List[ContextItem], top_k: int) -> List[ContextItem]:
        """
        Reranks a list of context items.
        
        Args:
            query: The user's original query string.
            items: A list of ContextItem objects from various sources.
            top_k: The desired number of items to return after reranking.
            
        Returns:
            A sorted list of the top_k most relevant ContextItem objects.
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查重排序器是否可用（例如LLM API是否可访问）"""
        pass


class IIntentAnalyzer(ABC):
    """
    Interface for the Intent Analyzer component.
    
    This component is responsible for understanding the user's query
    and extracting structured information to guide the retrieval process.
    """
    @abstractmethod
    def analyze(self, query: str) -> IntentAnalysis:
        """
        Analyzes the user query to determine intent and extract entities.

        Args:
            query: The user's natural language query.

        Returns:
            An IntentAnalysis object containing structured information about the query.
        """
        pass


class IMultiSourceBuilder(ABC):
    """多源上下文构建器接口
    
    协调多个检索器，构建最终的上下文。
    """
    
    @abstractmethod
    def build_context(
        self, 
        query: str, 
        intent_analysis: IntentAnalysis,
        config: Optional[Dict[str, Any]] = None
    ) -> RerankResult:
        """构建多源上下文
        
        Args:
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 可选的配置覆盖
            
        Returns:
            最终的重排序结果
        """
        pass
    
    @abstractmethod
    def get_available_sources(self) -> List[str]:
        """获取可用的检索源列表"""
        pass
    
    @abstractmethod
    def health_check(self) -> Dict[str, bool]:
        """检查各组件的健康状态"""
        pass


class IContextCache(ABC):
    """上下文缓存接口
    
    可选的缓存层，用于提高性能。
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[List[ContextItem]]:
        """从缓存获取结果"""
        pass
    
    @abstractmethod
    def put(self, key: str, items: List[ContextItem], ttl: int = 3600) -> None:
        """将结果存入缓存
        
        Args:
            key: 缓存键
            items: 上下文项列表
            ttl: 生存时间（秒）
        """
        pass
    
    @abstractmethod
    def invalidate(self, pattern: str = "*") -> None:
        """清除缓存"""
        pass


class IMetricsCollector(ABC):
    """指标收集器接口
    
    用于收集性能指标和使用统计。
    """
    
    @abstractmethod
    def record_retrieval_time(self, source_type: str, duration: float) -> None:
        """记录检索时间"""
        pass
    
    @abstractmethod
    def record_rerank_time(self, duration: float) -> None:
        """记录重排序时间"""
        pass
    
    @abstractmethod
    def record_query_count(self, source_type: str) -> None:
        """记录查询次数"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标统计"""
        pass


# 工厂接口，用于创建各种组件
class IRetrieverFactory(ABC):
    """检索器工厂接口"""
    
    @abstractmethod
    def create_vector_retriever(self) -> IContextRetriever:
        """创建向量检索器"""
        pass
    
    @abstractmethod
    def create_call_graph_retriever(self) -> IContextRetriever:
        """创建调用图检索器"""
        pass
    
    @abstractmethod
    def create_dependency_retriever(self) -> IContextRetriever:
        """创建依赖图检索器"""
        pass
    
    @abstractmethod
    def create_reranker(self) -> IReranker:
        """创建重排序器"""
        pass
    
    @abstractmethod
    def create_intent_analyzer(self) -> IIntentAnalyzer:
        """创建意图分析器"""
        pass
    
    @abstractmethod
    def create_multi_source_builder(self) -> IMultiSourceBuilder:
        """创建多源构建器"""
        pass 