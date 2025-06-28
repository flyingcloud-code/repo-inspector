"""
嵌入管道集成测试

测试代码嵌入管道在不同项目中的隔离效果
"""
import os
import unittest
import shutil
import tempfile
import uuid
from pathlib import Path

from src.code_learner.project.project_manager import ProjectManager
from src.code_learner.llm.vector_store import ChromaVectorStore
from src.code_learner.llm.code_chunker import CodeChunker
from src.code_learner.llm.code_embedder import CodeEmbedder
from src.code_learner.llm.embedding_engine import JinaEmbeddingEngine


class TestEmbeddingPipeline(unittest.TestCase):
    """嵌入管道集成测试类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 设置测试环境
        cls.test_dir = tempfile.mkdtemp()
        cls.test_data_dir = os.path.join(cls.test_dir, "data")
        cls.test_chroma_dir = os.path.join(cls.test_dir, "chroma")
        os.makedirs(cls.test_data_dir, exist_ok=True)
        os.makedirs(cls.test_chroma_dir, exist_ok=True)
        
        # 创建测试代码文件
        cls.test_code_dir = os.path.join(cls.test_dir, "code")
        os.makedirs(cls.test_code_dir, exist_ok=True)
        
        # 创建测试代码文件1
        cls.test_code_file1 = os.path.join(cls.test_code_dir, "test_code1.c")
        with open(cls.test_code_file1, 'w') as f:
            f.write('void test_func_one() {\n  printf("Hello");\n}')
            
        # 创建测试代码文件2
        cls.test_code_file2 = os.path.join(cls.test_code_dir, "test_code2.c")
        with open(cls.test_code_file2, 'w') as f:
            f.write('int test_func_two(int x) {\n  return x * 2;\n}')
        
        # 创建项目管理器
        cls.config = {"project_data_dir": cls.test_data_dir}
        cls.project_manager = ProjectManager(cls.config)
        
        # 创建两个测试项目
        cls.project_id_1 = cls.project_manager.create_project("/tmp/project1", "Project 1")
        cls.project_id_2 = cls.project_manager.create_project("/tmp/project2", "Project 2")
        
        # 创建两个项目的Chroma存储
        cls.vector_store_1 = ChromaVectorStore(
            persist_directory=cls.test_chroma_dir,
            project_id=cls.project_id_1
        )
        
        cls.vector_store_2 = ChromaVectorStore(
            persist_directory=cls.test_chroma_dir,
            project_id=cls.project_id_2
        )
        
        # 创建代码分块器
        cls.chunker = CodeChunker()
        
        # 创建嵌入引擎
        cls.embedding_engine = JinaEmbeddingEngine()
        cls.embedding_engine.load_model("jinaai/jina-embeddings-v2-base-code")
        
        # 创建代码嵌入器
        cls.embedder_1 = CodeEmbedder(
            vector_store=cls.vector_store_1,
            embedding_engine=cls.embedding_engine
        )
        cls.embedder_2 = CodeEmbedder(
            vector_store=cls.vector_store_2,
            embedding_engine=cls.embedding_engine
        )
        
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        # 清理临时目录
        shutil.rmtree(cls.test_dir)
        
    def test_embedding_isolation(self):
        """测试嵌入隔离功能"""
        # 分块代码
        chunks_1 = self.chunker.chunk_file_by_size(self.test_code_file1)
        chunks_2 = self.chunker.chunk_file_by_size(self.test_code_file2)
        
        # 为项目1嵌入代码块
        collection_name_1 = f"{self.project_id_1}_code_chunks"
        self.vector_store_1.create_collection(collection_name_1)
        
        # 使用嵌入引擎编码文本
        texts_1 = [chunk.content for chunk in chunks_1]
        embeddings_1 = self.embedding_engine.encode_batch(texts_1)
        metadatas_1 = [chunk.metadata for chunk in chunks_1]
        
        # 添加到向量存储
        self.vector_store_1.add_embeddings(texts_1, embeddings_1, metadatas_1, collection_name_1)
        
        # 为项目2嵌入代码块
        collection_name_2 = f"{self.project_id_2}_code_chunks"
        self.vector_store_2.create_collection(collection_name_2)
        
        # 使用嵌入引擎编码文本
        texts_2 = [chunk.content for chunk in chunks_2]
        embeddings_2 = self.embedding_engine.encode_batch(texts_2)
        metadatas_2 = [chunk.metadata for chunk in chunks_2]
        
        # 添加到向量存储
        self.vector_store_2.add_embeddings(texts_2, embeddings_2, metadatas_2, collection_name_2)
        
        # 验证项目1的集合中的代码块
        collections_1 = self.vector_store_1.list_collections()
        self.assertIn(collection_name_1, collections_1)
        
        # 验证项目2的集合中的代码块
        collections_2 = self.vector_store_2.list_collections()
        self.assertIn(collection_name_2, collections_2)
        
        # 验证项目1不能看到项目2的集合
        self.assertNotIn(collection_name_2, collections_1)
        
        # 验证项目2不能看到项目1的集合
        self.assertNotIn(collection_name_1, collections_2)
        
    def test_query_isolation(self):
        """测试查询隔离功能"""
        # 准备测试数据
        texts_1 = ["This is a test function for project 1"]
        embeddings_1 = self.embedding_engine.encode_batch(texts_1)
        metadatas_1 = [{"source": "project_1"}]
        
        texts_2 = ["This is a test function for project 2"]
        embeddings_2 = self.embedding_engine.encode_batch(texts_2)
        metadatas_2 = [{"source": "project_2"}]
        
        # 在项目1的集合中添加嵌入
        collection_name_1 = self.vector_store_1.get_collection_name("test_collection")
        self.vector_store_1.create_collection(collection_name_1)
        self.vector_store_1.add_embeddings(texts_1, embeddings_1, metadatas_1, collection_name_1)
        
        # 在项目2的集合中添加嵌入
        collection_name_2 = self.vector_store_2.get_collection_name("test_collection")
        self.vector_store_2.create_collection(collection_name_2)
        self.vector_store_2.add_embeddings(texts_2, embeddings_2, metadatas_2, collection_name_2)
        
        # 使用项目1的嵌入引擎查询项目1的集合
        query_text = "test function"
        query_embedding = self.embedding_engine.encode_text(query_text)
        
        # 查询项目1的集合
        results_1 = self.vector_store_1.query_embeddings(query_embedding, n_results=1, collection_name=collection_name_1)
        self.assertEqual(len(results_1), 1)
        self.assertEqual(results_1[0]["document"], texts_1[0])
        self.assertEqual(results_1[0]["metadata"]["source"], "project_1")
        
        # 查询项目2的集合
        results_2 = self.vector_store_2.query_embeddings(query_embedding, n_results=1, collection_name=collection_name_2)
        self.assertEqual(len(results_2), 1)
        self.assertEqual(results_2[0]["document"], texts_2[0])
        self.assertEqual(results_2[0]["metadata"]["source"], "project_2")
        
    def test_cross_project_query(self):
        """测试跨项目查询隔离"""
        # 准备测试数据
        texts_1 = ["Unique content for project 1 only"]
        embeddings_1 = self.embedding_engine.encode_batch(texts_1)
        metadatas_1 = [{"source": "project_1_unique"}]
        
        texts_2 = ["Unique content for project 2 only"]
        embeddings_2 = self.embedding_engine.encode_batch(texts_2)
        metadatas_2 = [{"source": "project_2_unique"}]
        
        # 在项目1的集合中添加嵌入
        collection_name_1 = self.vector_store_1.get_collection_name("unique_collection")
        self.vector_store_1.create_collection(collection_name_1)
        self.vector_store_1.add_embeddings(texts_1, embeddings_1, metadatas_1, collection_name_1)
        
        # 在项目2的集合中添加嵌入
        collection_name_2 = self.vector_store_2.get_collection_name("unique_collection")
        self.vector_store_2.create_collection(collection_name_2)
        self.vector_store_2.add_embeddings(texts_2, embeddings_2, metadatas_2, collection_name_2)
        
        # 使用项目1的嵌入引擎查询项目1的集合
        query_text = "unique content"
        query_embedding = self.embedding_engine.encode_text(query_text)
        
        # 在项目1中查询项目2的集合名称（应该查不到）
        with self.assertRaises(Exception):
            self.vector_store_1.query_embeddings(query_embedding, n_results=1, collection_name=collection_name_2)
            
        # 在项目2中查询项目1的集合名称（应该查不到）
        with self.assertRaises(Exception):
            self.vector_store_2.query_embeddings(query_embedding, n_results=1, collection_name=collection_name_1)


if __name__ == "__main__":
    unittest.main()