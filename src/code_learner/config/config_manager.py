"""配置管理器

实现单例模式的配置管理器，支持YAML配置文件和环境变量覆盖
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

from ..core.exceptions import ConfigurationError


@dataclass
class DatabaseConfig:
    """数据库配置"""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "<your password>"
    neo4j_database: str = "neo4j"
    sqlite_path: str = "./data/metadata.db"


@dataclass
class VectorStoreConfig:
    """向量存储配置"""
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "code_embeddings"


@dataclass
class LLMConfig:
    """LLM配置"""
    embedding_model_name: str = "jinaai/jina-embeddings-v2-base-code"
    embedding_cache_dir: str = "~/.cache/torch/sentence_transformers/"
    embedding_batch_size: int = 32

    chat_api_key: str = ""
    chat_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    chat_model: str = "google/gemini-2.0-flash-001"
    chat_max_tokens: int = 8192
    chat_temperature: float = 1.0
    chat_top_p: float = 0.95


@dataclass
class ParserConfig:
    """解析器配置"""
    tree_sitter_language: str = "c"
    include_patterns: list = None
    exclude_patterns: list = None
    max_file_size: int = 10485760  # 10MB
    encoding: str = "utf-8"

    def __post_init__(self):
        if self.include_patterns is None:
            self.include_patterns = ["*.c", "*.h"]
        if self.exclude_patterns is None:
            self.exclude_patterns = ["*test*", "*example*", "*.bak"]


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "./logs/code_learner.log"
    file_max_size: str = "10MB"
    file_backup_count: int = 5
    console_enabled: bool = True
    console_level: str = "INFO"


@dataclass
class PerformanceConfig:
    """性能配置"""
    max_workers: int = 4
    cache_enabled: bool = True
    cache_ttl: int = 3600
    cache_max_size: int = 1000
    embedding_batch_size: int = 32
    parsing_batch_size: int = 10


@dataclass
class AppConfig:
    """应用配置"""
    name: str = "C语言智能代码分析调试工具"
    version: str = "0.1.0"
    data_dir: str = "./data"
    logs_dir: str = "./logs"
    cache_dir: str = "./cache"
    debug: bool = False
    verbose: bool = False


@dataclass
class Config:
    """完整配置"""
    database: DatabaseConfig
    vector_store: VectorStoreConfig
    llm: LLMConfig
    parser: ParserConfig
    logging: LoggingConfig
    performance: PerformanceConfig
    app: AppConfig


class ConfigManager:
    """配置管理器 - 单例模式"""

    _instance: Optional['ConfigManager'] = None
    _config: Optional[Config] = None

    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_config(self, config_path: Optional[Path] = None) -> Config:
        """加载配置

        Args:
            config_path: 配置文件路径，默认为 config/config.yml

        Returns:
            Config: 配置对象

        Raises:
            ConfigurationError: 配置加载失败
        """
        if self._config is not None:
            return self._config

        try:
            # 加载.env文件
            if DOTENV_AVAILABLE:
                load_dotenv()

            # 确定配置文件路径
            if config_path is None:
                config_path = Path("config/config.yml")

            # 加载YAML配置
            config_data = self._load_yaml_config(config_path)

            # 应用环境变量覆盖
            config_data = self._apply_environment_overrides(config_data)

            # 创建配置对象
            self._config = self._create_config_objects(config_data)

            # 验证配置
            self._validate_config(self._config)

            return self._config

        except Exception as e:
            raise ConfigurationError("config_loading", str(e))

    def _load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """加载YAML配置文件"""
        if not config_path.exists():
            raise ConfigurationError("config_file", f"Configuration file not found: {config_path}")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError("yaml_parsing", f"Invalid YAML format: {e}")

    def _apply_environment_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """应用环境变量覆盖"""
        env_mappings = {
            'NEO4J_PASSWORD': ['database', 'neo4j', 'password'],
            'NEO4J_URI': ['database', 'neo4j', 'uri'],
            'NEO4J_USER': ['database', 'neo4j', 'user'],
            'OPENROUTER_API_KEY': ['llm', 'chat', 'api_key'],
            'OPENROUTER_MODEL': ['llm', 'chat', 'model'],
            'LOG_LEVEL': ['logging', 'level'],
            'DEBUG': ['app', 'debug'],
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # 处理布尔值
                if env_var == 'DEBUG':
                    env_value = env_value.lower() in ('true', '1', 'yes', 'on')

                # 设置配置值
                current = config_data
                for key in config_path[:-1]:
                    current = current.setdefault(key, {})
                current[config_path[-1]] = env_value

        return config_data

    def _create_config_objects(self, config_data: Dict[str, Any]) -> Config:
        """创建配置对象"""
        # 数据库配置
        db_config = config_data.get('database', {})
        neo4j_config = db_config.get('neo4j', {})
        sqlite_config = db_config.get('sqlite', {})

        database = DatabaseConfig(
            neo4j_uri=neo4j_config.get('uri', 'bolt://localhost:7687'),
            neo4j_user=neo4j_config.get('user', 'neo4j'),
            neo4j_password=neo4j_config.get('password', ''),
            neo4j_database=neo4j_config.get('database', 'neo4j'),
            sqlite_path=sqlite_config.get('path', './data/metadata.db')
        )

        # 向量存储配置
        vs_config = config_data.get('vector_store', {})
        chroma_config = vs_config.get('chroma', {})

        vector_store = VectorStoreConfig(
            chroma_persist_directory=chroma_config.get('persist_directory', './data/chroma'),
            chroma_collection_name=chroma_config.get('collection_name', 'code_embeddings')
        )

        # LLM配置
        llm_config = config_data.get('llm', {})
        embedding_config = llm_config.get('embedding', {})
        chat_config = llm_config.get('chat', {})

        llm = LLMConfig(
            embedding_model_name=embedding_config.get('model_name', 'jinaai/jina-embeddings-v2-base-code'),
            embedding_cache_dir=embedding_config.get('cache_dir', '~/.cache/torch/sentence_transformers/'),
            embedding_batch_size=embedding_config.get('batch_size', 32),
            chat_api_key=chat_config.get('api_key', ''),
            chat_base_url=chat_config.get('base_url', 'https://openrouter.ai/api/v1/chat/completions'),
            chat_model=chat_config.get('model', 'google/gemini-2.0-flash-001'),
            chat_max_tokens=chat_config.get('max_tokens', 8192),
            chat_temperature=chat_config.get('temperature', 1.0),
            chat_top_p=chat_config.get('top_p', 0.95)
        )

        # 解析器配置
        parser_config = config_data.get('parser', {})
        file_patterns = parser_config.get('file_patterns', {})
        options = parser_config.get('options', {})

        parser = ParserConfig(
            tree_sitter_language=parser_config.get('tree_sitter', {}).get('language', 'c'),
            include_patterns=file_patterns.get('include', ['*.c', '*.h']),
            exclude_patterns=file_patterns.get('exclude', ['*test*', '*example*', '*.bak']),
            max_file_size=options.get('max_file_size', 10485760),
            encoding=options.get('encoding', 'utf-8')
        )

        # 日志配置
        logging_config = config_data.get('logging', {})
        file_config = logging_config.get('file', {})
        console_config = logging_config.get('console', {})

        logging = LoggingConfig(
            level=logging_config.get('level', 'INFO'),
            format=logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            file_enabled=file_config.get('enabled', True),
            file_path=file_config.get('path', './logs/code_learner.log'),
            file_max_size=file_config.get('max_size', '10MB'),
            file_backup_count=file_config.get('backup_count', 5),
            console_enabled=console_config.get('enabled', True),
            console_level=console_config.get('level', 'INFO')
        )

        # 性能配置
        perf_config = config_data.get('performance', {})
        cache_config = perf_config.get('cache', {})
        batch_config = perf_config.get('batch', {})

        performance = PerformanceConfig(
            max_workers=perf_config.get('max_workers', 4),
            cache_enabled=cache_config.get('enabled', True),
            cache_ttl=cache_config.get('ttl', 3600),
            cache_max_size=cache_config.get('max_size', 1000),
            embedding_batch_size=batch_config.get('embedding_batch_size', 32),
            parsing_batch_size=batch_config.get('parsing_batch_size', 10)
        )

        # 应用配置
        app_config = config_data.get('app', {})

        app = AppConfig(
            name=app_config.get('name', 'C语言智能代码分析调试工具'),
            version=app_config.get('version', '0.1.0'),
            data_dir=app_config.get('data_dir', './data'),
            logs_dir=app_config.get('logs_dir', './logs'),
            cache_dir=app_config.get('cache_dir', './cache'),
            debug=app_config.get('debug', False),
            verbose=app_config.get('verbose', False)
        )

        return Config(
            database=database,
            vector_store=vector_store,
            llm=llm,
            parser=parser,
            logging=logging,
            performance=performance,
            app=app
        )

    def _validate_config(self, config: Config) -> None:
        """验证配置"""
        # 验证必需的API密钥
        if not config.llm.chat_api_key:
            print("警告: OpenRouter API Key未设置，请设置环境变量 OPENROUTER_API_KEY")

        # 验证目录路径
        for dir_path in [config.app.data_dir, config.app.logs_dir, config.app.cache_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

        # 验证日志级别
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        if config.logging.level not in valid_levels:
            raise ConfigurationError('log_level', f"Invalid log level: {config.logging.level}")

    def get_config(self) -> Config:
        """获取当前配置"""
        if self._config is None:
            return self.load_config()
        return self._config

    def reload_config(self, config_path: Optional[Path] = None) -> Config:
        """重新加载配置"""
        self._config = None
        return self.load_config(config_path)
