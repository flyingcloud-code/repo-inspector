"""日志工具模块

提供统一的日志配置和管理功能
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from ..config.config_manager import ConfigManager, LoggingConfig


class LoggerManager:
    """日志管理器"""
    
    _initialized = False
    
    @classmethod
    def setup_logging(cls, config: Optional[LoggingConfig] = None) -> None:
        """设置日志配置
        
        Args:
            config: 日志配置，如果为None则从ConfigManager获取
        """
        if cls._initialized:
            return
        
        if config is None:
            config_manager = ConfigManager()
            app_config = config_manager.get_config()
            config = app_config.logging
        
        # 设置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.level.upper()))
        
        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 设置日志格式
        formatter = logging.Formatter(config.format)
        
        # 控制台处理器
        if config.console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, config.console_level.upper()))
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # 文件处理器
        if config.file_enabled:
            # 确保日志目录存在
            log_path = Path(config.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 解析文件大小
            max_bytes = cls._parse_size(config.file_max_size)
            
            # 创建轮转文件处理器
            file_handler = logging.handlers.RotatingFileHandler(
                filename=config.file_path,
                maxBytes=max_bytes,
                backupCount=config.file_backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, config.level.upper()))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        cls._initialized = True
    
    @staticmethod
    def _parse_size(size_str: str) -> int:
        """解析大小字符串为字节数
        
        Args:
            size_str: 大小字符串，如 '10MB', '1GB'
            
        Returns:
            int: 字节数
        """
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            # 假设是字节数
            return int(size_str)
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取指定名称的日志器
        
        Args:
            name: 日志器名称，通常使用 __name__
            
        Returns:
            logging.Logger: 日志器实例
        """
        if not cls._initialized:
            cls.setup_logging()
        
        return logging.getLogger(name)


def get_logger(name: str) -> logging.Logger:
    """便捷函数：获取日志器
    
    Args:
        name: 日志器名称
        
    Returns:
        logging.Logger: 日志器实例
    """
    return LoggerManager.get_logger(name) 