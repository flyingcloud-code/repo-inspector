"""
C语言解析器模块

使用tree-sitter解析C语言源代码，提取函数信息。
"""

import tree_sitter_c as tsc
from tree_sitter import Language, Parser
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set
import re
import os
from collections import defaultdict
import logging

from ..core.interfaces import IParser
from ..core.data_models import Function, FileInfo, ParsedCode, FunctionCall, FallbackStats, FileDependency, ModuleDependency, ProjectDependencies
from ..core.exceptions import ParseError
from ..utils.logger import get_logger


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
            self.logger = get_logger(__name__)
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
            if isinstance(file_path, str):
                file_path = Path(file_path)
                
            if not file_path.exists():
                raise ParseError(str(file_path), f"File not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            functions = self.extract_functions(content, str(file_path))
            
            # 修正：将调用关系赋值给正确的字段
            function_calls = self.extract_function_calls(tree, content, str(file_path))
            
            file_info = FileInfo.from_path(file_path)
            
            return ParsedCode(
                file_info=file_info,
                functions=functions,
                call_relationships=function_calls  # 修正字段名
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
        从源代码中提取函数信息，包括返回类型、参数和注释。
        此版本使用递归辅助函数，更健壮，可以处理更多C语言语法变体。
        """
        functions = []
        tree = self.parser.parse(bytes(source_code, 'utf-8'))

        query = self.language.query("(function_definition) @func")
        captures = query.captures(tree.root_node)

        def get_func_name(declarator_node):
            """递归地从一个声明节点中找到最终的函数名标识符。"""
            if not declarator_node:
                return None
            if declarator_node.type == 'identifier':
                return declarator_node.text.decode('utf-8')
            
            nested_declarator = declarator_node.child_by_field_name('declarator')
            return get_func_name(nested_declarator)

        for node, name in captures:
            if name == "func":
                declarator_node = node.child_by_field_name('declarator')
                type_node = node.child_by_field_name('type')

                func_name = get_func_name(declarator_node)
                parameters = []
                
                if declarator_node:
                    params_node = declarator_node.child_by_field_name('parameters')
                    if params_node:
                        # 正确处理 (void) 参数
                        if len(params_node.named_children) == 1 and params_node.named_children[0].type == 'parameter_declaration' and params_node.named_children[0].text.decode('utf-8') == 'void':
                             parameters = ['void']
                        else:
                            param_texts = [p.text.decode('utf-8') for p in params_node.named_children if p.type == 'parameter_declaration']
                            parameters = [' '.join(pt.split()) for pt in param_texts]

                return_type = type_node.text.decode('utf-8').strip() if type_node else "void"

                docstring = self.extract_function_docstring(node, source_code)
                
                if func_name:
                    functions.append(Function(
                        name=func_name,
                        code=node.text.decode('utf-8'),
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        file_path=file_path,
                        parameters=parameters,
                        return_type=return_type,
                        docstring=docstring
                    ))
        
        return functions

    def _fallback_extract_functions(self, source_code: str, file_path: str) -> List[Function]:
        """
        旧的、更简单的函数提取方法，作为备用
        """
        self.logger.warning(f"Using fallback function extractor for {file_path}")
        functions = []
        tree = self.parser.parse(bytes(source_code, 'utf-8'))
        query = self.language.query("(function_definition) @func")
        for node, name in query.captures(tree.root_node):
            func_name_node = node.child_by_field_name("declarator").child_by_field_name("declarator")
            if func_name_node:
                functions.append(Function(
                    name=func_name_node.text.decode('utf-8'),
                    code=node.text.decode('utf-8'),
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                    file_path=file_path
                ))
        return functions
    
    def extract_function_calls(self, tree, source_code: str, file_path: str) -> List[FunctionCall]:
        """从源代码中提取函数调用关系（Tree-sitter实现）
        
        Args:
            tree: Tree-sitter解析的树
            source_code: C源代码
            file_path: 当前文件路径
            
        Returns:
            List[FunctionCall]: 调用关系列表
        """
        call_relationships: List[FunctionCall] = []
        query = self.language.query("(call_expression) @call")
        captures = query.captures(tree.root_node)

        def find_enclosing_function(node):
            temp = node
            while temp:
                if temp.type == 'function_definition':
                    name_node = temp.child_by_field_name('declarator').child_by_field_name('declarator')
                    if name_node:
                        return name_node.text.decode('utf-8')
                temp = temp.parent
                return None

        for node, name in captures:
            caller_name = find_enclosing_function(node)
            if not caller_name:
                continue

            callee_node = node.child_by_field_name('function')
            if callee_node and callee_node.type == 'identifier':
                callee_name = callee_node.text.decode('utf-8')
                call_context = ""
                # 循环查找，跳过空白节点
                comment_node = node.prev_sibling
                while comment_node and not comment_node.is_named:
                    comment_node = comment_node.prev_sibling
                if comment_node and comment_node.type == 'comment':
                    call_context = comment_node.text.decode('utf-8').strip()

                call_relationships.append(FunctionCall(
                    caller_name=caller_name,
                            callee_name=callee_name,
                    call_type='direct',  # 简化处理，后续可扩展
                    line_number=node.start_point[0] + 1,
                            file_path=file_path,
                    context=call_context
                ))

        return call_relationships
    
    def get_fallback_statistics(self):
        """获取fallback统计信息 - 占位实现
        
        Returns:
            FallbackStats: fallback使用统计
            
        Raises:
            NotImplementedError: 功能将在Story 2.1.3中实现
        """
        raise NotImplementedError("get_fallback_statistics will be implemented in Story 2.1.3")

    def extract_file_dependencies(self, file_path: Path) -> List[FileDependency]:
        """提取文件依赖关系（主要是#include语句）
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[FileDependency]: 文件依赖关系列表
        """
        self.logger.info(f"提取文件依赖关系: {file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
        except Exception as e:
            self.logger.error(f"读取文件失败: {e}")
            raise ParseError(f"读取文件失败: {e}")
        
        dependencies = []
        
        # 使用正则表达式匹配所有#include语句
        # 匹配系统头文件 #include <xxx.h>
        system_includes = re.finditer(r'#include\s*<([^>]+)>', source_code)
        for match in system_includes:
            target_file = match.group(1)
            line_number = source_code[:match.start()].count('\n') + 1
            
            # 获取上下文（include语句所在行）
            lines = source_code.splitlines()
            context = lines[line_number - 1] if line_number <= len(lines) else ""
            
            # 尝试解析路径，若能在项目内解析到真实文件则认为是项目头文件
            resolved_path = self._resolve_include_path(file_path, target_file)
            is_system = True
            target_resolved = target_file
            if resolved_path and resolved_path.exists():
                is_system = False
                target_resolved = str(resolved_path)

            dependency = FileDependency(
                source_file=str(file_path),
                target_file=target_resolved,
                dependency_type="include",
                is_system=is_system,
                line_number=line_number,
                context=context
            )
            dependencies.append(dependency)
        
        # 匹配项目头文件 #include "xxx.h"
        project_includes = re.finditer(r'#include\s*"([^"]+)"', source_code)
        for match in project_includes:
            target_file = match.group(1)
            line_number = source_code[:match.start()].count('\n') + 1
            
            # 获取上下文（include语句所在行）
            lines = source_code.splitlines()
            context = lines[line_number - 1] if line_number <= len(lines) else ""
            
            # 尝试解析相对路径
            target_path = self._resolve_include_path(file_path, target_file)
            
            dependency = FileDependency(
                source_file=str(file_path),
                target_file=str(target_path) if target_path else target_file,
                dependency_type="include",
                is_system=False,
                line_number=line_number,
                context=context
            )
            dependencies.append(dependency)
        
        self.logger.debug(f"找到 {len(dependencies)} 个依赖关系")
        return dependencies
    
    def _resolve_include_path(self, source_file: Path, include_path: str) -> Optional[Path]:
        """解析#include中的相对路径
        
        Args:
            source_file: 源文件路径
            include_path: include中的路径
            
        Returns:
            Optional[Path]: 解析后的绝对路径，如果无法解析则返回None
        """
        # 首先尝试直接在源文件目录下查找
        direct_path = source_file.parent / include_path
        if direct_path.exists():
            return direct_path
        
        # 尝试在源文件的上级目录查找
        parent_path = source_file.parent.parent / include_path
        if parent_path.exists():
            return parent_path
        
        # 尝试在项目根目录下的include目录查找
        # 假设项目结构是标准的，根目录下有include目录
        root_dirs = ["include", "inc", "headers"]
        for i in range(3):  # 向上查找3级
            current = source_file.parent
            for _ in range(i):
                if current.parent == current:  # 已经是根目录
                    break
                current = current.parent
                
            for root_dir in root_dirs:
                include_dir = current / root_dir
                if include_dir.exists():
                    include_file = include_dir / include_path
                    if include_file.exists():
                        return include_file
        
        # 无法解析，返回None
        return None
    
    def analyze_project_dependencies(self, project_path: Path) -> ProjectDependencies:
        """分析项目依赖关系
        
        Args:
            project_path: 项目路径
            
        Returns:
            ProjectDependencies: 项目依赖关系
        """
        self.logger.info(f"分析项目依赖关系: {project_path}")
        
        if not project_path.exists() or not project_path.is_dir():
            raise FileNotFoundError(f"项目目录不存在: {project_path}")
        
        # 1. 收集所有C和头文件
        c_files = list(project_path.glob("**/*.c"))
        h_files = list(project_path.glob("**/*.h"))
        all_files = c_files + h_files
        
        self.logger.debug(f"找到 {len(c_files)} 个C文件和 {len(h_files)} 个头文件")
        
        # 2. 提取所有文件依赖关系
        file_dependencies = []
        for file_path in all_files:
            try:
                deps = self.extract_file_dependencies(file_path)
                file_dependencies.extend(deps)
            except Exception as e:
                self.logger.warning(f"提取文件依赖关系失败 {file_path}: {e}")
        
        # 3. 构建模块依赖关系
        module_dependencies = self._build_module_dependencies(file_dependencies, project_path)
        
        # 4. 检测循环依赖
        circular_dependencies = self._detect_circular_dependencies(module_dependencies)
        
        # 5. 计算模块化评分
        modularity_score = self._calculate_modularity_score(module_dependencies, circular_dependencies)
        
        # 6. 构建项目依赖关系
        project_deps = ProjectDependencies(
            file_dependencies=file_dependencies,
            module_dependencies=module_dependencies,
            circular_dependencies=circular_dependencies,
            modularity_score=modularity_score
        )
        
        self.logger.info(f"项目依赖分析完成: {len(file_dependencies)} 文件依赖, "
                        f"{len(module_dependencies)} 模块依赖, "
                        f"{len(circular_dependencies)} 循环依赖")
        
        return project_deps
    
    def _build_module_dependencies(self, file_dependencies: List[FileDependency], 
                                 project_path: Path) -> List[ModuleDependency]:
        """构建模块依赖关系
        
        Args:
            file_dependencies: 文件依赖关系列表
            project_path: 项目路径
            
        Returns:
            List[ModuleDependency]: 模块依赖关系列表
        """
        # 模块定义：基于目录结构，每个一级子目录视为一个模块
        module_deps_map = defaultdict(lambda: defaultdict(list))
        
        # 过滤掉系统头文件依赖
        project_deps = [dep for dep in file_dependencies if not dep.is_system]
        
        for dep in project_deps:
            # 处理源文件路径
            source_file = Path(dep.source_file)
            if not source_file.is_absolute():
                source_file = project_path / source_file
            
            # 处理目标文件路径
            target_file = Path(dep.target_file)
            if not target_file.is_absolute():
                # 如果是相对路径，尝试从源文件位置解析
                source_dir = source_file.parent
                resolved_target = source_dir / target_file
                if not resolved_target.exists():
                    # 尝试使用项目路径解析
                    resolved_target = project_path / target_file
                    if not resolved_target.exists():
                        # 尝试使用_resolve_include_path方法解析
                        resolved = self._resolve_include_path(source_file, str(target_file))
                        if resolved:
                            resolved_target = resolved
                target_file = resolved_target
            
            # 获取相对于项目根目录的路径
            try:
                rel_source = source_file.relative_to(project_path)
                
                # 确保目标文件在项目内
                if str(project_path) in str(target_file):
                    rel_target = target_file.relative_to(project_path)
                else:
                    # 如果目标文件不在项目内，跳过
                    self.logger.debug(f"目标文件不在项目内: {target_file}")
                    continue
            except ValueError as e:
                self.logger.debug(f"无法解析相对路径: {e}")
                continue  # 跳过不在项目内的文件
            
            # 提取模块名（一级目录）
            source_module = rel_source.parts[0] if len(rel_source.parts) > 0 else "root"
            target_module = rel_target.parts[0] if len(rel_target.parts) > 0 else "root"
            
            # 跳过自依赖
            if source_module == target_module:
                continue
            
            # 记录模块间依赖关系
            module_deps_map[source_module][target_module].append((str(source_file), str(target_file)))
            self.logger.debug(f"添加模块依赖: {source_module} -> {target_module}")
        
        # 构建ModuleDependency对象
        module_dependencies = []
        for source_module, targets in module_deps_map.items():
            for target_module, files in targets.items():
                # 计算依赖强度（基于依赖文件数量）
                source_files_count = len(list(project_path.glob(f"{source_module}/**/*.c")))
                strength = len(files) / max(1, source_files_count)
                
                module_dep = ModuleDependency(
                    source_module=source_module,
                    target_module=target_module,
                    file_count=len(files),
                    strength=min(1.0, strength),  # 强度最大为1.0
                    files=files
                )
                module_dependencies.append(module_dep)
                self.logger.debug(f"创建模块依赖: {source_module} -> {target_module}, 文件数: {len(files)}")
        
        return module_dependencies
    
    def _detect_circular_dependencies(self, module_dependencies: List[ModuleDependency]) -> List[List[str]]:
        """检测循环依赖
        
        Args:
            module_dependencies: 模块依赖关系列表
            
        Returns:
            List[List[str]]: 循环依赖链列表
        """
        # 构建依赖图
        graph = defaultdict(set)
        for dep in module_dependencies:
            graph[dep.source_module].add(dep.target_module)
        
        # 深度优先搜索检测环
        def find_cycles(node, path=None, visited=None):
            if path is None:
                path = []
            if visited is None:
                visited = set()
            
            path.append(node)
            visited.add(node)
            
            cycles = []
            for neighbor in graph[node]:
                if neighbor in path:
                    # 找到环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    sub_cycles = find_cycles(neighbor, path.copy(), visited.copy())
                    cycles.extend(sub_cycles)
            
            return cycles
        
        # 从每个节点开始搜索
        all_cycles = []
        visited_starts = set()
        for module in list(graph.keys()):
            if module not in visited_starts:
                cycles = find_cycles(module)
                for cycle in cycles:
                    if cycle not in all_cycles:
                        all_cycles.append(cycle)
                visited_starts.add(module)
        
        # 标记循环依赖
        for dep in module_dependencies:
            for cycle in all_cycles:
                if dep.source_module in cycle and dep.target_module in cycle:
                    dep.is_circular = True
        
        return all_cycles
    
    def _calculate_modularity_score(self, module_dependencies: List[ModuleDependency], 
                                  circular_dependencies: List[List[str]]) -> float:
        """计算模块化评分
        
        评分基于以下因素：
        1. 模块间依赖数量（越少越好）
        2. 循环依赖数量（越少越好）
        3. 依赖强度（越低越好）
        
        Args:
            module_dependencies: 模块依赖关系列表
            circular_dependencies: 循环依赖链列表
            
        Returns:
            float: 模块化评分(0-1)，越高越好
        """
        if not module_dependencies:
            return 1.0  # 没有依赖，完全模块化
        
        # 获取所有模块
        all_modules = set()
        for dep in module_dependencies:
            all_modules.add(dep.source_module)
            all_modules.add(dep.target_module)
        
        module_count = len(all_modules)
        if module_count <= 1:
            return 1.0  # 只有一个模块
        
        # 理论上最大可能的依赖数（完全连接图）
        max_possible_deps = module_count * (module_count - 1)
        
        # 实际依赖数
        actual_deps = len(module_dependencies)
        
        # 依赖密度 (0-1)，越低越好
        dependency_density = actual_deps / max_possible_deps if max_possible_deps > 0 else 0
        
        # 平均依赖强度 (0-1)，越低越好
        avg_strength = sum(dep.strength for dep in module_dependencies) / actual_deps if actual_deps > 0 else 0
        
        # 循环依赖比例 (0-1)，越低越好
        circular_deps_count = sum(1 for dep in module_dependencies if dep.is_circular)
        circular_ratio = circular_deps_count / actual_deps if actual_deps > 0 else 0
        
        # 计算最终得分 (0-1)，越高越好
        # 权重可以根据实际需求调整
        score = 1.0 - (0.4 * dependency_density + 0.3 * avg_strength + 0.3 * circular_ratio)
        
        # 确保分数在0-1范围内
        return max(0.0, min(1.0, score)) 

    def extract_function_docstring(self, function_node, source_code: str) -> str:
        """
        提取函数的文档字符串，支持多种注释格式
        
        Args:
            function_node: Tree-sitter函数定义节点
            source_code: 源代码字符串
            
        Returns:
            str: 清理后的文档字符串
        """
        # 向前搜索注释节点
        comments = []
        current_node = function_node.prev_sibling
        search_limit = 15  # 最多向前搜索15个节点
        
        while current_node and search_limit > 0:
            if current_node.type == 'comment':
                comments.insert(0, current_node.text.decode('utf-8'))
            elif current_node.is_named:
                # 遇到其他有名节点（如其他函数、变量声明等），停止搜索
                break
            current_node = current_node.prev_sibling
            search_limit -= 1
        
        # 处理找到的注释
        if not comments:
            return ""
        
        # 合并和清理注释内容
        docstring_parts = []
        for comment_text in comments:
            cleaned = self._clean_comment_text(comment_text)
            if cleaned:
                docstring_parts.append(cleaned)
        
        return '\n'.join(docstring_parts).strip()
    
    def _clean_comment_text(self, comment_text: str) -> str:
        """
        清理注释文本，移除注释标记并格式化
        
        Args:
            comment_text: 原始注释文本
            
        Returns:
            str: 清理后的注释内容
        """
        import re
        
        # 移除 C++ 风格注释 //
        if comment_text.strip().startswith('//'):
            text = comment_text.strip()[2:].strip()
            return text
        
        # 处理 /* */ 和 /** */ 风格注释
        text = comment_text
        
        # 移除开始和结束标记
        text = re.sub(r'/\*+', '', text)
        text = re.sub(r'\*+/', '', text)
        
        # 按行处理
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # 移除每行开头的 * 或 * 
            if line.startswith('*'):
                line = line[1:].strip()
            elif line.startswith('* '):
                line = line[2:].strip()
            
            # 保留非空行
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip() 