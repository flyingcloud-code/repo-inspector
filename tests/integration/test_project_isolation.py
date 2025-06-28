"""
项目隔离集成测试

测试项目隔离功能在Neo4j和Chroma中的实际效果
使用真实的数据库和代码仓库
"""
import os
import unittest
import shutil
import tempfile
import uuid
from pathlib import Path

from src.code_learner.project.project_manager import ProjectManager
from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.llm.vector_store import ChromaVectorStore
from src.code_learner.llm.code_chunker import CodeChunker, ChunkingStrategy
from src.code_learner.llm.code_embedder import CodeEmbedder
from src.code_learner.llm.embedding_engine import JinaEmbeddingEngine
from src.code_learner.parser.c_parser import CParser


class TestProjectIsolation(unittest.TestCase):
    """项目隔离集成测试类"""

    @classmethod
    def setUpClass(cls):
        """测试类初始化"""
        # 设置测试环境
        cls.test_dir = tempfile.mkdtemp()
        cls.test_data_dir = os.path.join(cls.test_dir, "data")
        cls.test_chroma_dir = os.path.join(cls.test_dir, "chroma")
        os.makedirs(cls.test_data_dir, exist_ok=True)
        os.makedirs(cls.test_chroma_dir, exist_ok=True)
        
        # 设置测试项目
        cls.opensbi_path = "/home/flyingcloud/work/project/code-repo-learner/reference_code_repo/opensbi"
        
        # 创建项目管理器
        cls.config = {"project_data_dir": cls.test_data_dir}
        cls.project_manager = ProjectManager(cls.config)
        
        # 创建两个测试项目，手动指定不同的项目ID
        cls.project_id_1 = f"project1_{uuid.uuid4().hex[:8]}"
        cls.project_id_2 = f"project2_{uuid.uuid4().hex[:8]}"
        
        # 创建项目配置
        cls.project_manager._create_project_config(
            repo_path=cls.opensbi_path,
            project_name="OpenSBI Project 1",
            project_id=cls.project_id_1
        )
        
        cls.project_manager._create_project_config(
            repo_path=cls.opensbi_path,
            project_name="OpenSBI Project 2",
            project_id=cls.project_id_2
        )
        
        # 连接Neo4j数据库
        cls.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        cls.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        cls.neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
        
        # 创建两个项目的Neo4j存储
        cls.graph_store_1 = Neo4jGraphStore(
            uri=cls.neo4j_uri,
            user=cls.neo4j_user,
            password=cls.neo4j_password,
            project_id=cls.project_id_1
        )
        
        cls.graph_store_2 = Neo4jGraphStore(
            uri=cls.neo4j_uri,
            user=cls.neo4j_user,
            password=cls.neo4j_password,
            project_id=cls.project_id_2
        )
        
        # 创建两个项目的Chroma存储
        cls.vector_store_1 = ChromaVectorStore(
            persist_directory=cls.test_chroma_dir,
            project_id=cls.project_id_1
        )
        
        cls.vector_store_2 = ChromaVectorStore(
            persist_directory=cls.test_chroma_dir,
            project_id=cls.project_id_2
        )
        
        # 创建代码解析器
        cls.parser = CParser()
        
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
        
        # 测试文件
        cls.test_file_path = os.path.join(cls.opensbi_path, "lib/sbi/sbi_hart.c")
        
    @classmethod
    def tearDownClass(cls):
        """测试类清理"""
        # 清理临时目录
        shutil.rmtree(cls.test_dir)
        
    def setUp(self):
        """每个测试前的设置"""
        # 确保Neo4j连接成功
        self.graph_store_1.connect()
        self.graph_store_2.connect()
        
    def tearDown(self):
        """每个测试后的清理"""
        # 关闭Neo4j连接
        self.graph_store_1.close()
        self.graph_store_2.close()
        
    def test_neo4j_project_isolation(self):
        """测试Neo4j项目隔离功能"""
        # 首先清空数据库
        self.graph_store_1.clear_database()
        self.graph_store_2.clear_database()
        
        # 在项目1中创建文件节点
        file1_created = self.graph_store_1.create_file_node(
            file_path=self.test_file_path,
            language="c"
        )
        self.assertTrue(file1_created, "项目1文件节点创建失败")
        
        # 在项目2中创建同名文件节点
        file2_created = self.graph_store_2.create_file_node(
            file_path=self.test_file_path,
            language="c"
        )
        self.assertTrue(file2_created, "项目2文件节点创建失败")
        
        # 在项目1中创建函数节点
        func1_created = self.graph_store_1.create_function_node(
            file_path=self.test_file_path,
            name="test_function",
            start_line=10,
            end_line=20
        )
        self.assertTrue(func1_created, "项目1函数节点创建失败")
        
        # 在项目2中创建同名函数节点，但行号不同
        func2_created = self.graph_store_2.create_function_node(
            file_path=self.test_file_path,
            name="test_function",
            start_line=30,
            end_line=40
        )
        self.assertTrue(func2_created, "项目2函数节点创建失败")
        
        # 验证项目1的函数节点
        functions_1 = self.graph_store_1.get_functions()
        print(f"项目1 ({self.project_id_1}) 函数节点: {functions_1}")
        self.assertEqual(len(functions_1), 1, f"期望项目1有1个函数，实际有{len(functions_1)}个")
        
        if len(functions_1) > 0:
            self.assertEqual(functions_1[0]["name"], "test_function")
            self.assertEqual(functions_1[0]["start_line"], 10)
        
        # 验证项目2的函数节点
        functions_2 = self.graph_store_2.get_functions()
        print(f"项目2 ({self.project_id_2}) 函数节点: {functions_2}")
        self.assertEqual(len(functions_2), 1, f"期望项目2有1个函数，实际有{len(functions_2)}个")
        
        if len(functions_2) > 0:
            self.assertEqual(functions_2[0]["name"], "test_function")
            self.assertEqual(functions_2[0]["start_line"], 30)
        
        # 验证项目隔离：使用简单查询，应该自动添加项目ID过滤
        query1 = """
        MATCH (f:Function)
        RETURN f
        """
        result1 = self.graph_store_1.run_query(query1)
        self.assertEqual(len(result1), 1, "项目1应该只能查询到自己的函数")
        if len(result1) > 0:
            self.assertEqual(result1[0]["f"]["project_id"], self.project_id_1)
        
        result2 = self.graph_store_2.run_query(query1)
        self.assertEqual(len(result2), 1, "项目2应该只能查询到自己的函数")
        if len(result2) > 0:
            self.assertEqual(result2[0]["f"]["project_id"], self.project_id_2)
        
        # 验证项目隔离：明确指定其他项目ID的查询应该返回空结果
        query2 = f"""
        MATCH (f:Function {{project_id: '{self.project_id_2}'}})
        RETURN f
        """
        result3 = self.graph_store_1.run_query(query2)
        self.assertEqual(len(result3), 0, "项目1不应该能查询到项目2的函数")
        
    def test_chroma_project_isolation(self):
        """测试Chroma项目隔离功能"""
        # 准备测试数据
        texts_1 = ["This is a test for project 1"]
        embeddings_1 = [[0.1, 0.2, 0.3, 0.4, 0.5] * 50]  # 250维向量
        metadatas_1 = [{"source": "project_1"}]
        
        texts_2 = ["This is a test for project 2"]
        embeddings_2 = [[0.5, 0.4, 0.3, 0.2, 0.1] * 50]  # 250维向量
        metadatas_2 = [{"source": "project_2"}]
        
        # 在项目1的集合中添加嵌入
        collection_name_1 = "test_collection"
        self.vector_store_1.add_embeddings(texts_1, embeddings_1, metadatas_1, collection_name_1)
        
        # 在项目2的集合中添加嵌入
        collection_name_2 = "test_collection"
        self.vector_store_2.add_embeddings(texts_2, embeddings_2, metadatas_2, collection_name_2)
        
        # 获取实际的集合名称（应该包含项目ID前缀）
        full_collection_name_1 = self.vector_store_1.get_collection_name(collection_name_1)
        full_collection_name_2 = self.vector_store_2.get_collection_name(collection_name_2)
        
        print(f"项目1 ({self.project_id_1}) 集合名称: {full_collection_name_1}")
        print(f"项目2 ({self.project_id_2}) 集合名称: {full_collection_name_2}")
        
        # 验证集合名称不同（因为项目ID不同）
        self.assertNotEqual(full_collection_name_1, full_collection_name_2)
        
        # 验证项目1的集合中只有项目1的数据
        results_1 = self.vector_store_1.query_collection(
            query_texts=["test for project 1"],
            collection_name=collection_name_1,
            n_results=10
        )
        self.assertEqual(len(results_1["ids"][0]), 1)
        self.assertEqual(results_1["metadatas"][0][0]["source"], "project_1")
        
        # 验证项目2的集合中只有项目2的数据
        results_2 = self.vector_store_2.query_collection(
            query_texts=["test for project 2"],
            collection_name=collection_name_2,
            n_results=10
        )
        self.assertEqual(len(results_2["ids"][0]), 1)
        self.assertEqual(results_2["metadatas"][0][0]["source"], "project_2")
        
    def test_end_to_end_isolation(self):
        """测试端到端的项目隔离功能"""
        # 读取测试文件内容
        with open(self.test_file_path, 'r') as f:
            file_content = f.read()
            
        # 使用不同的分块策略为两个项目创建不同的代码块
        chunks_1 = self.chunker.chunk_file_by_size(self.test_file_path)
        chunks_2 = self.chunker.chunk_file_by_size(self.test_file_path)
        
        # 为项目1嵌入代码块
        collection_name_1 = "code_chunks"
        
        # 使用嵌入引擎编码文本
        texts_1 = [chunk.content for chunk in chunks_1]
        embeddings_1 = self.embedding_engine.encode_batch(texts_1)
        metadatas_1 = [chunk.metadata for chunk in chunks_1]
        
        # 添加到向量存储
        self.vector_store_1.add_embeddings(texts_1, embeddings_1, metadatas_1, collection_name_1)
        
        # 为项目2嵌入代码块
        collection_name_2 = "code_chunks"
        
        # 使用嵌入引擎编码文本
        texts_2 = [chunk.content for chunk in chunks_2]
        embeddings_2 = self.embedding_engine.encode_batch(texts_2)
        metadatas_2 = [chunk.metadata for chunk in chunks_2]
        
        # 添加到向量存储
        self.vector_store_2.add_embeddings(texts_2, embeddings_2, metadatas_2, collection_name_2)
        
        # 获取完整的集合名称（带项目ID）
        full_collection_name_1 = self.vector_store_1.get_collection_name(collection_name_1)
        full_collection_name_2 = self.vector_store_2.get_collection_name(collection_name_2)
        
        # 验证项目1的集合中的代码块数量
        collections_1 = self.vector_store_1.list_collections()
        self.assertIn(full_collection_name_1, collections_1)
        collection_info_1 = self.vector_store_1.get_collection_info(full_collection_name_1)
        
        # 验证项目2的集合中的代码块数量
        collections_2 = self.vector_store_2.list_collections()
        self.assertIn(full_collection_name_2, collections_2)
        collection_info_2 = self.vector_store_2.get_collection_info(full_collection_name_2)
        
        # 验证两个项目的代码块数量相同（因为使用相同的分块策略）
        self.assertEqual(collection_info_1["count"], collection_info_2["count"])
        
        # 验证项目1只能看到自己的集合
        for collection in collections_1:
            self.assertTrue(collection.startswith(self.project_id_1))
            
        # 验证项目2只能看到自己的集合
        for collection in collections_2:
            self.assertTrue(collection.startswith(self.project_id_2))


if __name__ == "__main__":
    unittest.main() 