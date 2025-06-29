"""配置管理器

实现单例模式的配置管理器，支持YAML配置文件和环境变量覆盖
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from dotenv import load_dotenv

from ..core.exceptions import ConfigurationError
from ..core.data_models import (
    Config, DatabaseConfig, VectorStoreConfig, LLMConfig, 
    ParserConfig, LoggingConfig, PerformanceConfig, AppConfig,
    EmbeddingConfig, EnhancedQueryConfig
)

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器 - 单例模式"""

    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None
    _config_path: Optional[Path] = None

    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            # 加载.env文件
            load_dotenv()
            logger.debug("已加载.env文件")
        return cls._instance

    def get_config(self) -> Config:
        """获取配置对象
        
        Returns:
            Config: 配置对象
        """
        if self._config is None:
            self._config = self.load_config()
        return self._config

    def load_config(self, config_path: Optional[Path] = None) -> Config:
        """加载配置文件
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
            
        Returns:
            Config: 配置对象
            
        Raises:
            ConfigurationError: 配置错误
        """
        try:
            if self._config is not None and (config_path is None or config_path == self._config_path):
                return self._config

            if config_path is None:
                config_path = Path('config/config.yml')

            self._config_path = config_path
            config_data = self._load_yaml_config(config_path)
            
            # 应用环境变量覆盖
            config_data = self._apply_environment_overrides(config_data)
            
            # 预处理配置数据，确保关键字段有效
            self._preprocess_config_data(config_data)
            
            # 创建配置对象
            self._config = self._create_config_object(config_data)

            return self._config

        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            raise ConfigurationError(f"加载配置失败: {e}")

    def _load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """加载YAML配置文件
        
        Args:
            config_path: 配置文件路径
        
        Returns:
            Dict[str, Any]: 配置数据字典
        """
        try:
            if not config_path.exists():
                logger.warning(f"配置文件不存在: {config_path}")
                return {}
            
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                logger.warning(f"配置文件为空: {config_path}")
                return {}
            
            return config_data
        except Exception as e:
            logger.error(f"加载YAML配置失败: {e}")
            raise ConfigurationError(f"加载YAML配置失败: {e}")
    
    def _apply_environment_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖
        
        Args:
            config_data: 配置数据字典
        
        Returns:
            Dict[str, Any]: 更新后的配置数据字典
        """
        env_mappings = {
            'NEO4J_PASSWORD': ['database', 'neo4j', 'password'],  # 必需
            'NEO4J_URI': ['database', 'neo4j', 'uri'],
            'NEO4J_USER': ['database', 'neo4j', 'user'],
            'OPENROUTER_API_KEY': ['llm', 'chat', 'api_key'],     # 必需
            'LOG_LEVEL': ['logging', 'level'],
            'DEBUG': ['app', 'debug'],
            'VERBOSE': ['app', 'verbose'],
        }
        
        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None and env_value.strip():  # 确保环境变量非空
                # 处理布尔值
                if env_var in ('DEBUG', 'VERBOSE'):
                    env_value = env_value.lower() in ('true', '1', 'yes', 'y')
                
                # 更新配置
                self._set_nested_value(config_data, config_path, env_value)
                logger.debug(f"从环境变量加载配置: {env_var}")
        
        return config_data
    
    def _set_nested_value(self, data: Dict[str, Any], path: List[str], value: Any) -> None:
        """设置嵌套字典的值
        
        Args:
            data: 嵌套字典
            path: 路径列表
            value: 要设置的值
        """
        current = data
        for i, key in enumerate(path):
            if i == len(path) - 1:
                current[key] = value
            else:
                if key not in current or not isinstance(current[key], dict):
                    current[key] = {}
                current = current[key]
    
    def _preprocess_config_data(self, config_data: Dict[str, Any]) -> None:
        """预处理配置数据，确保关键字段有效
        
        Args:
            config_data: 配置数据字典
        
        Raises:
            ConfigurationError: 配置验证失败时抛出
        """
        # 验证日志级别
        if 'logging' in config_data and 'level' in config_data['logging']:
            log_level = config_data['logging']['level']
            valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            if log_level not in valid_levels:
                raise ConfigurationError(f"无效的日志级别: {log_level}, 有效值: {valid_levels}")
        
        # 验证Neo4j密码
        if 'database' in config_data and 'neo4j' in config_data['database']:
            if 'password' not in config_data['database']['neo4j'] or not config_data['database']['neo4j']['password']:
                raise ConfigurationError("NEO4J_PASSWORD环境变量是必需的")
        
        # 验证API密钥
        if 'llm' in config_data and 'chat' in config_data['llm']:
            if 'api_key' not in config_data['llm']['chat'] or not config_data['llm']['chat']['api_key']:
                raise ConfigurationError("OPENROUTER_API_KEY环境变量是必需的")
    
    def _create_config_object(self, config_data: Dict[str, Any]) -> Config:
        """创建配置对象
        
        Args:
            config_data: 配置数据字典
        
        Returns:
            Config: 配置对象
        """
        try:
            return Config.from_dict(config_data)
        except Exception as e:
            logger.error(f"创建配置对象失败: {e}")
            raise ConfigurationError(f"创建配置对象失败: {e}")
    
    def reload_config(self, config_path: Optional[Path] = None) -> Config:
        """重新加载配置
        
        Args:
            config_path: 配置文件路径，如果为None则使用当前路径
            
        Returns:
            Config: 配置对象
        """
        self._config = None
        return self.load_config(config_path)
