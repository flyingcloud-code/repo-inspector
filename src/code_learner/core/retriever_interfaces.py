"""
检索器和重排序器接口定义

定义多源检索系统中各组件的抽象接口，
遵循SOLID原则中的接口隔离和依赖倒置。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .context_models import (
    ContextItem, 
    IntentAnalysis, 
    RetrievalConfig, 
    RetrievalResult,
    RerankResult
)


class IContextRetriever(ABC):
    """上下文检索器接口
    
    定义了所有检索器必须实现的基本方法。
    每个具体的检索器（Vector、CallGraph、Dependency）
    都应该实现这个接口。
    """
    
    @abstractmethod
    def retrieve(
        self, 
        query: str, 
        intent_analysis: IntentAnalysis, 
        config: RetrievalConfig
    ) -> RetrievalResult:
        """检索相关的上下文项
        
        Args:
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 检索配置
            
        Returns:
            检索结果，包含上下文项列表和元数据
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
    """重排序器接口
    
    定义了重排序器的基本方法，支持不同的重排序策略。
    """
    
    @abstractmethod
    def rerank(
        self, 
        query: str, 
        context_items: List[ContextItem], 
        top_k: int = 5
    ) -> RerankResult:
        """对上下文项进行重新排序
        
        Args:
            query: 原始查询
            context_items: 待重排序的上下文项列表
            top_k: 返回的top-k结果数量
            
        Returns:
            重排序结果
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查重排序器是否可用（例如LLM API是否可访问）"""
        pass


class IIntentAnalyzer(ABC):
    """意图分析器接口
    
    负责分析用户查询的意图，提取关键信息。
    """
    
    @abstractmethod
    def analyze(self, query: str) -> IntentAnalysis:
        """分析用户查询的意图
        
        Args:
            query: 用户查询字符串
            
        Returns:
            意图分析结果
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