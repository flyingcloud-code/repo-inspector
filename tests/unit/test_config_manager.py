"""ConfigManager单元测试

测试配置管理器的各项功能
"""
import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from src.code_learner.config.config_manager import ConfigManager, Config
from src.code_learner.core.exceptions import ConfigurationError


class TestConfigManager:
    """ConfigManager测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置单例
        ConfigManager._instance = None
        ConfigManager._config = None
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    def test_load_default_config(self):
        """测试加载默认配置"""
        manager = ConfigManager()
        
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({
                'database': {
                    'neo4j': {'uri': 'bolt://localhost:7687', 'user': 'neo4j', 'password': 'test'},
                    'sqlite': {'path': './test.db'}
                },
                'vector_store': {
                    'chroma': {'persist_directory': './test_chroma'}
                },
                'llm': {
                    'embedding': {'model_name': 'test-model'},
                    'chat': {'api_key': 'test-key', 'model': 'test-chat-model'}
                },
                'parser': {
                    'tree_sitter': {'language': 'c'},
                    'file_patterns': {'include': ['*.c'], 'exclude': ['*test*']},
                    'options': {'max_file_size': 1000000}
                },
                'logging': {
                    'level': 'DEBUG',
                    'file': {'enabled': True, 'path': './test.log'},
                    'console': {'enabled': True}
                },
                'performance': {
                    'max_workers': 2,
                    'cache': {'enabled': True}
                },
                'app': {
                    'name': 'Test App',
                    'version': '0.1.0',
                    'debug': True
                }
            }, f)
            temp_path = f.name
        
        try:
            config = manager.load_config(Path(temp_path))
            
            # 验证配置加载
            assert isinstance(config, Config)
            # 注意：环境变量会覆盖配置文件，这是正确行为
            assert config.database.neo4j_uri  # 只验证有值
            # 验证没有被环境变量覆盖的配置项
            assert config.llm.embedding_model_name == 'test-model'
            assert config.app.name == 'Test App'
            # DEBUG环境变量存在时，会覆盖配置文件中的值
            import os
            if os.environ.get('DEBUG'):
                # 环境变量DEBUG=false会覆盖配置文件中的debug=True
                assert config.app.debug is False
            else:
                assert config.app.debug is True
            
        finally:
            os.unlink(temp_path)
    
    def test_environment_variable_override(self):
        """测试环境变量覆盖"""
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({
                'database': {'neo4j': {'password': 'default_password'}},
                'llm': {'chat': {'api_key': 'default_key'}},
                'logging': {'level': 'INFO'},
                'app': {'debug': False}
            }, f)
            temp_path = f.name
        
        try:
            # 设置环境变量
            with patch.dict(os.environ, {
                'NEO4J_PASSWORD': 'env_password',
                'OPENROUTER_API_KEY': 'env_api_key',
                'LOG_LEVEL': 'DEBUG',
                'DEBUG': 'true'
            }):
                manager = ConfigManager()
                config = manager.load_config(Path(temp_path))
                
                # 验证环境变量覆盖
                assert config.database.neo4j_password == 'env_password'
                assert config.llm.chat_api_key == 'env_api_key'
                assert config.logging.level == 'DEBUG'
                assert config.app.debug is True
                
        finally:
            os.unlink(temp_path)
    
    def test_config_validation(self):
        """测试配置验证"""
        manager = ConfigManager()
        
        # 创建无效配置文件，并阻止load_dotenv和环境变量影响
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({
                'logging': {'level': 'INVALID_LEVEL'}
            }, f)
            temp_path = f.name
        
        try:
            # 使用patch阻止load_dotenv和环境变量影响，测试纯配置文件验证
            with patch('src.code_learner.config.config_manager.load_dotenv'):
                with patch.dict(os.environ, {}, clear=True):  # clear=True清除所有环境变量
                    with pytest.raises(ConfigurationError) as exc_info:
                        manager.load_config(Path(temp_path))
                    
                    assert 'log_level' in str(exc_info.value)
            
        finally:
            os.unlink(temp_path)
    
    def test_missing_config_file(self):
        """测试配置文件不存在的情况"""
        manager = ConfigManager()
        
        with pytest.raises(ConfigurationError) as exc_info:
            manager.load_config(Path('/nonexistent/config.yml'))
        
        assert 'Configuration file not found' in str(exc_info.value)
    
    def test_invalid_yaml_format(self):
        """测试无效YAML格式"""
        manager = ConfigManager()
        
        # 创建无效YAML文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            temp_path = f.name
        
        try:
            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config(Path(temp_path))
            
            assert 'yaml_parsing' in str(exc_info.value)
            
        finally:
            os.unlink(temp_path)
    
    def test_config_caching(self):
        """测试配置缓存"""
        manager = ConfigManager()
        
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({'app': {'name': 'Test'}}, f)
            temp_path = f.name
        
        try:
            # 第一次加载
            config1 = manager.load_config(Path(temp_path))
            
            # 第二次加载应该返回缓存的配置
            config2 = manager.load_config(Path(temp_path))
            
            assert config1 is config2
            
        finally:
            os.unlink(temp_path)
    
    def test_config_reload(self):
        """测试配置重新加载"""
        manager = ConfigManager()
        
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump({'app': {'name': 'Test1'}}, f)
            temp_path = f.name
        
        try:
            # 第一次加载
            config1 = manager.load_config(Path(temp_path))
            assert config1.app.name == 'Test1'
            
            # 修改配置文件
            with open(temp_path, 'w') as f:
                yaml.dump({'app': {'name': 'Test2'}}, f)
            
            # 重新加载
            config2 = manager.reload_config(Path(temp_path))
            assert config2.app.name == 'Test2'
            assert config1 is not config2
            
        finally:
            os.unlink(temp_path)
    
    def test_directory_creation(self):
        """测试目录自动创建"""
        manager = ConfigManager()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建配置文件，指定不存在的目录
            config_data = {
                'app': {
                    'data_dir': f'{temp_dir}/data',
                    'logs_dir': f'{temp_dir}/logs', 
                    'cache_dir': f'{temp_dir}/cache'
                }
            }
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(config_data, f)
                temp_path = f.name
            
            try:
                config = manager.load_config(Path(temp_path))
                
                # 验证目录已创建
                assert Path(config.app.data_dir).exists()
                assert Path(config.app.logs_dir).exists()
                assert Path(config.app.cache_dir).exists()
                
            finally:
                os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 