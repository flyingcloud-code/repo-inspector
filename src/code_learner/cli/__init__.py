"""
代码学习器CLI模块

提供命令行界面与代码学习器交互
"""

# This file makes the 'cli' directory a Python package.

# Expose key CLI functions for easier access if needed
from .status_commands import StatusCommands
from .project_commands import ProjectCommands
from .analyze_commands import AnalyzeCommands
from .query_commands import QueryCommands
from .call_graph_commands import CallGraphCommands
from .dep_graph_commands import DepGraphCommands

__all__ = [
    'StatusCommands',
    'ProjectCommands',
    'AnalyzeCommands',
    'QueryCommands',
    'CallGraphCommands',
    'DepGraphCommands',
]
