"""
Neo4j图存储单元测试

测试Neo4jGraphStore类的核心功能：
- 连接管理
- 数据存储
- 错误处理
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.core.data_models import ParsedCode, Function, FileInfo
from src.code_learner.core.exceptions import StorageError


class TestNeo4jGraphStore:
    """Neo4j图存储测试类"""

    def setup_method(self):
        """每个测试前的设置"""
        self.store = Neo4jGraphStore()

    def teardown_method(self):
        """每个测试后的清理"""
        if hasattr(self.store, 'driver') and self.store.driver:
            self.store.driver.close()

    def test_connection_success(self):
        """测试成功连接Neo4j数据库"""
        with patch('src.code_learner.storage.neo4j_store.GraphDatabase') as mock_db:
            mock_driver = Mock()
            mock_driver.verify_connectivity.return_value = None
            mock_db.driver.return_value = mock_driver

            result = self.store.connect("bolt://localhost:7687", "neo4j", "password")

            assert result is True
            assert self.store.driver is not None
            mock_db.driver.assert_called_once()
            mock_driver.verify_connectivity.assert_called_once()

    def test_connection_failure(self):
        """测试连接失败的情况"""
        with patch('src.code_learner.storage.neo4j_store.GraphDatabase') as mock_db:
            mock_db.driver.side_effect = Exception("Connection failed")

            result = self.store.connect("bolt://localhost:7687", "neo4j", "wrong_password")

            assert result is False
            assert self.store.driver is None

    def test_store_parsed_code_success(self):
        """测试成功存储ParsedCode数据"""
        from datetime import datetime
        
        # 准备测试数据
        file_info = FileInfo(
            path="/test/example.c",
            name="example.c",
            size=1024,
            last_modified=datetime.now()
        )
        
        functions = [
            Function(
                name="main",
                code="int main() { return 0; }",
                start_line=10,
                end_line=20,
                file_path="/test/example.c"
            ),
            Function(
                name="helper",
                code="void helper() {}",
                start_line=5,
                end_line=8,
                file_path="/test/example.c"
            )
        ]
        
        parsed_code = ParsedCode(
            file_info=file_info,
            functions=functions
        )

        # Mock Neo4j操作
        with patch.object(self.store, 'driver') as mock_driver:
            mock_session = Mock()
            mock_tx = Mock()
            mock_driver.session.return_value.__enter__.return_value = mock_session
            mock_session.execute_write.return_value = True

            result = self.store.store_parsed_code(parsed_code)

            assert result is True
            mock_driver.session.assert_called_once()
            mock_session.execute_write.assert_called_once()

    def test_store_parsed_code_without_connection(self):
        """测试未连接时存储数据应该失败"""
        from datetime import datetime
        
        file_info = FileInfo(path="/test/example.c", name="example.c", size=1024, last_modified=datetime.now())
        parsed_code = ParsedCode(file_info=file_info, functions=[])

        with pytest.raises(StorageError) as exc_info:
            self.store.store_parsed_code(parsed_code)
        
        assert "not connected" in str(exc_info.value).lower()

    def test_clear_database_success(self):
        """测试成功清空数据库"""
        with patch.object(self.store, 'driver') as mock_driver:
            mock_session = Mock()
            mock_driver.session.return_value.__enter__.return_value = mock_session
            mock_session.execute_write.return_value = True

            result = self.store.clear_database()

            assert result is True
            mock_session.execute_write.assert_called_once()

    def test_clear_database_without_connection(self):
        """测试未连接时清空数据库应该失败"""
        with pytest.raises(StorageError) as exc_info:
            self.store.clear_database()
        
        assert "not connected" in str(exc_info.value).lower()

    def test_transaction_error_handling(self):
        """测试事务错误处理"""
        from datetime import datetime
        
        file_info = FileInfo(path="/test/example.c", name="example.c", size=1024, last_modified=datetime.now())
        parsed_code = ParsedCode(file_info=file_info, functions=[])

        with patch.object(self.store, 'driver') as mock_driver:
            mock_session = Mock()
            mock_driver.session.return_value.__enter__.return_value = mock_session
            mock_session.execute_write.side_effect = Exception("Transaction failed")

            with pytest.raises(StorageError) as exc_info:
                self.store.store_parsed_code(parsed_code)
            
            assert "transaction failed" in str(exc_info.value).lower()

    def test_context_manager_resource_cleanup(self):
        """测试资源正确清理"""
        with patch('src.code_learner.storage.neo4j_store.GraphDatabase') as mock_db:
            mock_driver = Mock()
            mock_driver.verify_connectivity.return_value = None
            mock_db.driver.return_value = mock_driver

            # 连接成功
            self.store.connect("bolt://localhost:7687", "neo4j", "password")
            assert self.store.driver is not None

            # 关闭连接
            self.store.close()
            mock_driver.close.assert_called_once()
            assert self.store.driver is None 