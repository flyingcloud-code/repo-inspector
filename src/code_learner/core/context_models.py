"""
上下文项数据模型

定义多源检索系统中使用的统一数据结构。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Literal
from enum import Enum


class SourceType(Enum):
    """检索源类型枚举"""
    VECTOR = "vector"
    CALL_GRAPH = "call_graph"
    DEPENDENCY = "dependency"


class IntentType(Enum):
    """用户意图类型枚举"""
    FUNCTION_QUERY = "function_query"  # 函数查询
    FILE_QUERY = "file_query"  # 文件查询
    CONCEPT_QUERY = "concept_query"  # 概念查询
    CALL_RELATIONSHIP = "call_relationship"  # 调用关系查询
    DEPENDENCY_QUERY = "dependency_query"  # 依赖关系查询
    GENERAL_QUESTION = "general_question"  # 一般问题


@dataclass
class ContextItem:
    """统一的上下文项数据结构
    
    用于表示从不同检索源获取的上下文信息，
    支持统一的重排序和处理流程。
    """
    content: str
    source_type: SourceType
    relevance_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """数据验证"""
        if not isinstance(self.source_type, SourceType):
            if isinstance(self.source_type, str):
                self.source_type = SourceType(self.source_type)
            else:
                raise ValueError(f"Invalid source_type: {self.source_type}")
        
        if not 0.0 <= self.relevance_score <= 1.0:
            raise ValueError(f"relevance_score must be between 0.0 and 1.0, got {self.relevance_score}")
    
    def to_rerank_format(self, max_length: int = 200) -> str:
        """转换为重排序输入格式
        
        Args:
            max_length: 内容的最大长度
            
        Returns:
            格式化的字符串，用于LLM重排序
        """
        truncated_content = self.content[:max_length]
        if len(self.content) > max_length:
            truncated_content += "..."
        
        return f"[{self.source_type.value.upper()}] {truncated_content}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "source_type": self.source_type.value,
            "relevance_score": self.relevance_score,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextItem":
        """从字典创建ContextItem实例"""
        return cls(
            content=data["content"],
            source_type=SourceType(data["source_type"]),
            relevance_score=data["relevance_score"],
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
        filtered_items = [item for item in self.items if item.relevance_score >= min_score]
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