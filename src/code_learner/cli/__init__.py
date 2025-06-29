"""
代码学习器CLI模块

提供命令行界面与代码学习器交互
"""

from .code_analyzer_cli import main as analyzer_main
from .call_graph_cli import main as call_graph_main
from .dependency_cli import main as dependency_main
from .unified_cli import main as unified_main

__all__ = [
    'analyzer_main',
    'call_graph_main',
    'dependency_main',
    'unified_main'
]
