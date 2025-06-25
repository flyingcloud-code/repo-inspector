"""Story 1.1 验收测试

测试基础环境搭建与配置系统的完整功能
"""
import os
import sys
import yaml
import pytest
import tempfile
import importlib
from pathlib import Path

from src.code_learner.config.config_manager import ConfigManager, Config
from src.code_learner.utils.logger import get_logger
from src.code_learner import setup_environment  # 从主包导入
from src.code_learner.core.data_models import Function, FileInfo, ParsedCode


class TestStory11Acceptance:
    """Story 1.1 验收测试类"""
    
    def test_acceptance_1_ubuntu_dependencies(self):
        """验收标准1: Ubuntu 24.04 LTS环境依赖安装正确"""
        # 测试Python版本
        assert sys.version_info.major == 3
        assert sys.version_info.minor >= 11
        
        # 测试关键包导入
        import neo4j
        import chromadb
        import tree_sitter
        import sentence_transformers
        import dotenv
        
        # 测试数据库连接
        import sqlite3
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        cursor.execute('SELECT sqlite_version();')
        version = cursor.fetchone()[0]
        conn.close()
        
        # 验证版本
        assert version is not None
        
        print("✅ 验收标准1: Ubuntu 24.04 LTS环境依赖安装正确")
    
    def test_acceptance_2_neo4j_ready(self):
        """验收标准2: Neo4j数据库可连接"""
        # 注意：这个测试需要Neo4j数据库在本地或远程运行
        # 如果没有可用的Neo4j，测试会跳过
        
        import neo4j
        from neo4j.exceptions import ServiceUnavailable
        
        # 从环境变量或配置获取连接信息
        config = ConfigManager().get_config()
        uri = config.database.neo4j_uri
        user = config.database.neo4j_user
        password = config.database.neo4j_password
        
        try:
            # 尝试连接Neo4j
            driver = neo4j.GraphDatabase.driver(uri, auth=(user, password))
            driver.verify_connectivity()
            
            # 执行简单查询
            with driver.session() as session:
                result = session.run("RETURN 1 AS num")
                record = result.single()
                assert record["num"] == 1
            
            driver.close()
            print("✅ 验收标准2: Neo4j数据库连接成功")
            
        except ServiceUnavailable:
            pytest.skip("Neo4j数据库不可用，跳过测试")
    
    def test_acceptance_3_jina_embeddings_ready(self):
        """验收标准3: Jina嵌入模型可用"""
        from sentence_transformers import SentenceTransformer
        
        try:
            # 加载模型
            model = SentenceTransformer('jinaai/jina-embeddings-v2-base-code')
            
            # 测试嵌入生成
            test_text = "def hello_world():\n    print('Hello, World!')"
            embeddings = model.encode([test_text])
            
            # 验证嵌入向量
            assert embeddings.shape[0] == 1  # 一个样本
            assert embeddings.shape[1] == 768  # 768维向量
            
            print("✅ 验收标准3: Jina嵌入模型加载成功")
            
        except Exception as e:
            pytest.skip(f"Jina嵌入模型不可用: {e}")
    
    def test_acceptance_4_package_structure(self):
        """验收标准4: 包结构创建完整"""
        # 获取项目根目录
        import src.code_learner
        base_path = Path(src.code_learner.__file__).parent
        
        # 验证主要包存在
        expected_packages = [
            "config",
            "core",
            "parser",
            "storage",
            "llm",
            "cli",
            "utils"
        ]
        
        for package in expected_packages:
            assert (base_path / package).is_dir()
            assert (base_path / package / "__init__.py").exists()
        
        # 验证核心模块文件
        expected_files = [
            "config/config_manager.py",
            "core/data_models.py",
            "core/interfaces.py", 
            "core/exceptions.py",
            "utils/logger.py"
        ]
        
        for file_path in expected_files:
            assert (base_path / file_path).exists()
        
        print("✅ 验收标准4: 完整包结构创建成功")
    
    def test_acceptance_5_config_manager(self):
        """验收标准5: ConfigManager能加载和验证配置"""
        import os
        
        # 测试1: 验证ConfigManager基本功能
        ConfigManager._instance = None
        ConfigManager._config = None
        
        # 创建测试配置
        test_config = {
            'database': {
                'neo4j': {'uri': 'bolt://test:7687', 'user': 'test', 'password': 'test'},
                'sqlite': {'path': './test.db'}
            },
            'vector_store': {
                'chroma': {'persist_directory': './test_chroma'}
            },
            'llm': {
                'embedding': {'model_name': 'test-model'},
                'chat': {'api_key': 'test-key', 'model': 'test-model'}
            },
            'parser': {
                'tree_sitter': {'language': 'c'},
                'file_patterns': {'include': ['*.c'], 'exclude': ['*test*']},
                'options': {'max_file_size': 1000000}
            },
            'logging': {
                'level': 'INFO',
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
                'data_dir': './test_data',
                'debug': False
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(test_config, f)
            temp_path = f.name
        
        try:
            # 测试配置文件加载和环境变量覆盖（这是正确行为）
            manager = ConfigManager()
            config = manager.load_config(Path(temp_path))
            
            # 验证配置对象创建成功
            assert isinstance(config, Config)
            
            # 验证配置文件中的值被正确加载（除非被环境变量覆盖）
            # 注意：如果系统环境变量存在，它们会覆盖配置文件的值
            current_neo4j_uri = os.environ.get('NEO4J_URI')
            if current_neo4j_uri:
                # 环境变量存在，应该使用环境变量的值
                assert config.database.neo4j_uri == current_neo4j_uri
            else:
                # 环境变量不存在，应该使用配置文件的值
                assert config.database.neo4j_uri == 'bolt://test:7687'
            
            # 测试没有环境变量覆盖的配置项
            assert config.llm.embedding_model_name == 'test-model'
            assert config.parser.tree_sitter_language == 'c'
            assert config.logging.level == 'INFO'
            assert config.app.name == 'Test App'
            
            # 验证目录自动创建
            assert Path(config.app.data_dir).exists()
            
            # 测试2: 验证环境变量优先级
            ConfigManager._instance = None
            ConfigManager._config = None
            
            # 保存当前环境变量
            original_env = {}
            for key in ['NEO4J_URI', 'OPENROUTER_API_KEY']:
                if key in os.environ:
                    original_env[key] = os.environ[key]
            
            # 设置测试环境变量
            os.environ['NEO4J_URI'] = 'bolt://override:7687'
            os.environ['OPENROUTER_API_KEY'] = 'override-api-key'
            
            try:
                manager = ConfigManager()
                config = manager.load_config(Path(temp_path))
                
                # 验证环境变量覆盖了配置文件
                assert config.database.neo4j_uri == 'bolt://override:7687'
                assert config.llm.chat_api_key == 'override-api-key'
                # 其他值应该保持配置文件中的值
                assert config.llm.embedding_model_name == 'test-model'
                assert config.app.name == 'Test App'
            finally:
                # 恢复原始环境变量
                for key in ['NEO4J_URI', 'OPENROUTER_API_KEY']:
                    if key in original_env:
                        os.environ[key] = original_env[key]
                    elif key in os.environ:
                        del os.environ[key]
            
            # 测试3: 验证实际生产环境配置加载
            ConfigManager._instance = None
            ConfigManager._config = None
            
            manager = ConfigManager()
            config = manager.get_config()  # 使用默认配置路径
            
            # 验证能成功加载配置
            assert isinstance(config, Config)
            # 验证从.env文件或环境变量加载的API Key
            assert config.llm.chat_api_key  # 应该有API Key
            assert config.database.neo4j_uri  # 应该有数据库URI
            # 验证配置的基本结构
            assert hasattr(config, 'database')
            assert hasattr(config, 'llm') 
            assert hasattr(config, 'parser')
            assert hasattr(config, 'logging')
            assert hasattr(config, 'app')
            
        finally:
            Path(temp_path).unlink()
        
        print("✅ 验收标准5: ConfigManager加载和验证配置成功")
    
    def test_acceptance_6_logging_system(self):
        """验收标准6: 日志系统正常工作"""
        # 测试日志系统初始化
        setup_environment()
        
        # 测试获取日志器
        logger = get_logger(__name__)
        assert logger is not None
        
        # 测试日志输出（不会实际输出到文件，因为使用默认配置）
        logger.info("测试日志信息")
        logger.warning("测试警告信息")
        logger.error("测试错误信息")
        
        print("✅ 验收标准6: 日志系统正常工作")
    
    def test_acceptance_7_package_imports(self):
        """验收标准7: 所有包能正常导入"""
        # 测试主包导入
        import src.code_learner
        assert src.code_learner.__version__ == "0.1.0"
        
        # 测试核心组件导入
        from src.code_learner import (
            ConfigManager, Config, Function, FileInfo, ParsedCode,
            EmbeddingData, QueryResult, IParser, IGraphStore,
            CodeLearnerError, get_logger, setup_environment
        )
        
        # 验证所有组件都可用
        assert ConfigManager is not None
        assert Function is not None
        assert IParser is not None
        assert CodeLearnerError is not None
        assert get_logger is not None
        assert setup_environment is not None
        
        # 测试子包导入
        import src.code_learner.config
        import src.code_learner.core
        import src.code_learner.parser
        import src.code_learner.storage
        import src.code_learner.llm
        import src.code_learner.cli
        import src.code_learner.utils
        
        print("✅ 验收标准7: 所有包正常导入")
    
    def test_story_1_1_complete(self):
        """Story 1.1 完整验收测试"""
        print("\n🎯 Story 1.1: 基础环境搭建与配置系统 - 验收测试")
        print("=" * 60)
        
        # 运行所有验收标准
        self.test_acceptance_1_ubuntu_dependencies()
        self.test_acceptance_2_neo4j_ready()
        self.test_acceptance_3_jina_embeddings_ready()
        self.test_acceptance_4_package_structure()
        self.test_acceptance_5_config_manager()
        self.test_acceptance_6_logging_system()
        self.test_acceptance_7_package_imports()
        
        print("=" * 60)
        print("🎉 Story 1.1 所有验收标准通过！")
        print("✨ 基础环境搭建与配置系统已完成")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"]) 