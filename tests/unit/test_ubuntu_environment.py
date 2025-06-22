"""Ubuntu环境依赖测试

验证所有核心依赖在Ubuntu环境下能正确安装和导入
"""
import pytest
import sys
import importlib


class TestUbuntuEnvironment:
    """Ubuntu环境依赖验证测试"""
    
    def test_python_version(self):
        """验证Python版本 >= 3.11"""
        version = sys.version_info
        assert version.major == 3
        assert version.minor >= 11
        print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    def test_tree_sitter_import(self):
        """验证tree-sitter导入和基本功能"""
        try:
            import tree_sitter
            from tree_sitter import Language, Parser
            
            # 验证基本类可以实例化
            parser = Parser()
            assert parser is not None
            print("Tree-sitter导入成功")
            
        except ImportError as e:
            pytest.fail(f"Tree-sitter导入失败: {e}")
    
    def test_chroma_import(self):
        """验证chromadb导入和客户端创建"""
        try:
            import chromadb
            
            # 创建内存客户端进行测试
            client = chromadb.Client()
            assert client is not None
            print(f"ChromaDB version: {chromadb.__version__}")
            
        except ImportError as e:
            pytest.fail(f"ChromaDB导入失败: {e}")
        except Exception as e:
            pytest.fail(f"ChromaDB客户端创建失败: {e}")
    
    def test_sentence_transformers_import(self):
        """验证sentence-transformers导入"""
        try:
            from sentence_transformers import SentenceTransformer
            
            # 不实际加载模型，只验证导入
            assert SentenceTransformer is not None
            print("Sentence Transformers导入成功")
            
        except ImportError as e:
            pytest.fail(f"Sentence Transformers导入失败: {e}")
    
    def test_neo4j_import(self):
        """验证neo4j驱动导入"""
        try:
            from neo4j import GraphDatabase
            
            # 验证GraphDatabase类存在
            assert GraphDatabase is not None
            print("Neo4j驱动导入成功")
            
        except ImportError as e:
            pytest.fail(f"Neo4j驱动导入失败: {e}")
    
    def test_sqlite_connection(self):
        """验证SQLite连接"""
        try:
            import sqlite3
            
            # 创建内存数据库测试连接
            conn = sqlite3.connect(':memory:')
            assert conn is not None
            
            # 测试基本SQL操作
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            print(f"SQLite version: {version}")
            
            conn.close()
            
        except Exception as e:
            pytest.fail(f"SQLite连接测试失败: {e}")
    
    def test_standard_libraries(self):
        """验证标准库导入"""
        required_modules = [
            'pathlib', 'dataclasses', 'typing', 'abc',
            'logging', 'yaml', 'json', 'os', 'sys'
        ]
        
        for module_name in required_modules:
            try:
                importlib.import_module(module_name)
                print(f"✓ {module_name}")
            except ImportError as e:
                pytest.fail(f"标准库 {module_name} 导入失败: {e}")


if __name__ == "__main__":
    # 允许直接运行测试
    pytest.main([__file__, "-v"]) 