"""
测试Neo4j图存储的函数代码检索和调用关系查询功能

验证Neo4j图存储的功能：
- 函数代码检索
- 函数调用关系查询
- 函数被调用关系查询
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.core.exceptions import StorageError


class TestNeo4jStoreFunctions:
    """测试Neo4j图存储的函数相关功能"""

    @pytest.fixture
    def mock_neo4j_driver(self):
        """模拟Neo4j驱动"""
        mock_driver = MagicMock()
        mock_session = MagicMock()
        
        # 使用MagicMock的__enter__和__exit__方法模拟上下文管理器
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = None
        
        mock_driver.session.return_value = mock_session
        
        return mock_driver

    def test_get_function_code_with_stored_code(self, mock_neo4j_driver):
        """测试从存储的代码获取函数代码"""
        # 创建Neo4j存储
        store = Neo4jGraphStore()
        store.driver = mock_neo4j_driver
        
        # 模拟查询结果
        mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_session.run.return_value = mock_result
        
        # 创建一个真实的字典而不是MagicMock
        record_dict = {
            "code": "int test_function() { return 0; }",
            "file_path": "/path/to/file.c",
            "start_line": 10,
            "end_line": 15
        }
        
        # 模拟record对象
        mock_record = MagicMock()
        mock_record.get.side_effect = record_dict.get
        mock_record.__getitem__.side_effect = record_dict.__getitem__
        
        mock_result.single.return_value = mock_record
        
        # 调用方法
        code = store.get_function_code("test_function")
        
        # 验证结果
        assert code == "int test_function() { return 0; }"
        
        # 验证查询
        mock_session.run.assert_called_once()
        args, kwargs = mock_session.run.call_args
        assert "MATCH (f:Function {name: $name})" in args[0]
        assert kwargs["name"] == "test_function"

    def test_get_function_code_from_file(self, mock_neo4j_driver):
        """测试从文件获取函数代码"""
        # 创建Neo4j存储
        store = Neo4jGraphStore()
        store.driver = mock_neo4j_driver
        
        # 模拟查询结果
        mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_session.run.return_value = mock_result
        
        # 创建一个真实的字典而不是MagicMock
        record_dict = {
            "code": None,
            "file_path": "/path/to/file.c",
            "start_line": 10,
            "end_line": 15
        }
        
        # 模拟record对象
        mock_record = MagicMock()
        mock_record.get.side_effect = record_dict.get
        mock_record.__getitem__.side_effect = record_dict.__getitem__
        
        mock_result.single.return_value = mock_record
        
        # 模拟_read_function_from_file方法
        with patch.object(store, '_read_function_from_file', return_value="line1\nline2\nline3\nline4\nline5\nline6"):
            # 调用方法
            code = store.get_function_code("test_function")
            
            # 验证结果
            assert code == "line1\nline2\nline3\nline4\nline5\nline6"
            
            # 验证_read_function_from_file被调用
            store._read_function_from_file.assert_called_once_with("/path/to/file.c", 10, 15)

    def test_get_function_code_not_found(self, mock_neo4j_driver):
        """测试函数不存在的情况"""
        # 创建Neo4j存储
        store = Neo4jGraphStore()
        store.driver = mock_neo4j_driver
        
        # 模拟查询结果为空
        mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_session.run.return_value = mock_result
        mock_result.single.return_value = None
        
        # 调用方法
        code = store.get_function_code("nonexistent_function")
        
        # 验证结果
        assert code is None

    def test_get_function_code_file_error(self, mock_neo4j_driver):
        """测试文件读取错误的情况"""
        # 创建Neo4j存储
        store = Neo4jGraphStore()
        store.driver = mock_neo4j_driver
        
        # 模拟查询结果
        mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_session.run.return_value = mock_result
        
        mock_record = MagicMock()
        mock_result.single.return_value = mock_record
        
        # 模拟数据库返回无代码但有文件信息
        mock_record.get.side_effect = lambda key, default=None: {
            "code": None,
            "file_path": "/path/to/file.c",
            "start_line": 10,
            "end_line": 15
        }.get(key, default)
        
        # 模拟文件读取错误
        with patch.object(store, '_read_function_from_file', return_value=None):
            # 调用方法
            code = store.get_function_code("test_function")
            
            # 验证结果
            assert code is None

    def test_query_function_calls(self, mock_neo4j_driver):
        """测试查询函数调用"""
        # 创建Neo4j存储
        store = Neo4jGraphStore()
        store.driver = mock_neo4j_driver
        
        # 模拟查询结果
        mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_session.run.return_value = mock_result
        
        # 模拟data方法返回值
        mock_result.data.return_value = [
            {"callee": "function1"},
            {"callee": "function2"},
            {"callee": "function3"}
        ]
        
        # 调用方法
        callees = store.query_function_calls("test_function")
        
        # 验证结果
        assert callees == ["function1", "function2", "function3"]
        
        # 验证查询
        mock_session.run.assert_called_once()
        args, kwargs = mock_session.run.call_args
        assert "MATCH (caller:Function {name: $name})-[:CALLS]->(callee:Function)" in args[0]
        assert kwargs["name"] == "test_function"

    def test_query_function_callers(self, mock_neo4j_driver):
        """测试查询函数被调用"""
        # 创建Neo4j存储
        store = Neo4jGraphStore()
        store.driver = mock_neo4j_driver
        
        # 模拟查询结果
        mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_session.run.return_value = mock_result
        
        # 模拟data方法返回值
        mock_result.data.return_value = [
            {"caller": "function1"},
            {"caller": "function2"},
            {"caller": "function3"}
        ]
        
        # 调用方法
        callers = store.query_function_callers("test_function")
        
        # 验证结果
        assert callers == ["function1", "function2", "function3"]
        
        # 验证查询
        mock_session.run.assert_called_once()
        args, kwargs = mock_session.run.call_args
        assert "MATCH (caller:Function)-[:CALLS]->(callee:Function {name: $name})" in args[0]
        assert kwargs["name"] == "test_function"

    def test_query_function_calls_empty(self, mock_neo4j_driver):
        """测试查询函数调用为空的情况"""
        # 创建Neo4j存储
        store = Neo4jGraphStore()
        store.driver = mock_neo4j_driver
        
        # 模拟查询结果为空
        mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
        mock_result = MagicMock()
        mock_session.run.return_value = mock_result
        mock_result.data.return_value = []
        
        # 调用方法
        callees = store.query_function_calls("test_function")
        
        # 验证结果
        assert callees == []

    def test_query_function_calls_error(self, mock_neo4j_driver):
        """测试查询函数调用错误的情况"""
        # 创建Neo4j存储
        store = Neo4jGraphStore()
        store.driver = mock_neo4j_driver
        
        # 模拟查询错误
        mock_session = mock_neo4j_driver.session.return_value.__enter__.return_value
        mock_session.run.side_effect = Exception("数据库错误")
        
        # 调用方法
        callees = store.query_function_calls("test_function")
        
        # 验证结果
        assert callees == [] 