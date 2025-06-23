"""
Story 1.3 验收测试

测试Neo4j图存储的端到端功能：
- 真实数据库连接
- 完整数据存储流程
- 数据验证和查询
"""

import pytest
from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.parser.c_parser import CParser
from src.code_learner.config.config_manager import ConfigManager
from src.code_learner.core.data_models import ParsedCode, Function, FileInfo
import tempfile
import os
from datetime import datetime
from pathlib import Path


class TestStory13Acceptance:
    """Story 1.3 验收测试类"""

    @classmethod
    def setup_class(cls):
        """测试类设置 - 加载配置"""
        cls.config_manager = ConfigManager()
        cls.config = cls.config_manager.load_config()
        cls.store = Neo4jGraphStore()
        cls.parser = CParser()

    def setup_method(self):
        """每个测试前的设置"""
        # 连接到Neo4j数据库
        success = self.store.connect(
            self.config.database.neo4j_uri,
            self.config.database.neo4j_user,
            self.config.database.neo4j_password
        )
        assert success, "Failed to connect to Neo4j database"
        
        # 清空数据库确保测试独立性
        self.store.clear_database()

    def teardown_method(self):
        """每个测试后的清理"""
        # 清空测试数据
        if hasattr(self.store, 'driver') and self.store.driver:
            self.store.clear_database()

    @classmethod
    def teardown_class(cls):
        """测试类清理"""
        if hasattr(cls.store, 'driver') and cls.store.driver:
            cls.store.close()

    def test_ac1_neo4j_connection_and_basic_operations(self):
        """验收标准1: Neo4j连接和基本操作"""
        # 测试连接
        assert self.store.driver is not None, "Neo4j driver should be connected"
        
        # 测试基本操作 - 清空数据库
        result = self.store.clear_database()
        assert result is True, "Clear database should succeed"

    def test_ac2_store_file_and_function_nodes(self):
        """验收标准2: 存储File和Function节点"""
        # 准备测试数据
        file_info = FileInfo(
            path="test_example.c",
            name="test_example.c", 
            size=256,
            last_modified=datetime.now()
        )
        
        functions = [
            Function(
                name="test_function",
                code="int test_function() { return 42; }",
                start_line=1,
                end_line=5,
                file_path="test_example.c"
            ),
            Function(
                name="main",
                code="int main() { return test_function(); }",
                start_line=7,
                end_line=10,
                file_path="test_example.c"
            )
        ]
        
        parsed_code = ParsedCode(file_info=file_info, functions=functions)
        
        # 存储数据
        result = self.store.store_parsed_code(parsed_code)
        assert result is True, "Store parsed code should succeed"
        
        # 验证数据存储 - 通过Cypher查询验证
        with self.store.driver.session() as session:
            # 验证文件节点
            file_result = session.run("MATCH (f:File {path: $path}) RETURN f", path="test_example.c")
            file_records = list(file_result)
            assert len(file_records) == 1, "Should have exactly one File node"
            
            # 验证函数节点
            func_result = session.run("MATCH (fn:Function) RETURN fn.name as name ORDER BY fn.name")
            func_records = list(func_result)
            assert len(func_records) == 2, "Should have exactly two Function nodes"
            
            func_names = [record["name"] for record in func_records]
            assert "main" in func_names, "Should have main function"
            assert "test_function" in func_names, "Should have test_function"

    def test_ac3_create_contains_relationship(self):
        """验收标准3: 创建CONTAINS关系 (File包含Function)"""
        # 准备和存储测试数据
        file_info = FileInfo(
            path="contains_test.c", 
            name="contains_test.c", 
            size=128, 
            last_modified=datetime.now()
        )
        functions = [
            Function(
                name="helper_func", 
                code="void helper_func() {}", 
                start_line=1, 
                end_line=3, 
                file_path="contains_test.c"
            )
        ]
        parsed_code = ParsedCode(file_info=file_info, functions=functions)
        
        # 存储数据
        result = self.store.store_parsed_code(parsed_code)
        assert result is True, "Store parsed code should succeed"
        
        # 验证CONTAINS关系
        with self.store.driver.session() as session:
            relationship_result = session.run("""
                MATCH (f:File {path: $path})-[:CONTAINS]->(fn:Function {name: $func_name})
                RETURN f.path as file_path, fn.name as func_name
            """, path="contains_test.c", func_name="helper_func")
            
            relationship_records = list(relationship_result)
            assert len(relationship_records) == 1, "Should have exactly one CONTAINS relationship"
            
            record = relationship_records[0]
            assert record["file_path"] == "contains_test.c", "File path should match"
            assert record["func_name"] == "helper_func", "Function name should match"

    def test_ac4_end_to_end_with_real_c_file(self):
        """验收标准4: 端到端测试 - 使用真实C文件"""
        # 创建临时C文件
        c_code = '''
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int main() {
    int result = add(5, 3);
    printf("Result: %d\\n", result);
    return 0;
}
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False) as f:
            f.write(c_code)
            temp_file_path = f.name
        
        try:
            # 使用CParser解析文件 - 传递Path对象
            parsed_code = self.parser.parse_file(Path(temp_file_path))
            assert parsed_code is not None, "Parser should successfully parse the file"
            assert len(parsed_code.functions) >= 2, "Should parse at least 2 functions (add, main)"
            
            # 存储到Neo4j
            result = self.store.store_parsed_code(parsed_code)
            assert result is True, "Should successfully store parsed code"
            
            # 验证完整数据流
            with self.store.driver.session() as session:
                # 验证文件和函数都存储了
                count_result = session.run("""
                    MATCH (f:File)-[:CONTAINS]->(fn:Function)
                    RETURN count(*) as relationship_count
                """)
                count_record = count_result.single()
                assert count_record["relationship_count"] >= 2, "Should have at least 2 file-function relationships"
                
                # 验证具体函数存在
                func_result = session.run("MATCH (fn:Function) RETURN fn.name as name")
                func_names = [record["name"] for record in func_result]
                assert "add" in func_names, "Should have 'add' function"
                assert "main" in func_names, "Should have 'main' function"
        
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path) 