import pytest
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, MagicMock
import tempfile

# 调整路径以允许从项目根目录导入
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from code_learner.llm.code_chunker import CodeChunker, CodeChunk, ChunkingStrategy

@pytest.fixture
def sample_file(tmp_path: Path) -> str:
    """创建一个包含示例文本的临时文件"""
    content = "This is the first line.\n"
    content += "This is the second line, which is a bit longer.\n"
    content += "Third line.\n"
    content += "Fourth line, also longer to test wrapping.\n"
    content += "Fifth and final line."
    
    file_path = tmp_path / "sample.txt"
    file_path.write_text(content, encoding='utf-8')
    return str(file_path)

class TestCodeChunker(unittest.TestCase):
    """测试代码分块器"""
    
    def setUp(self):
        """设置测试环境"""
        self.chunker = CodeChunker(chunk_size=100, chunk_overlap=20)
        
        # 创建临时测试文件
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # 创建一个简单的C文件用于测试
        self.test_c_file = os.path.join(self.temp_dir.name, "test.c")
        with open(self.test_c_file, "w") as f:
            f.write("""
/**
 * 这是一个测试文件
 * 用于测试代码分块器
 */

#include <stdio.h>
#define MAX_SIZE 100

// 全局变量
int global_var = 42;

/**
 * 简单的函数
 */
int add(int a, int b) {
    return a + b;
}

/**
 * 主函数
 */
int main() {
    printf("Hello, World!\\n");
    int result = add(5, 3);
    printf("5 + 3 = %d\\n", result);
    return 0;
}

// 结构体定义
struct Point {
    int x;
    int y;
};

// 枚举定义
enum Color {
    RED,
    GREEN,
    BLUE
};
""")
    
    def tearDown(self):
        """清理测试环境"""
        self.temp_dir.cleanup()
    
    def test_chunk_file_by_size(self):
        """测试按大小分块"""
        chunks = self.chunker.chunk_file_by_size(self.test_c_file)
        
        # 验证结果
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIsInstance(chunk, CodeChunk)
            self.assertLessEqual(len(chunk.content), self.chunker.chunk_size)
            self.assertEqual(chunk.metadata["strategy"], "fixed_size")
    
    def test_chunk_file_by_tree_sitter(self):
        """测试使用tree-sitter分块"""
        # 跳过测试如果tree-sitter未初始化
        if not self.chunker.ts_initialized:
            self.skipTest("tree-sitter未初始化，跳过测试")
        
        chunks = self.chunker.chunk_file_by_tree_sitter(self.test_c_file)
        
        # 验证结果
        self.assertGreater(len(chunks), 0)
        
        # 验证是否提取了函数
        function_chunks = [c for c in chunks if c.metadata.get("type") == "function"]
        self.assertGreaterEqual(len(function_chunks), 2)  # 应该至少有add和main两个函数
        
        # 验证是否提取了结构体
        struct_chunks = [c for c in chunks if c.metadata.get("type") == "struct"]
        self.assertGreaterEqual(len(struct_chunks), 1)  # 应该有Point结构体
        
        # 验证是否提取了枚举
        enum_chunks = [c for c in chunks if c.metadata.get("type") == "enum"]
        self.assertGreaterEqual(len(enum_chunks), 1)  # 应该有Color枚举
        
        # 验证是否提取了头部注释
        header_chunks = [c for c in chunks if c.metadata.get("type") == "header_comment"]
        self.assertGreaterEqual(len(header_chunks), 1)  # 应该有文件头注释
        
        # 验证函数名称是否正确
        function_names = [c.function_name for c in function_chunks]
        self.assertIn("add", function_names)
        self.assertIn("main", function_names)
        
        # 验证每个块的元数据
        for chunk in chunks:
            self.assertEqual(chunk.metadata["strategy"], "tree_sitter")
            self.assertIsNotNone(chunk.metadata.get("type"))
            self.assertEqual(chunk.metadata["source"], self.test_c_file)
    
    def test_nonexistent_file(self):
        """测试处理不存在的文件"""
        chunks = self.chunker.chunk_file_by_size("nonexistent_file.c")
        self.assertEqual(len(chunks), 0)
        
        if self.chunker.ts_initialized:
            chunks = self.chunker.chunk_file_by_tree_sitter("nonexistent_file.c")
            self.assertEqual(len(chunks), 0)
    
    def test_empty_file(self):
        """测试处理空文件"""
        empty_file = os.path.join(self.temp_dir.name, "empty.c")
        with open(empty_file, "w") as f:
            f.write("")
        
        chunks = self.chunker.chunk_file_by_size(empty_file)
        self.assertEqual(len(chunks), 0)
        
        if self.chunker.ts_initialized:
            chunks = self.chunker.chunk_file_by_tree_sitter(empty_file)
            self.assertEqual(len(chunks), 0)
    
    def test_invalid_chunk_params(self):
        """测试无效的分块参数"""
        with self.assertRaises(ValueError):
            CodeChunker(chunk_size=100, chunk_overlap=100)
        
        with self.assertRaises(ValueError):
            CodeChunker(chunk_size=100, chunk_overlap=150)


if __name__ == "__main__":
    unittest.main() 