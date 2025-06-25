"""
CParser单元测试
"""

import pytest
from pathlib import Path

from src.code_learner.parser.c_parser import CParser
from src.code_learner.core.exceptions import ParseError


class TestCParser:
    """CParser测试类"""
    
    def test_parser_initialization(self):
        """测试解析器初始化"""
        parser = CParser()
        assert parser.language is not None
        assert parser.parser is not None
    
    def test_parse_simple_function(self, tmp_path):
        """测试解析简单函数"""
        # 创建测试文件
        c_file = tmp_path / "test.c"
        c_code = """
int add(int a, int b) {
    return a + b;
}
"""
        c_file.write_text(c_code)
        
        # 解析文件
        parser = CParser()
        result = parser.parse_file(c_file)
        
        # 验证结果
        assert result.file_info.name == "test.c"
        assert result.file_info.path == str(c_file)
        assert len(result.functions) == 1
        
        func = result.functions[0]
        assert func.name == "add"
        assert func.start_line == 2
        assert func.end_line == 4
        assert "int add(int a, int b)" in func.code
    
    def test_parse_multiple_functions(self, tmp_path):
        """测试解析多个函数"""
        c_file = tmp_path / "multi.c"
        c_code = """
int add(int a, int b) {
    return a + b;
}

int subtract(int a, int b) {
    return a - b;
}

void print_hello() {
    printf("Hello\\n");
}
"""
        c_file.write_text(c_code)
        
        parser = CParser()
        result = parser.parse_file(c_file)
        
        assert len(result.functions) == 3
        
        # 检查函数名
        function_names = [f.name for f in result.functions]
        assert "add" in function_names
        assert "subtract" in function_names
        assert "print_hello" in function_names
    
    def test_parse_empty_file(self, tmp_path):
        """测试解析空文件"""
        c_file = tmp_path / "empty.c"
        c_file.write_text("")
        
        parser = CParser()
        result = parser.parse_file(c_file)
        
        assert len(result.functions) == 0
        assert result.file_info.name == "empty.c"
    
    def test_parse_nonexistent_file(self):
        """测试解析不存在的文件"""
        parser = CParser()
        
        with pytest.raises(ParseError, match="File not found"):
            parser.parse_file(Path("nonexistent.c"))
    
    def test_parse_file_with_syntax_error(self, tmp_path):
        """测试解析语法错误的文件"""
        c_file = tmp_path / "syntax_error.c"
        c_code = """
int add(int a, int b {  // 缺少右括号
    return a + b;
}
"""
        c_file.write_text(c_code)
        
        parser = CParser()
        # tree-sitter通常能处理语法错误，不会抛出异常
        result = parser.parse_file(c_file)
        
        # 验证文件信息仍然正确
        assert result.file_info.name == "syntax_error.c"
    
    def test_extract_functions_complex(self, tmp_path):
        """测试提取复杂函数"""
        c_file = tmp_path / "complex.c"
        c_code = """
#include <stdio.h>

// 简单函数
int simple_func() {
    return 42;
}

// 带参数的函数
int complex_func(int x, char *str, double d) {
    if (x > 0) {
        printf("%s: %f\\n", str, d);
        return x * 2;
    }
    return 0;
}

// 静态函数
static void helper_func(void) {
    // 帮助函数
}
"""
        c_file.write_text(c_code)
        
        parser = CParser()
        result = parser.parse_file(c_file)
        
        assert len(result.functions) == 3
        
        # 找到complex_func并验证
        complex_func = next(f for f in result.functions if f.name == "complex_func")
        assert "int x, char *str, double d" in complex_func.code
        assert complex_func.start_line > 0
    
    def test_parse_directory(self, tmp_path):
        """测试解析目录中的多个C文件"""
        # 创建多个C文件
        c_file1 = tmp_path / "file1.c"
        c_file1.write_text("int func1() { return 1; }")
        
        c_file2 = tmp_path / "file2.c"
        c_file2.write_text("int func2() { return 2; }")
        
        # 创建非C文件（应该被忽略）
        txt_file = tmp_path / "readme.txt"
        txt_file.write_text("This is not a C file")
        
        parser = CParser()
        results = parser.parse_directory(tmp_path)
        
        # 应该只解析C文件
        assert len(results) == 2
        
        # 验证文件名
        file_names = [result.file_info.name for result in results]
        assert "file1.c" in file_names
        assert "file2.c" in file_names
        assert "readme.txt" not in file_names 