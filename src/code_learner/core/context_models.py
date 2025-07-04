"""
上下文项数据模型

定义多源检索系统中使用的统一数据结构。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum


class SourceType(str, Enum):
    """The source of the retrieved context."""
    VECTOR = "vector_search"
    GRAPH_FUNCTION_DEFINITION = "graph_function_definition"
    GRAPH_CALLERS = "graph_callers"
    GRAPH_CALLEES = "graph_callees"
    GRAPH_DEPENDENCIES = "graph_dependencies"
    UNKNOWN = "unknown"

class IntentType(str, Enum):
    """The type of user intent."""
    GENERAL_QUESTION = "general_question"
    EXPLAIN_CODE = "explain_code"
    FIND_USAGE = "find_usage"
    FIND_DEFINITION = "find_definition"
    FIND_DEPENDENCIES = "find_dependencies"


@dataclass
class ContextItem:
    """
    A standardized data structure for a single piece of context
    retrieved from any source (vector DB, graph DB, etc.).
    
    This ensures that data from different retrievers has a consistent
    shape, making it easy for downstream components like the Reranker
    to process them.
    """
    content: str
    source: str  # e.g., "vector_search", "graph_retrieval_callers"
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_rerank_format(self) -> str:
        """
        Converts the context item into a string format suitable for
        the LLM Reranker prompt.

        The format is designed to be concise and informative for the LLM.
        """
        # Truncate content for brevity in the rerank prompt
        truncated_content = (self.content[:250] + '...') if len(self.content) > 250 else self.content
        return f"[Source: {self.source}, Score: {self.score:.2f}]\n{truncated_content}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "source": self.source,
            "score": self.score,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextItem":
        """从字典创建ContextItem实例"""
        return cls(
            content=data["content"],
            source=data["source"],
            score=data["score"],
            metadata=data.get("metadata", {})
        )


@dataclass
class IntentAnalysis:
    """意图分析结果
    
    包含从用户查询中提取的结构化信息，
    用于指导不同检索器的查询策略。
    """
    entities: List[Dict[str, str]] = field(default_factory=list)  # 提取的实体（函数名、文件名等）
    intent_type: IntentType = IntentType.GENERAL_QUESTION  # 意图类型
    keywords: List[str] = field(default_factory=list)  # 关键词
    context_hints: Dict[str, Any] = field(default_factory=dict)  # 上下文提示
    confidence: float = 0.0  # 分析置信度
    
    def __post_init__(self):
        """数据验证和转换"""
        # 如果intent_type是字符串，转换为枚举
        if isinstance(self.intent_type, str):
            try:
                self.intent_type = IntentType(self.intent_type)
            except ValueError:
                self.intent_type = IntentType.GENERAL_QUESTION
    
    def has_function_names(self) -> bool:
        """检查是否包含函数名"""
        return any(entity.get("type") == "function" for entity in self.entities)
    
    def has_file_names(self) -> bool:
        """检查是否包含文件名"""
        return any(entity.get("type") == "file" for entity in self.entities)
    
    def get_function_names(self) -> List[str]:
        """获取所有函数名"""
        return [entity.get("name") for entity in self.entities if entity.get("type") == "function"]
    
    def get_file_names(self) -> List[str]:
        """获取所有文件名"""
        return [entity.get("name") for entity in self.entities if entity.get("type") == "file"]


@dataclass
class RetrievalConfig:
    """检索配置"""
    top_k: int = 5
    enable_parallel: bool = True
    timeout_seconds: int = 30
    min_relevance_score: float = 0.0
    
    def validate(self) -> None:
        """验证配置参数"""
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if not 0.0 <= self.min_relevance_score <= 1.0:
            raise ValueError("min_relevance_score must be between 0.0 and 1.0")


@dataclass
class RetrievalResult:
    """检索结果包装器"""
    items: List[ContextItem]
    source_type: SourceType
    query_time: float  # 检索耗时（秒）
    total_candidates: int  # 候选项总数
    
    def filter_by_score(self, min_score: float) -> "RetrievalResult":
        """按相关性分数过滤结果"""
        filtered_items = [item for item in self.items if item.score >= min_score]
        return RetrievalResult(
            items=filtered_items,
            source_type=self.source_type,
            query_time=self.query_time,
            total_candidates=len(filtered_items)
        )
    
    def top_k(self, k: int) -> "RetrievalResult":
        """获取前k个结果"""
        return RetrievalResult(
            items=self.items[:k],
            source_type=self.source_type,
            query_time=self.query_time,
            total_candidates=self.total_candidates
        )


@dataclass
class RerankResult:
    """重排序结果"""
    items: List[ContextItem]
    rerank_time: float  # 重排序耗时（秒）
    original_count: int  # 原始项目数量
    confidence: float = 0.0  # 重排序置信度
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_context_string(self, separator: str = "\n\n") -> str:
        """转换为上下文字符串"""
        return separator.join(item.content for item in self.items) 