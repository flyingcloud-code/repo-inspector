"""
多源检索模块

提供基于向量、调用图和依赖图的多源检索功能。
"""

# 导出主要的检索器类
from .vector_retriever import VectorContextRetriever
from .multi_source_builder import MultiSourceContextBuilder

# 版本信息
__version__ = "2.0.0"

# 导出列表
__all__ = [
    "VectorContextRetriever",
    "MultiSourceContextBuilder",
] 