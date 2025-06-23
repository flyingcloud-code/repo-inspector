"""
C语言解析器模块

使用tree-sitter解析C语言源代码，提取函数信息。
"""

import tree_sitter_c as tsc
from tree_sitter import Language, Parser
from pathlib import Path
from typing import List

from ..core.interfaces import IParser
from ..core.data_models import Function, FileInfo, ParsedCode
from ..core.exceptions import ParseError


class CParser(IParser):
    """C语言解析器，使用tree-sitter解析C代码"""
    
    def __init__(self):
        """初始化C语言解析器"""
        try:
            # 使用tree-sitter 0.21.3 API
            # 根据Simon Willison的示例，Language需要库文件路径和语言名称
            # 但对于tree_sitter_c模块，我们需要使用不同的方法
            from tree_sitter import Language, Parser
            import tree_sitter_c as tsc
            
            # 创建Language对象
            self.language = Language(tsc.language(), 'c')
            self.parser = Parser()
            self.parser.set_language(self.language)
        except Exception as e:
            raise ParseError("", f"Failed to initialize C parser: {e}")
    
    def parse_file(self, file_path: Path) -> ParsedCode:
        """
        解析C语言文件
        
        Args:
            file_path: C文件路径
            
        Returns:
            ParsedCode: 解析结果
        """
        try:
            if not file_path.exists():
                raise ParseError(str(file_path), f"File not found: {file_path}")
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析代码
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            # 提取函数信息
            functions = self.extract_functions(content, str(file_path))
            
            # 创建文件信息
            file_info = FileInfo.from_path(file_path)
            
            return ParsedCode(
                file_info=file_info,
                functions=functions
            )
            
        except Exception as e:
            raise ParseError(str(file_path), f"Failed to parse file {file_path}: {e}")
    
    def parse_directory(self, dir_path: Path, pattern: str = "*.c") -> List[ParsedCode]:
        """
        解析目录下的所有C文件
        
        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            List[ParsedCode]: 解析结果列表
        """
        results = []
        
        try:
            for c_file in dir_path.glob(pattern):
                if c_file.is_file():
                    result = self.parse_file(c_file)
                    results.append(result)
        except Exception as e:
            raise ParseError(str(dir_path), f"Failed to parse directory {dir_path}: {e}")
        
        return results
    
    def extract_functions(self, source_code: str, file_path: str) -> List[Function]:
        """
        从源代码中提取函数信息
        
        Args:
            source_code: C源代码字符串
            file_path: 文件路径（用于记录）
            
        Returns:
            List[Function]: 函数列表
        """
        functions = []
        
        try:
            # 解析源代码
            tree = self.parser.parse(bytes(source_code, 'utf-8'))
            
            # 查询所有函数定义
            query = self.language.query("""
            (function_definition
              (function_declarator
                (identifier) @function.name)) @function.def
            """)
            
            captures = query.captures(tree.root_node)
            
            # 按函数分组处理captures
            function_data = {}
            
            for node, capture_name in captures:
                if capture_name == "function.def":
                    # 获取函数的起始和结束行号
                    start_line = node.start_point[0] + 1  # tree-sitter使用0索引
                    end_line = node.end_point[0] + 1
                    
                    # 使用node.text提取函数源代码，避免字节范围错误
                    function_source = node.text.decode('utf-8')
                    
                    function_data[node.id] = {
                        'start_line': start_line,
                        'end_line': end_line,
                        'source': function_source,
                        'name': None
                    }
                    
                elif capture_name == "function.name":
                    # 查找对应的函数定义节点
                    parent = node.parent
                    while parent and parent.type != "function_definition":
                        parent = parent.parent
                    
                    if parent and parent.id in function_data:
                        # 使用node.text而不是字节范围，避免字节范围错误
                        function_name = node.text.decode('utf-8')
                        function_data[parent.id]['name'] = function_name
            
            # 创建Function对象
            for func_id, data in function_data.items():
                if data['name']:  # 只处理有名称的函数
                    function = Function(
                        name=data['name'],
                        code=data['source'],
                        start_line=data['start_line'],
                        end_line=data['end_line'],
                        file_path=file_path
                    )
                    functions.append(function)
            
        except Exception as e:
            # 如果查询失败，返回空列表而不是抛出异常
            # 这样可以处理语法错误的文件
            pass
        
        return functions 