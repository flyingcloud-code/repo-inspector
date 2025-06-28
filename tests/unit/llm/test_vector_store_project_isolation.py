import unittest
from unittest.mock import patch, MagicMock

from src.code_learner.llm.vector_store import ChromaVectorStore


class TestChromaVectorStoreProjectIsolation(unittest.TestCase):
    def setUp(self):
        # 模拟Chroma客户端
        self.client_mock = MagicMock()
        self.collection_mock = MagicMock()
        
        # 设置模拟对象的行为
        self.client_mock.get_or_create_collection.return_value = self.collection_mock
        
        # 创建带有项目ID的ChromaVectorStore实例
        with patch('chromadb.PersistentClient', return_value=self.client_mock):
            self.vector_store = ChromaVectorStore(
                persist_directory="./data/chroma",
                project_id="p1234567890"
            )
            
        # 创建不带项目ID的ChromaVectorStore实例（向后兼容测试）
        with patch('chromadb.PersistentClient', return_value=self.client_mock):
            self.legacy_vector_store = ChromaVectorStore(
                persist_directory="./data/chroma"
            )
            
    def test_collection_name_with_project_id(self):
        """测试带有项目ID的集合命名"""
        # 获取集合名称
        collection_name = self.vector_store.get_collection_name("code_chunks")
        
        # 验证集合名称包含项目ID
        self.assertEqual(collection_name, "p1234567890_code_chunks")
        
    def test_collection_name_without_project_id(self):
        """测试不带项目ID的集合命名（向后兼容）"""
        # 获取集合名称
        collection_name = self.legacy_vector_store.get_collection_name("code_chunks")
        
        # 验证集合名称不包含项目ID
        self.assertEqual(collection_name, "code_chunks")
        
    def test_add_embeddings_with_project_id(self):
        """测试添加嵌入时使用项目特定的集合名称"""
        # 准备测试数据
        texts = ["text1", "text2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        metadatas = [{"source": "file1"}, {"source": "file2"}]
        
        # 调用方法
        self.vector_store.add_embeddings(texts, embeddings, metadatas)
        
        # 验证使用了正确的集合名称
        self.client_mock.get_or_create_collection.assert_called_once_with(name="p1234567890_code_chunks")
        
    def test_add_embeddings_without_project_id(self):
        """测试添加嵌入时不使用项目特定的集合名称（向后兼容）"""
        # 准备测试数据
        texts = ["text1", "text2"]
        embeddings = [[0.1, 0.2], [0.3, 0.4]]
        metadatas = [{"source": "file1"}, {"source": "file2"}]
        
        # 调用方法
        self.legacy_vector_store.add_embeddings(texts, embeddings, metadatas)
        
        # 验证使用了默认集合名称
        self.client_mock.get_or_create_collection.assert_called_once_with(name="code_chunks")
        
    def test_query_with_project_id(self):
        """测试查询时使用项目特定的集合名称"""
        # 准备模拟返回值
        self.collection_mock.query.return_value = {
            "documents": ["text1"],
            "metadatas": [{"source": "file1"}],
            "distances": [0.1]
        }
        
        # 调用方法
        self.vector_store.query_embeddings([0.1, 0.2], n_results=1)
        
        # 验证使用了正确的集合名称
        self.client_mock.get_or_create_collection.assert_called_once_with(name="p1234567890_code_chunks")
        
    def test_query_without_project_id(self):
        """测试查询时不使用项目特定的集合名称（向后兼容）"""
        # 准备模拟返回值
        self.collection_mock.query.return_value = {
            "documents": ["text1"],
            "metadatas": [{"source": "file1"}],
            "distances": [0.1]
        }
        
        # 调用方法
        self.legacy_vector_store.query_embeddings([0.1, 0.2], n_results=1)
        
        # 验证使用了默认集合名称
        self.client_mock.get_or_create_collection.assert_called_once_with(name="code_chunks")


if __name__ == "__main__":
    unittest.main() 