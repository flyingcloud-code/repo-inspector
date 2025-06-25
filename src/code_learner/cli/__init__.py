"""CLI模块

包含命令行界面相关的功能
"""

from .call_graph_cli import CallGraphCLI, main as call_graph_main

__all__ = [
    'CallGraphCLI',
    'call_graph_main'
]
