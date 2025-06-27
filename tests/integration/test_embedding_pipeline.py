import pytest
import os
import sys
import subprocess
import time

# 调整路径以允许从项目根目录导入
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from code_learner.storage.neo4j_store import Neo4jGraphStore
from code_learner.llm.vector_store import ChromaVectorStore
from code_learner.core.data_models import ParsedCode, Function, FileInfo

FIXTURE_FILE = "tests/fixtures/embedding_test_code.c"

@pytest.fixture(scope="module")
def neo4j_store():
    """提供一个连接到数据库的 Neo4jGraphStore 实例"""
    store = Neo4jGraphStore()
    if not store.connect():
        pytest.fail("无法连接到 Neo4j，请确保数据库正在运行并已配置。")
    
    # 清理数据库以进行测试
    store.clear_database()
    yield store
    
    # 测试后再次清理
    store.clear_database()
    store.close()

@pytest.fixture(scope="module")
def vector_store():
    """提供一个 ChromaVectorStore 实例"""
    # 使用一个测试专用的集合
    store = ChromaVectorStore(persist_directory="./data/test_chroma")
    return store

def setup_test_data(store: Neo4jGraphStore, temp_dir: Path):
    """向 Neo4j 数据库中注入测试数据"""
    # 定义虚拟路径和真实路径
    virtual_path1 = "/test/file1.c"
    real_path1 = temp_dir / "test" / "file1.c"
    real_path1.touch()

    virtual_path2 = "/test/file2.c"
    real_path2 = temp_dir / "test" / "file2.c"
    real_path2.touch()

    # 创建两个函数
    func1 = Function(
        name="test_func_one",
        code="void test_func_one() {\\n  printf(\\"Hello\\");\\n}",
        start_line=1,
        end_line=3,
        file_path=str(real_path1)
    )
    func2 = Function(
        name="test_func_two",
        code="int test_func_two(int a, int b) {\\n  return a + b;\\n}",
        start_line=5,
        end_line=7,
        file_path=str(real_path2) # 使用真实路径
    )
    
    # 创建文件信息和解析后的代码对象
    file1_info = FileInfo.from_path(real_path1)
    # 确保文件信息中的路径是我们在数据库中期望的路径
    file1_info.path = func1.file_path 
    parsed_code1 = ParsedCode(file_info=file1_info, functions=[func1])

    file2_info = FileInfo.from_path(real_path2)
    file2_info.path = func2.file_path
    parsed_code2 = ParsedCode(file_info=file2_info, functions=[func2])

    # 存储到数据库
    assert store.store_parsed_code(parsed_code1)
    assert store.store_parsed_code(parsed_code2)

class TestEmbeddingPipeline:
    """测试端到端的嵌入流程"""

    def test_semantic_embedding_pipeline(self, neo4j_store: Neo4jGraphStore, vector_store: ChromaVectorStore):
        """测试 'semantic' 策略的完整流程，使用夹具文件"""
        # 0. 清理旧数据
        neo4j_store.clear_database()
        collection_name = "test_semantic_embeddings_from_fixture"
        vector_store.delete_collection(collection_name)

        # 1. 设置: 使用 code-analyzer 解析夹具文件以填充 Neo4j
        analyze_command = [
            "code-analyzer",
            "analyze",
            "--file", FIXTURE_FILE
        ]
        analyze_result = subprocess.run(analyze_command, capture_output=True, text=True, shell=True, executable="/bin/bash")
        print("--- Analyze STDOUT ---")
        print(analyze_result.stdout)
        print("--- Analyze STDERR ---")
        print(analyze_result.stderr)
        assert analyze_result.returncode == 0, "code-analyzer 执行失败"
        
        # 2. 执行: 运行嵌入命令
        embed_command = [
            "code-embed",
            "--strategy", "semantic",
            "--collection", collection_name
        ]
        
        embed_result = subprocess.run(embed_command, capture_output=True, text=True, shell=True, executable="/bin/bash")
        print("--- Embed STDOUT ---")
        print(embed_result.stdout)
        print("--- Embed STDERR ---")
        print(embed_result.stderr)
        assert embed_result.returncode == 0, "嵌入命令执行失败"
        assert "嵌入任务成功完成" in embed_result.stdout

        # 3. 验证: 检查 ChromaDB 中的结果
        time.sleep(1) # 等待持久化
        
        collection = vector_store.get_collection(collection_name)
        assert collection is not None
        
        count = collection.count()
        assert count == 2, f"集合应包含2个嵌入，但实际为 {count}"
        
        embeddings = collection.get(include=["metadatas"])
        metadatas = embeddings['metadatas']
        
        func_names = {meta.get('function_name') for meta in metadatas}
        assert "test_func_one" in func_names
        assert "test_func_two" in func_names

        for meta in metadatas:
            assert meta['strategy'] == 'semantic'
            assert meta['node_type'] == 'Function'
            assert meta['source'] == os.path.abspath(FIXTURE_FILE)

        # 清理
        vector_store.delete_collection(collection_name) 