import unittest
from unittest.mock import patch, MagicMock

from src.code_learner.storage.neo4j_store import Neo4jGraphStore


class TestNeo4jStoreProjectIsolation(unittest.TestCase):
    def setUp(self):
        # 模拟Neo4j驱动
        self.driver_mock = MagicMock()
        self.session_mock = MagicMock()
        self.transaction_mock = MagicMock()
        
        # 设置模拟对象的行为
        self.driver_mock.session.return_value = self.session_mock
        self.session_mock.__enter__.return_value = self.session_mock
        self.session_mock.__exit__.return_value = None
        self.session_mock.begin_transaction.return_value = self.transaction_mock
        self.transaction_mock.__enter__.return_value = self.transaction_mock
        self.transaction_mock.__exit__.return_value = None
        
        # 创建带有项目ID的Neo4jGraphStore实例
        with patch('neo4j.GraphDatabase.driver', return_value=self.driver_mock):
            self.graph_store = Neo4jGraphStore(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password",
                project_id="p1234567890"
            )
            
        # 创建不带项目ID的Neo4jGraphStore实例（向后兼容测试）
        with patch('neo4j.GraphDatabase.driver', return_value=self.driver_mock):
            self.legacy_graph_store = Neo4jGraphStore(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="password"
            )
            
    def test_create_file_node_with_project_id(self):
        """测试创建带有项目ID的文件节点"""
        # 设置模拟返回值
        result_mock = MagicMock()
        self.session_mock.run.return_value = result_mock
        
        # 调用方法
        self.graph_store.create_file_node(file_path="/path/to/file.py", language="python")
        
        # 验证查询包含项目ID
        call_args = self.session_mock.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("project_id", params)
        self.assertEqual(params["project_id"], "p1234567890")
        self.assertIn("project_id: $project_id", query)
        
    def test_create_file_node_without_project_id(self):
        """测试创建不带项目ID的文件节点（向后兼容）"""
        # 设置模拟返回值
        result_mock = MagicMock()
        self.session_mock.run.return_value = result_mock
        
        # 调用方法
        self.legacy_graph_store.create_file_node(file_path="/path/to/file.py", language="python")
        
        # 验证查询不包含项目ID
        call_args = self.session_mock.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        # 检查查询中不包含project_id
        self.assertNotIn("project_id", params)
        self.assertNotIn("project_id", query)
        
    def test_create_function_node_with_project_id(self):
        """测试创建带有项目ID的函数节点"""
        # 设置模拟返回值
        result_mock = MagicMock()
        self.session_mock.run.return_value = result_mock
        
        # 调用方法
        self.graph_store.create_function_node(
            file_path="/path/to/file.py",
            name="test_function",
            start_line=10,
            end_line=20
        )
        
        # 验证查询包含项目ID
        call_args = self.session_mock.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("project_id", params)
        self.assertEqual(params["project_id"], "p1234567890")
        self.assertIn("project_id: $project_id", query)
        
    def test_create_relationship_with_project_id(self):
        """测试创建带有项目ID的关系"""
        # 设置模拟返回值
        result_mock = MagicMock()
        self.session_mock.run.return_value = result_mock
        
        # 调用方法
        self.graph_store.create_calls_relationship(
            caller_function="caller_function",
            called_function="called_function"
        )
        
        # 验证查询包含项目ID
        call_args = self.session_mock.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("project_id", params)
        self.assertEqual(params["project_id"], "p1234567890")
        self.assertIn("project_id: $project_id", query)
        
    def test_get_functions_with_project_id(self):
        """测试获取函数时使用项目ID过滤"""
        # 设置模拟返回值
        result_mock = MagicMock()
        self.session_mock.run.return_value = result_mock
        
        # 调用方法
        self.graph_store.get_functions()
        
        # 验证查询包含项目ID过滤
        call_args = self.session_mock.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("project_id", params)
        self.assertEqual(params["project_id"], "p1234567890")
        self.assertIn("project_id = $project_id", query)
        
    def test_get_call_graph_with_project_id(self):
        """测试获取调用图时使用项目ID过滤"""
        # 设置模拟返回值
        result_mock = MagicMock()
        self.session_mock.run.return_value = result_mock
        
        # 调用方法
        self.graph_store.get_call_graph()
        
        # 验证查询包含项目ID过滤
        call_args = self.session_mock.run.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        
        self.assertIn("project_id", params)
        self.assertEqual(params["project_id"], "p1234567890")
        self.assertIn("project_id = $project_id", query)


if __name__ == "__main__":
    unittest.main() 