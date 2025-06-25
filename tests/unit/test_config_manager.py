"""配置管理器单元测试

测试ConfigManager类的功能
"""
import os
import pytest
import yaml
import tempfile
from pathlib import Path
# 移除mock导入，改用真实API测试
# from unittest.mock import patch

from src.code_learner.config.config_manager import ConfigManager, Config
from src.code_learner.core.exceptions import ConfigurationError


class TestConfigManager:
    """ConfigManager测试类"""
    
    def setup_method(self):
        """每个测试前的设置"""
        # 重置单例
        ConfigManager._instance = None
        ConfigManager._config = None
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        
        assert manager1 is manager2
    
    def test_load_default_config(self):
        """测试加载默认配置"""
        manager = ConfigManager()
        config = manager.get_config()
        
        # 验证配置对象
        assert isinstance(config, Config)
        assert hasattr(config, 'database')
        assert hasattr(config, 'llm')
        assert hasattr(config, 'parser')
        assert hasattr(config, 'logging')
        assert hasattr(config, 'app')
    
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
            # 保存当前环境变量
            original_env = {}
            for key in ['NEO4J_PASSWORD', 'OPENROUTER_API_KEY', 'LOG_LEVEL', 'DEBUG']:
                if key in os.environ:
                    original_env[key] = os.environ[key]
            
            # 设置测试环境变量
            os.environ['NEO4J_PASSWORD'] = 'env_password'
            os.environ['OPENROUTER_API_KEY'] = 'env_api_key'
            os.environ['LOG_LEVEL'] = 'DEBUG'
            os.environ['DEBUG'] = 'true'
            
            # 使用真实环境变量测试
            manager = ConfigManager()
            config = manager.load_config(Path(temp_path))
            
            # 验证环境变量覆盖
            assert config.database.neo4j_password == 'env_password'
            assert config.llm.chat_api_key == 'env_api_key'
            assert config.logging.level == 'DEBUG'
            assert config.app.debug is True
            
            # 恢复原始环境变量
            for key in ['NEO4J_PASSWORD', 'OPENROUTER_API_KEY', 'LOG_LEVEL', 'DEBUG']:
                if key in original_env:
                    os.environ[key] = original_env[key]
                else:
                    del os.environ[key]
                
        finally:
            os.unlink(temp_path)
    
    def test_config_validation(self):
        """测试配置验证"""
        manager = ConfigManager()
        
        # 创建无效配置文件 - 使用不存在的日志级别
        config_data = {
            'database': {'neo4j': {'uri': 'bolt://localhost:7687', 'user': 'neo4j', 'password': 'test'}},
            'vector_store': {'chroma': {'persist_directory': './test_chroma'}},
            'llm': {'embedding': {'model_name': 'test-model'}, 'chat': {'api_key': 'test-key'}},
            'parser': {'tree_sitter': {'language': 'c'}},
            'logging': {'level': 'INVALID_LEVEL'},  # 无效的日志级别
            'performance': {'max_workers': 2},
            'app': {'name': 'Test App', 'version': '0.1.0'}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
            
        print(f"\n调试: 创建的配置文件路径: {temp_path}")
        print(f"调试: 配置文件内容: {config_data}")
        
        try:
            # 保存当前环境变量
            original_env = {}
            env_keys = ['NEO4J_PASSWORD', 'OPENROUTER_API_KEY', 'LOG_LEVEL', 'DEBUG']
            for key in env_keys:
                if key in os.environ:
                    original_env[key] = os.environ[key]
                    del os.environ[key]
            
            # 使用真实环境测试配置验证
            try:
                # 添加调试输出
                print("\n调试: 尝试加载无效配置...")
                config = manager.load_config(Path(temp_path))
                print(f"调试: 配置加载成功，日志级别为: {config.logging.level}")
                
                # 检查配置管理器内部方法
                print(f"调试: 直接从文件读取配置...")
                with open(temp_path, 'r') as f:
                    raw_config = yaml.safe_load(f)
                print(f"调试: 文件中的日志级别: {raw_config['logging']['level']}")
                
                assert False, "应该抛出ConfigurationError异常，但没有"
            except ConfigurationError as e:
                print(f"调试: 正确捕获到异常: {e}")
                assert 'log_level' in str(e).lower()
            
            # 恢复原始环境变量
            for key, value in original_env.items():
                os.environ[key] = value
            
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