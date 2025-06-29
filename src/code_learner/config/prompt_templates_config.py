"""Prompt 模板配置文件

此文件集中定义所有可用的重排序 Prompt 模板，
方便用户修改或扩展，而无需进入业务代码。

要添加新模板：
1. 在 `TEMPLATES` 字典中添加新的键值对
2. 键为模板名称，值为可调用对象 (函数或 lambda)
3. 在配置文件 `settings.yaml` -> `enhanced_query.prompt_template` 中填入新模板名即可启用

注意：若要完全自定义 Prompt 生成逻辑，可在此定义函数，
签名应为 `(query: str, context_items: List[ContextItem]) -> str`。
"""
from typing import List
from ..core.context_models import ContextItem
from ..rerank.prompt_templates import PromptTemplates as _PT

# ----------------- 默认模板实现 -----------------

def default(query: str, context_items: List[ContextItem]) -> str:  # noqa: D401
    """默认模板 – 直接调用原 default_rerank_prompt"""
    return _PT.default_rerank_prompt(query, context_items)


def function_analysis(query: str, context_items: List[ContextItem]) -> str:
    """函数分析场景模板"""
    return _PT.function_analysis_prompt(query, context_items)


def dependency_check(query: str, context_items: List[ContextItem]) -> str:
    """依赖分析场景模板"""
    return _PT.dependency_prompt(query, context_items) if hasattr(_PT, "dependency_prompt") else _PT.default_rerank_prompt(query, context_items)


def debugging(query: str, context_items: List[ContextItem]) -> str:
    """调试场景模板"""
    return _PT.debugging_prompt(query, context_items)

# -------------------------------------------------

TEMPLATES = {
    "default": default,
    "function_analysis": function_analysis,
    "dependency_check": dependency_check,
    "debugging": debugging,
} 