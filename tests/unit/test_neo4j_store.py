"""
Neo4j图存储单元测试

测试Neo4jGraphStore类的核心功能：
- 真实数据库连接
- 数据存储和查询
- 错误处理
"""

import pytest
from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.core.data_models import ParsedCode, Function, FileInfo
from src.code_learner.core.exceptions import StorageError
from src.code_learner.config.config_manager import ConfigManager
from datetime import datetime


class TestNeo4jGraphStore:
    """Neo4j图存储测试类 - 使用真实数据库"""

    @classmethod
    def setup_class(cls):
        """测试类设置 - 加载配置"""
        cls.config_manager = ConfigManager()
        cls.config = cls.config_manager.load_config()

    def setup_method(self):
        """每个测试前的设置"""
        self.store = Neo4jGraphStore()

    def teardown_method(self):
        """每个测试后的清理"""
        if hasattr(self.store, 'driver') and self.store.driver:
            # 清理测试数据
            try:
                self.store.clear_database()
            except:
                pass
            self.store.close()

    def test_connection_success(self):
        """测试成功连接Neo4j数据库"""
        result = self.store.connect(
            self.config.database.neo4j_uri,
            self.config.database.neo4j_user,
            self.config.database.neo4j_password
        )

        assert result is True
        assert self.store.driver is not None

    def test_connection_failure(self):
        """测试连接失败的情况"""
        # 连接失败应该抛出StorageError异常，而不是返回False
        with pytest.raises(StorageError):
            self.store.connect(
                "bolt://localhost:9999",  # 错误的端口
                "neo4j", 
                "wrong_password"
            )

        assert self.store.driver is None

    def test_store_parsed_code_success(self):
        """测试成功存储ParsedCode数据"""
        # 先连接数据库
        success = self.store.connect(
            self.config.database.neo4j_uri,
            self.config.database.neo4j_user,
            self.config.database.neo4j_password
        )
        assert success, "Failed to connect to database"
        
        # 清空数据库
        self.store.clear_database()
        
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

        # 存储数据
        result = self.store.store_parsed_code(parsed_code)
        assert result is True
        
        # 验证数据确实存储了
        with self.store.driver.session() as session:
            # 验证文件节点
            file_result = session.run("MATCH (f:File {path: $path}) RETURN f", path="/test/example.c")
            file_records = list(file_result)
            assert len(file_records) == 1
            
            # 验证函数节点
            func_result = session.run("MATCH (fn:Function) RETURN fn.name as name")
            func_records = list(func_result)
            assert len(func_records) == 2
            
            func_names = [record["name"] for record in func_records]
            assert "main" in func_names
            assert "helper" in func_names

    def test_store_parsed_code_without_connection(self):
        """测试未连接时存储数据应该失败"""
        file_info = FileInfo(
            path="/test/example.c", 
            name="example.c", 
            size=1024, 
            last_modified=datetime.now()
        )
        parsed_code = ParsedCode(file_info=file_info, functions=[])

        with pytest.raises(StorageError) as exc_info:
            self.store.store_parsed_code(parsed_code)
        
        assert "not connected" in str(exc_info.value).lower()

    def test_clear_database_success(self):
        """测试成功清空数据库"""
        # 先连接数据库
        success = self.store.connect(
            self.config.database.neo4j_uri,
            self.config.database.neo4j_user,
            self.config.database.neo4j_password
        )
        assert success, "Failed to connect to database"
        
        # 添加一些测试数据
        file_info = FileInfo(
            path="/test/clear_test.c",
            name="clear_test.c",
            size=100,
            last_modified=datetime.now()
        )
        functions = [Function("test_func", "void test_func() {}", 1, 3, "/test/clear_test.c")]
        parsed_code = ParsedCode(file_info=file_info, functions=functions)
        
        self.store.store_parsed_code(parsed_code)
        
        # 验证数据存在
        with self.store.driver.session() as session:
            count_result = session.run("MATCH (n) RETURN count(n) as count")
            count_before = count_result.single()["count"]
            assert count_before > 0, "Should have some data before clearing"
        
        # 清空数据库
        result = self.store.clear_database()
        assert result is True
        
        # 验证数据已清空
        with self.store.driver.session() as session:
            count_result = session.run("MATCH (n) RETURN count(n) as count")
            count_after = count_result.single()["count"]
            assert count_after == 0, "Should have no data after clearing"

    def test_clear_database_without_connection(self):
        """测试未连接时清空数据库应该失败"""
        with pytest.raises(StorageError) as exc_info:
            self.store.clear_database()
        
        assert "not connected" in str(exc_info.value).lower()

    def test_context_manager_resource_cleanup(self):
        """测试资源正确清理"""
        # 连接成功
        success = self.store.connect(
            self.config.database.neo4j_uri,
            self.config.database.neo4j_user,
            self.config.database.neo4j_password
        )
        assert success, "Failed to connect to database"
        assert self.store.driver is not None

        # 关闭连接
        self.store.close()
        assert self.store.driver is None 