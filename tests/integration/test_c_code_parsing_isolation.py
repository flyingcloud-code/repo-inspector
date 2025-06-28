"""
C代码解析和存储的项目隔离集成测试

使用真实的OpenSBI代码库测试C代码解析和存储功能
验证项目隔离在实际代码解析和存储过程中的效果
"""
import os
import unittest
import shutil
import tempfile
import time
from pathlib import Path

from src.code_learner.project.project_manager import ProjectManager
from src.code_learner.storage.neo4j_store import Neo4jGraphStore
from src.code_learner.llm.vector_store import ChromaVectorStore
from src.code_learner.parser.c_parser import CParser
from src.code_learner.llm.code_chunker import CodeChunker
from src.code_learner.llm.code_embedder import CodeEmbedder
from src.code_learner.llm.embedding_engine import JinaEmbeddingEngine


class TestCCodeParsingIsolation(unittest.TestCase):
    """C代码解析和存储的项目隔离集成测试类"""

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
        
        # 创建两个测试项目
        cls.project_id_1 = cls.project_manager.create_project(cls.opensbi_path, "OpenSBI Project 1")
        cls.project_id_2 = cls.project_manager.create_project(cls.opensbi_path, "OpenSBI Project 2")
        
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
        
        # 测试文件路径
        cls.test_files = [
            os.path.join(cls.opensbi_path, "lib/sbi/sbi_hart.c"),
            os.path.join(cls.opensbi_path, "lib/sbi/sbi_system.c"),
            os.path.join(cls.opensbi_path, "lib/sbi/sbi_timer.c")
        ]
        
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
        
        # 清理数据库
        self.graph_store_1.clear_database()
        self.graph_store_2.clear_database()
        
    def tearDown(self):
        """每个测试后的清理"""
        # 关闭Neo4j连接
        self.graph_store_1.close()
        self.graph_store_2.close()
        
    def test_parse_and_store_c_files(self):
        """测试解析和存储C文件"""
        # 在项目1中解析和存储第一个文件
        self._parse_and_store_file(self.test_files[0], self.graph_store_1)
        
        # 在项目2中解析和存储所有文件
        for file_path in self.test_files:
            self._parse_and_store_file(file_path, self.graph_store_2)
            
        # 验证项目1只有一个文件
        files_1 = self.graph_store_1.get_files()
        self.assertEqual(len(files_1), 1)
        self.assertEqual(files_1[0]["path"], self.test_files[0])
        
        # 验证项目2有三个文件
        files_2 = self.graph_store_2.get_files()
        self.assertEqual(len(files_2), 3)
        
        # 验证项目1和项目2的函数数量不同
        functions_1 = self.graph_store_1.get_functions()
        functions_2 = self.graph_store_2.get_functions()
        self.assertLess(len(functions_1), len(functions_2))
        
        # 验证项目1中的函数不会出现在项目2的查询结果中
        for func in functions_1:
            # 在项目2中查询项目1的函数
            query = f"MATCH (f:Function {{name: '{func['name']}', project_id: '{self.project_id_1}'}}) RETURN f"
            result = self.graph_store_2.run_query(query)
            self.assertEqual(len(result), 0)
            
    def test_parse_embed_and_query(self):
        """测试解析、嵌入和查询C代码"""
        # 在项目1中解析、嵌入和存储第一个文件
        self._parse_embed_and_store_file(self.test_files[0], self.graph_store_1, self.vector_store_1, "code_chunks_1")
        
        # 在项目2中解析、嵌入和存储第二个文件
        self._parse_embed_and_store_file(self.test_files[1], self.graph_store_2, self.vector_store_2, "code_chunks_2")
        
        # 验证项目1和项目2的函数数量不同
        functions_1 = self.graph_store_1.get_functions()
        functions_2 = self.graph_store_2.get_functions()
        self.assertNotEqual(len(functions_1), len(functions_2))
        
        # 验证项目1和项目2的代码块集合不同
        collection_name_1 = f"{self.project_id_1}_code_chunks_1"
        collection_name_2 = f"{self.project_id_2}_code_chunks_2"
        
        collections_1 = self.vector_store_1.list_collections()
        collections_2 = self.vector_store_2.list_collections()
        
        self.assertIn(collection_name_1, collections_1)
        self.assertIn(collection_name_2, collections_2)
        
        # 验证项目1不能看到项目2的集合
        self.assertNotIn(collection_name_2, collections_1)
        
        # 验证项目2不能看到项目1的集合
        self.assertNotIn(collection_name_1, collections_2)
        
    def test_real_c_code_function_isolation(self):
        """测试真实C代码函数的项目隔离"""
        # 在两个项目中解析相同的文件
        file_path = self.test_files[0]
        
        # 解析文件
        with open(file_path, 'r') as f:
            content = f.read()
            
        parsed_data = self.parser.parse_file(file_path)
        
        # 在项目1中存储解析结果
        self._store_parsed_data(parsed_data, self.graph_store_1)
        
        # 修改部分函数信息后在项目2中存储
        for func in parsed_data["functions"]:
            # 修改函数的注释
            func["docstring"] = f"Modified in project 2: {func['docstring']}"
            
        self._store_parsed_data(parsed_data, self.graph_store_2)
        
        # 选择一个共同的函数名进行比较
        common_function_name = parsed_data["functions"][0]["name"]
        
        # 在项目1中查询该函数
        query_1 = f"""
        MATCH (f:Function {{name: '{common_function_name}', project_id: '{self.project_id_1}'}})
        RETURN f.name, f.docstring
        """
        result_1 = self.graph_store_1.run_query(query_1)
        
        # 在项目2中查询该函数
        query_2 = f"""
        MATCH (f:Function {{name: '{common_function_name}', project_id: '{self.project_id_2}'}})
        RETURN f.name, f.docstring
        """
        result_2 = self.graph_store_2.run_query(query_2)
        
        # 验证两个项目中的函数注释不同
        self.assertEqual(result_1[0]["f.name"], result_2[0]["f.name"])
        self.assertNotEqual(result_1[0]["f.docstring"], result_2[0]["f.docstring"])
        self.assertTrue(result_2[0]["f.docstring"].startswith("Modified in project 2:"))
        
    def _parse_and_store_file(self, file_path, graph_store):
        """解析并存储文件"""
        # 读取文件内容
        with open(file_path, 'r') as f:
            content = f.read()
            
        # 解析文件
        parsed_data = self.parser.parse_file(file_path)
        
        # 存储解析结果
        self._store_parsed_data(parsed_data, graph_store)
        
    def _parse_embed_and_store_file(self, file_path, graph_store, vector_store, collection_name):
        """解析、嵌入并存储文件"""
        # 读取文件内容
        with open(file_path, 'r') as f:
            content = f.read()
            
        # 解析文件
        parsed_data = self.parser.parse_file(file_path)
        
        # 存储解析结果
        self._store_parsed_data(parsed_data, graph_store)
        
        # 分块代码
        chunks = self.chunker.chunk_file_by_size(file_path)
        
        # 嵌入代码块
        collection_name = f"{graph_store.project_id}_{collection_name}"
        vector_store.create_collection(collection_name)
        
        # 使用嵌入引擎编码文本
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedding_engine.encode_batch(texts)
        metadatas = [chunk.metadata for chunk in chunks]
        
        # 添加到向量存储
        vector_store.add_embeddings(texts, embeddings, metadatas, collection_name)
        
    def _store_parsed_data(self, parsed_data, graph_store):
        """存储解析结果"""
        # 创建文件节点
        graph_store.create_file_node(
            file_path=parsed_data["file_path"],
            language=parsed_data["language"]
        )
        
        # 创建函数节点
        for func in parsed_data["functions"]:
            graph_store.create_function_node(
                file_path=parsed_data["file_path"],
                name=func["name"],
                start_line=func["start_line"],
                end_line=func["end_line"],
                docstring=func.get("docstring", ""),
                parameters=func.get("parameters", []),
                return_type=func.get("return_type", "")
            )
            
        # 创建调用关系
        for call in parsed_data.get("function_calls", []):
            graph_store.create_function_call_relationship(
                caller_name=call["caller"],
                callee_name=call["callee"],
                file_path=parsed_data["file_path"]
            )


if __name__ == "__main__":
    unittest.main() 