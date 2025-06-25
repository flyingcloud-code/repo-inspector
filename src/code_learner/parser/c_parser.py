"""
C语言解析器模块

使用tree-sitter解析C语言源代码，提取函数信息。
"""

import tree_sitter_c as tsc
from tree_sitter import Language, Parser
from pathlib import Path
from typing import List, Optional

from ..core.interfaces import IParser
from ..core.data_models import Function, FileInfo, ParsedCode, FunctionCall
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
        解析单个C文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            ParsedCode: 解析结果
        """
        try:
            # 确保路径是 Path 对象
            if isinstance(file_path, str):
                file_path = Path(file_path)
                
            if not file_path.exists():
                raise ParseError(str(file_path), f"File not found: {file_path}")
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析代码
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            # 提取函数信息
            functions = self.extract_functions(content, str(file_path))
            
            # 提取函数调用关系 (Story 2.1.3)
            try:
                call_relationships = self.extract_function_calls(content, str(file_path))
            except NotImplementedError:
                call_relationships = []
            
            # 创建文件信息
            file_info = FileInfo.from_path(file_path)
            
            return ParsedCode(
                file_info=file_info,
                functions=functions,
                call_relationships=call_relationships
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

    # Story 2.1 新增方法 - 占位实现 (将在Story 2.1.3中正式实现)
    
    def extract_function_calls(self, source_code: str, file_path: str) -> List[FunctionCall]:
        """从源代码中提取函数调用关系（Tree-sitter实现）
        
        Args:
            source_code: C源代码
            file_path: 当前文件路径
            
        Returns:
            List[FunctionCall]: 调用关系列表
        """
        call_relationships: List[FunctionCall] = []

        try:
            tree = self.parser.parse(bytes(source_code, "utf-8"))

            # 辅助函数：获取函数名节点
            def _get_function_name(func_def_node) -> Optional[str]:
                # function_definition -> function_declarator -> identifier
                for child in func_def_node.children:
                    if child.type == "function_declarator":
                        ident = child.child_by_field_name("declarator") or child.child_by_field_name("identifier")
                        # tree-sitter-c 0.21 uses child_by_field_name("declarator") sometimes
                        if ident and ident.type == "identifier":
                            return ident.text.decode("utf-8")
                return None

            # 遍历 AST 并记录调用
            cursor = tree.walk()

            def _traverse(node, current_func: Optional[str]):
                # 如果遇到函数定义，更新当前函数
                if node.type == "function_definition":
                    current_func = _get_function_name(node)

                # 处理调用表达式
                if node.type == "call_expression" and current_func:
                    func_node = node.child_by_field_name("function")
                    if func_node is None:
                        func_node = node.child(0)  # 兜底

                    # 识别调用类型与被调用者
                    call_type = "direct"
                    callee_name = "unknown"

                    if func_node.type == "identifier":
                        callee_name = func_node.text.decode("utf-8")
                        if callee_name == current_func:
                            call_type = "recursive"
                    elif func_node.type in ("field_expression", "member_expression"):
                        call_type = "member"
                        # 取最后一个 identifier 作为函数名
                        id_node = None
                        for ch in func_node.children:
                            if ch.type == "identifier":
                                id_node = ch
                        if id_node:
                            callee_name = id_node.text.decode("utf-8")
                    elif func_node.type == "pointer_expression":
                        call_type = "pointer"
                        # 尝试获取内部 identifier
                        id_nodes = [ch for ch in func_node.children if ch.type == "identifier"]
                        if id_nodes:
                            callee_name = id_nodes[-1].text.decode("utf-8")

                    line_no = node.start_point[0] + 1
                    context_snippet = source_code.splitlines()[line_no - 1].strip()

                    call_relationships.append(
                        FunctionCall(
                            caller_name=current_func,
                            callee_name=callee_name,
                            call_type=call_type,
                            line_number=line_no,
                            file_path=file_path,
                            context=context_snippet
                        )
                    )

                # 递归遍历子节点
                for child in node.children:
                    _traverse(child, current_func)

            _traverse(cursor.node, None)

        except Exception:
            # 解析失败时返回空列表，调用方可记录 fallback
            pass

        return call_relationships
    
    def get_fallback_statistics(self):
        """获取fallback统计信息 - 占位实现
        
        Returns:
            FallbackStats: fallback使用统计
            
        Raises:
            NotImplementedError: 功能将在Story 2.1.3中实现
        """
        raise NotImplementedError("get_fallback_statistics will be implemented in Story 2.1.3") 