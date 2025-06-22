"""包导入测试

验证所有包和模块能正确导入
"""
import pytest


class TestPackageImports:
    """包导入测试类"""
    
    def test_main_package_import(self):
        """测试主包导入"""
        import src.code_learner
        
        # 验证版本信息
        assert hasattr(src.code_learner, '__version__')
        assert hasattr(src.code_learner, 'get_version')
        assert src.code_learner.get_version() == src.code_learner.__version__
    
    def test_config_package_import(self):
        """测试配置包导入"""
        from src.code_learner.config import config_manager
        from src.code_learner.config.config_manager import ConfigManager, Config
        
        # 验证类可以实例化
        manager = ConfigManager()
        assert manager is not None
    
    def test_core_package_import(self):
        """测试核心包导入"""
        # 数据模型导入
        from src.code_learner.core.data_models import (
            Function, FileInfo, ParsedCode, EmbeddingData, QueryResult, AnalysisSession
        )
        
        # 接口导入
        from src.code_learner.core.interfaces import (
            IParser, IGraphStore, IVectorStore, IEmbeddingEngine, IChatBot
        )
        
        # 异常导入
        from src.code_learner.core.exceptions import (
            CodeLearnerError, ParseError, DatabaseConnectionError,
            ConfigurationError, ModelLoadError
        )
        
        # 验证类存在
        assert Function is not None
        assert IParser is not None
        assert CodeLearnerError is not None
    
    def test_utils_package_import(self):
        """测试工具包导入"""
        from src.code_learner.utils.logger import LoggerManager, get_logger
        
        # 验证日志器可以获取
        logger = get_logger(__name__)
        assert logger is not None
    
    def test_empty_packages_import(self):
        """测试空包导入"""
        # 这些包目前只有__init__.py文件
        import src.code_learner.parser
        import src.code_learner.storage
        import src.code_learner.llm
        import src.code_learner.cli
        
        # 验证包可以导入
        assert src.code_learner.parser is not None
        assert src.code_learner.storage is not None
        assert src.code_learner.llm is not None
        assert src.code_learner.cli is not None
    
    def test_main_package_exports(self):
        """测试主包导出"""
        from src.code_learner import (
            ConfigManager, Config, Function, FileInfo, ParsedCode,
            EmbeddingData, QueryResult, IParser, IGraphStore,
            CodeLearnerError, get_logger, setup_environment
        )
        
        # 验证所有导出都可用
        assert ConfigManager is not None
        assert Function is not None
        assert IParser is not None
        assert CodeLearnerError is not None
        assert get_logger is not None
        assert setup_environment is not None
    
    def test_setup_environment(self):
        """测试环境设置函数"""
        from src.code_learner import setup_environment
        
        # 应该能正常调用而不出错
        try:
            setup_environment()
        except Exception as e:
            pytest.fail(f"setup_environment调用失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 