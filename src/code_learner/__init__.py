"""C语言智能代码分析调试工具

一个基于AI技术的C语言代码理解和调试助手
"""

__version__ = "0.1.0"
__author__ = "Code Learner Team"
__email__ = "team@codelearner.dev"

# 核心组件导入
from .config.config_manager import ConfigManager, Config
from .core.data_models import Function, FileInfo, ParsedCode, EmbeddingData, QueryResult
from .core.interfaces import IParser, IGraphStore, IVectorStore, IEmbeddingEngine, IChatBot
from .core.exceptions import (
    CodeLearnerError, ParseError, DatabaseConnectionError,
    ConfigurationError, ModelLoadError, EmbeddingError, QueryError, APIError
)
from .utils.logger import get_logger


# 版本信息
def get_version() -> str:
    """获取版本信息"""
    return __version__


# 快捷初始化函数
def setup_environment():
    """设置环境和日志"""
    from .utils.logger import LoggerManager
    LoggerManager.setup_logging()

    logger = get_logger(__name__)
    logger.info(f"C语言智能代码分析调试工具 v{__version__} 初始化完成")


__all__ = [
    # 版本信息
    '__version__', 'get_version',

    # 核心配置
    'ConfigManager', 'Config',

    # 数据模型
    'Function', 'FileInfo', 'ParsedCode', 'EmbeddingData', 'QueryResult',

    # 接口定义
    'IParser', 'IGraphStore', 'IVectorStore', 'IEmbeddingEngine', 'IChatBot',

    # 异常类
    'CodeLearnerError', 'ParseError', 'DatabaseConnectionError',
    'ConfigurationError', 'ModelLoadError', 'EmbeddingError', 'QueryError', 'APIError',

    # 工具函数
    'get_logger', 'setup_environment'
]
