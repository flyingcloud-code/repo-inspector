"""
代码分块器

负责将代码文件分割成语义完整的块，以便进行向量嵌入和检索。
实现重叠策略，确保上下文连续性。
"""
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging
from enum import Enum, auto
import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_c as tsc
from pathlib import Path

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChunkingStrategy(Enum):
    """分块策略"""
    SEMANTIC = auto()  # 从Neo4j获取语义块
    FIXED_SIZE = auto()  # 固定大小分块
    TREE_SITTER = auto()  # 使用tree-sitter直接进行语义分块，不依赖Neo4j


@dataclass
class CodeChunk:
    """代码块"""
    id: str
    content: str
    metadata: Dict[str, Any]
    start_line: int
    end_line: int
    file_path: Optional[str] = None
    function_name: Optional[str] = None


class CodeChunker:
    """代码分块器
    
    提供将代码文件按固定大小或语义单元分割成块的功能。
    """
    
    def __init__(self, 
                chunk_size: int = 512,  # 块大小（字符数）
                chunk_overlap: int = 100  # 块重叠（字符数）
                ):
        """初始化代码分块器
        
        Args:
            chunk_size: 块大小（字符数）
            chunk_overlap: 块重叠（字符数）
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("块重叠必须小于块大小")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # 初始化tree-sitter解析器
        try:
            self.language = Language(tsc.language(), 'c')
            self.parser = Parser()
            self.parser.set_language(self.language)
            self.ts_initialized = True
        except Exception as e:
            logger.warning(f"初始化tree-sitter解析器失败: {e}")
            self.ts_initialized = False
        
        logger.info(f"初始化代码分块器: chunk_size={chunk_size} chars, overlap={chunk_overlap} chars")
    
    def chunk_file_by_size(self, file_path: str) -> List[CodeChunk]:
        """将文件按固定字符大小分块
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[CodeChunk]: 代码块列表
        """
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._chunk_content_by_size(content, file_path)
                
        except Exception as e:
            logger.error(f"文件按大小分块失败: {file_path}, 错误: {e}", exc_info=True)
            return []
    
    def _chunk_content_by_size(self, content: str, source_id: str) -> List[CodeChunk]:
        """将内容字符串按固定字符大小分块
        
        Args:
            content: 文本内容
            source_id: 源标识符
            
        Returns:
            List[CodeChunk]: 代码块列表
        """
        chunks = []
        content_len = len(content)
        if content_len == 0:
            return chunks

        i = 0
        chunk_id_counter = 0
        while i < content_len:
            end = i + self.chunk_size
            chunk_content = content[i:end]
            
            # 简单的行号估算
            start_line = content.count('\n', 0, i) + 1
            end_line = content.count('\n', 0, i + len(chunk_content)) + 1

            chunks.append(CodeChunk(
                id=f"{source_id}_{chunk_id_counter}",
                content=chunk_content,
                metadata={
                    "source": source_id,
                    "strategy": "fixed_size",
                    "chunk_id": chunk_id_counter,
                },
                start_line=start_line,
                end_line=end_line,
                file_path=source_id if os.path.exists(source_id) else None
            ))
            
            i += self.chunk_size - self.chunk_overlap
            chunk_id_counter += 1
        
        return chunks
    
    def chunk_file_by_tree_sitter(self, file_path: str) -> List[CodeChunk]:
        """使用tree-sitter直接进行语义分块，不依赖Neo4j
        
        基于tree-sitter解析器识别代码中的语义单元（函数、结构体定义等），
        并将它们作为独立的代码块。
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[CodeChunk]: 代码块列表
        """
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return []
        
        if not self.ts_initialized:
            logger.warning("tree-sitter解析器未初始化，无法进行语义分块")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析代码
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            # 提取语义单元
            chunks = []
            
            # 1. 提取函数定义
            function_chunks = self._extract_function_chunks(tree, content, file_path)
            chunks.extend(function_chunks)
            
            # 2. 提取结构体和枚举定义
            struct_enum_chunks = self._extract_struct_enum_chunks(tree, content, file_path)
            chunks.extend(struct_enum_chunks)
            
            # 3. 提取全局变量和宏定义
            global_macro_chunks = self._extract_global_macro_chunks(tree, content, file_path)
            chunks.extend(global_macro_chunks)
            
            # 4. 提取文件头部注释
            header_comment_chunks = self._extract_header_comment_chunks(tree, content, file_path)
            chunks.extend(header_comment_chunks)
            
            # 如果没有提取到任何语义块，则回退到按大小分块
            if not chunks:
                logger.warning(f"未从文件中提取到语义块，回退到按大小分块: {file_path}")
                return self.chunk_file_by_size(file_path)
            
            # 按照在文件中的位置排序
            chunks.sort(key=lambda x: x.start_line)
            
            return chunks
                
        except Exception as e:
            logger.error(f"文件按tree-sitter语义分块失败: {file_path}, 错误: {e}", exc_info=True)
            # 出错时回退到按大小分块
            logger.info(f"回退到按大小分块: {file_path}")
            return self.chunk_file_by_size(file_path)
    
    def _extract_function_chunks(self, tree, content: str, file_path: str) -> List[CodeChunk]:
        """提取函数定义作为代码块
        
        Args:
            tree: tree-sitter解析树
            content: 源代码内容
            file_path: 文件路径
            
        Returns:
            List[CodeChunk]: 函数代码块列表
        """
        chunks = []
        
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
                
                # 提取函数源代码
                function_source = content[node.start_byte:node.end_byte]
                
                function_data[node.id] = {
                    'start_line': start_line,
                    'end_line': end_line,
                    'source': function_source,
                    'name': None,
                    'node': node
                }
                
            elif capture_name == "function.name":
                # 查找对应的函数定义节点
                parent = node.parent
                while parent and parent.type != "function_definition":
                    parent = parent.parent
                
                if parent and parent.id in function_data:
                    function_name = content[node.start_byte:node.end_byte]
                    function_data[parent.id]['name'] = function_name
        
        # 创建函数代码块
        for func_id, data in function_data.items():
            if data['name']:  # 只处理有名称的函数
                chunk_id = f"{os.path.basename(file_path)}_{data['name']}"
                chunks.append(CodeChunk(
                    id=chunk_id,
                    content=data['source'],
                    metadata={
                        'source': file_path,
                        'strategy': 'tree_sitter',
                        'type': 'function',
                        'name': data['name'],
                    },
                    start_line=data['start_line'],
                    end_line=data['end_line'],
                    file_path=file_path,
                    function_name=data['name']
                ))
        
        return chunks
    
    def _extract_struct_enum_chunks(self, tree, content: str, file_path: str) -> List[CodeChunk]:
        """提取结构体和枚举定义作为代码块
        
        Args:
            tree: tree-sitter解析树
            content: 源代码内容
            file_path: 文件路径
            
        Returns:
            List[CodeChunk]: 结构体和枚举代码块列表
        """
        chunks = []
        
        # 查询所有结构体和枚举定义
        query = self.language.query("""
        (struct_specifier
          name: (type_identifier) @struct.name) @struct.def
        (enum_specifier
          name: (type_identifier) @enum.name) @enum.def
        """)
        
        captures = query.captures(tree.root_node)
        
        # 按定义分组处理captures
        struct_enum_data = {}
        
        for node, capture_name in captures:
            if capture_name == "struct.def" or capture_name == "enum.def":
                # 获取起始和结束行号
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                
                # 提取源代码
                source = content[node.start_byte:node.end_byte]
                
                type_name = "struct" if capture_name == "struct.def" else "enum"
                
                struct_enum_data[node.id] = {
                    'start_line': start_line,
                    'end_line': end_line,
                    'source': source,
                    'name': None,
                    'type': type_name
                }
                
            elif capture_name == "struct.name" or capture_name == "enum.name":
                # 查找对应的定义节点
                parent = node.parent
                parent_type = "struct_specifier" if capture_name == "struct.name" else "enum_specifier"
                
                while parent and parent.type != parent_type:
                    parent = parent.parent
                
                if parent and parent.id in struct_enum_data:
                    name = content[node.start_byte:node.end_byte]
                    struct_enum_data[parent.id]['name'] = name
        
        # 创建结构体和枚举代码块
        chunk_id_counter = 0
        for data_id, data in struct_enum_data.items():
            if data['name']:  # 只处理有名称的定义
                chunk_id = f"{os.path.basename(file_path)}_{data['type']}_{data['name']}"
                chunks.append(CodeChunk(
                    id=chunk_id,
                    content=data['source'],
                    metadata={
                        'source': file_path,
                        'strategy': 'tree_sitter',
                        'type': data['type'],
                        'name': data['name'],
                    },
                    start_line=data['start_line'],
                    end_line=data['end_line'],
                    file_path=file_path
                ))
                chunk_id_counter += 1
        
        return chunks
    
    def _extract_global_macro_chunks(self, tree, content: str, file_path: str) -> List[CodeChunk]:
        """提取全局变量和宏定义作为代码块
        
        Args:
            tree: tree-sitter解析树
            content: 源代码内容
            file_path: 文件路径
            
        Returns:
            List[CodeChunk]: 全局变量和宏定义代码块列表
        """
        chunks = []
        
        # 查询所有全局变量声明和宏定义
        query = self.language.query("""
        (declaration
          (identifier) @global_var.name) @global_var.def
        (preproc_def
          name: (identifier) @macro.name) @macro.def
        """)
        
        captures = query.captures(tree.root_node)
        
        # 处理全局变量和宏定义
        global_macro_data = {}
        
        for node, capture_name in captures:
            if capture_name == "global_var.def" or capture_name == "macro.def":
                # 检查是否在函数内部
                parent = node.parent
                in_function = False
                while parent:
                    if parent.type == "function_definition":
                        in_function = True
                        break
                    parent = parent.parent
                
                if in_function:
                    continue  # 跳过函数内部的声明
                
                # 获取起始和结束行号
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                
                # 提取源代码
                source = content[node.start_byte:node.end_byte]
                
                type_name = "global_var" if capture_name == "global_var.def" else "macro"
                
                global_macro_data[node.id] = {
                    'start_line': start_line,
                    'end_line': end_line,
                    'source': source,
                    'name': None,
                    'type': type_name
                }
                
            elif capture_name == "global_var.name" or capture_name == "macro.name":
                # 查找对应的定义节点
                parent = node.parent
                parent_type = "declaration" if capture_name == "global_var.name" else "preproc_def"
                
                while parent and parent.type != parent_type:
                    parent = parent.parent
                
                if parent and parent.id in global_macro_data:
                    name = content[node.start_byte:node.end_byte]
                    global_macro_data[parent.id]['name'] = name
        
        # 创建全局变量和宏定义代码块
        chunk_id_counter = 0
        for data_id, data in global_macro_data.items():
            if data['name']:  # 只处理有名称的定义
                chunk_id = f"{os.path.basename(file_path)}_{data['type']}_{data['name']}"
                chunks.append(CodeChunk(
                    id=chunk_id,
                    content=data['source'],
                    metadata={
                        'source': file_path,
                        'strategy': 'tree_sitter',
                        'type': data['type'],
                        'name': data['name'],
                    },
                    start_line=data['start_line'],
                    end_line=data['end_line'],
                    file_path=file_path
                ))
                chunk_id_counter += 1
        
        return chunks
    
    def _extract_header_comment_chunks(self, tree, content: str, file_path: str) -> List[CodeChunk]:
        """提取文件头部注释作为代码块
        
        Args:
            tree: tree-sitter解析树
            content: 源代码内容
            file_path: 文件路径
            
        Returns:
            List[CodeChunk]: 头部注释代码块列表
        """
        chunks = []
        
        # 提取文件顶部的注释
        # 查找文件开头的所有注释节点
        query = self.language.query("""
        (comment) @file.comment
        """)
        
        captures = query.captures(tree.root_node)
        
        # 收集文件开头的连续注释
        header_comments = []
        last_end_line = 0
        
        for node, capture_name in captures:
            if capture_name == "file.comment":
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                
                # 只考虑文件开头的注释或者与前一个注释相邻的注释
                if start_line <= 10 or (last_end_line > 0 and start_line - last_end_line <= 2):
                    comment_text = content[node.start_byte:node.end_byte]
                    header_comments.append({
                        'text': comment_text,
                        'start_line': start_line,
                        'end_line': end_line
                    })
                    last_end_line = end_line
                else:
                    # 不再是文件头部的注释，停止收集
                    break
        
        # 如果有头部注释，创建一个代码块
        if header_comments:
            # 合并连续的注释
            combined_text = "\n".join(comment['text'] for comment in header_comments)
            start_line = header_comments[0]['start_line']
            end_line = header_comments[-1]['end_line']
            
            chunk_id = f"{os.path.basename(file_path)}_header_comment"
            chunks.append(CodeChunk(
                id=chunk_id,
                content=combined_text,
                metadata={
                    'source': file_path,
                    'strategy': 'tree_sitter',
                    'type': 'header_comment',
                },
                start_line=start_line,
                end_line=end_line,
                file_path=file_path
            ))
        
        return chunks 