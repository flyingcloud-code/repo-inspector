from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import json
import logging
import os

from ..core.data_models import (
    FileDependency, ModuleDependency, ProjectDependencies
)
from ..core.interfaces import IParser, IGraphStore, IDependencyService
from ..parser.c_parser import CParser
from ..storage.neo4j_store import Neo4jGraphStore
from ..utils.logger import get_logger


class DependencyService(IDependencyService):
    """依赖关系分析服务
    
    提供文件和模块级别的依赖关系分析功能，包括：
    1. 提取文件依赖关系（#include语句）
    2. 构建模块依赖关系
    3. 检测循环依赖
    4. 生成依赖图可视化
    """
    
    def __init__(self, parser: IParser = None, graph_store: IGraphStore = None):
        """初始化依赖分析服务
        
        Args:
            parser: 代码解析器，默认使用CParser
            graph_store: 图存储，默认使用Neo4jGraphStore
        """
        self.logger = get_logger(__name__)
        self.parser = parser if parser else CParser()
        self.graph_store = graph_store if graph_store else Neo4jGraphStore()
    
    def analyze_project(self, project_path: Union[str, Path]) -> ProjectDependencies:
        """分析项目依赖关系
        
        Args:
            project_path: 项目路径
            
        Returns:
            ProjectDependencies: 项目依赖关系
        """
        if isinstance(project_path, str):
            project_path = Path(project_path)
        
        self.logger.info(f"开始分析项目依赖关系: {project_path}")
        
        # 使用解析器分析项目依赖
        project_deps = self.parser.analyze_project_dependencies(project_path)
        
        # 存储依赖关系到图数据库
        if self.graph_store.store_file_dependencies(project_deps.file_dependencies):
            self.logger.info(f"文件依赖关系已存储到图数据库")
        
        if self.graph_store.store_module_dependencies(project_deps.module_dependencies):
            self.logger.info(f"模块依赖关系已存储到图数据库")
        
        return project_deps
    
    def analyze_file(self, file_path: Union[str, Path]) -> List[FileDependency]:
        """分析单个文件的依赖关系
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[FileDependency]: 文件依赖关系列表
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        self.logger.info(f"开始分析文件依赖关系: {file_path}")
        
        # 使用解析器提取文件依赖
        dependencies = self.parser.extract_file_dependencies(file_path)
        
        # 存储依赖关系到图数据库
        if self.graph_store.store_file_dependencies(dependencies):
            self.logger.info(f"文件依赖关系已存储到图数据库")
        
        return dependencies
    
    def get_file_dependencies(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取文件依赖关系
        
        Args:
            file_path: 文件路径，如果为None则获取所有文件依赖
            
        Returns:
            List[Dict[str, Any]]: 文件依赖关系列表
        """
        return self.graph_store.query_file_dependencies(file_path)
    
    def get_module_dependencies(self, module_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取模块依赖关系
        
        Args:
            module_name: 模块名称，如果为None则获取所有模块依赖
            
        Returns:
            List[Dict[str, Any]]: 模块依赖关系列表
        """
        return self.graph_store.query_module_dependencies(module_name)
    
    def get_circular_dependencies(self) -> List[List[str]]:
        """获取循环依赖
        
        Returns:
            List[List[str]]: 循环依赖链列表
        """
        return self.graph_store.detect_circular_dependencies()
    
    def generate_dependency_graph(self, 
                                output_format: str = "mermaid", 
                                scope: str = "module",
                                focus_item: Optional[str] = None) -> str:
        """生成依赖关系图
        
        Args:
            output_format: 输出格式，支持 "mermaid", "json", "dot", "ascii"
            scope: 依赖范围，支持 "file", "module"
            focus_item: 聚焦的文件或模块，如果为None则显示全部
            
        Returns:
            str: 依赖图表示
        """
        self.logger.info(f"生成依赖图: 格式={output_format}, 范围={scope}, 聚焦={focus_item}")
        
        if scope == "file":
            dependencies = self.get_file_dependencies(focus_item)
            return self._generate_file_dependency_graph(dependencies, output_format, focus_item)
        elif scope == "module":
            dependencies = self.get_module_dependencies(focus_item)
            return self._generate_module_dependency_graph(dependencies, output_format, focus_item)
        else:
            raise ValueError(f"不支持的依赖范围: {scope}")
    
    def _generate_file_dependency_graph(self, 
                                      dependencies: List[Dict[str, Any]], 
                                      output_format: str,
                                      focus_file: Optional[str] = None) -> str:
        """生成文件依赖图
        
        Args:
            dependencies: 文件依赖关系列表
            output_format: 输出格式
            focus_file: 聚焦的文件
            
        Returns:
            str: 依赖图表示
        """
        if not dependencies:
            return "没有找到依赖关系"
        
        if output_format == "json":
            return json.dumps(dependencies, indent=2, ensure_ascii=False)
        
        elif output_format == "mermaid":
            # 生成Mermaid格式的依赖图
            mermaid = "graph LR\n"
            
            # 添加节点样式
            mermaid += "    %% 节点样式\n"
            mermaid += "    classDef systemFile fill:#f9f,stroke:#333,stroke-width:1px;\n"
            mermaid += "    classDef projectFile fill:#bbf,stroke:#333,stroke-width:1px;\n"
            mermaid += "    classDef focusFile fill:#fbb,stroke:#f00,stroke-width:2px;\n\n"
            
            # 添加节点和边
            added_nodes = set()
            for dep in dependencies:
                source_id = f"f{hash(dep['source_file']) % 10000:04d}"
                target_id = f"f{hash(dep['target_file']) % 10000:04d}"
                
                # 添加源文件节点
                if dep['source_file'] not in added_nodes:
                    source_name = os.path.basename(dep['source_file'])
                    mermaid += f"    {source_id}[\"{source_name}\"]\n"
                    added_nodes.add(dep['source_file'])
                
                # 添加目标文件节点
                if dep['target_file'] not in added_nodes:
                    target_name = os.path.basename(dep['target_file'])
                    mermaid += f"    {target_id}[\"{target_name}\"]\n"
                    added_nodes.add(dep['target_file'])
                
                # 添加依赖边
                mermaid += f"    {source_id} --> {target_id}\n"
            
            # 添加节点类型
            mermaid += "\n    %% 应用节点样式\n"
            for dep in dependencies:
                source_id = f"f{hash(dep['source_file']) % 10000:04d}"
                target_id = f"f{hash(dep['target_file']) % 10000:04d}"
                
                # 应用系统文件样式
                if dep['is_system']:
                    mermaid += f"    class {target_id} systemFile;\n"
                else:
                    mermaid += f"    class {target_id} projectFile;\n"
                
                mermaid += f"    class {source_id} projectFile;\n"
                
                # 应用焦点文件样式
                if focus_file:
                    if dep['source_file'] == focus_file:
                        mermaid += f"    class {source_id} focusFile;\n"
                    if dep['target_file'] == focus_file:
                        mermaid += f"    class {target_id} focusFile;\n"
            
            return mermaid
        
        elif output_format == "ascii":
            # 生成ASCII格式的依赖图
            result = "文件依赖关系:\n"
            for dep in dependencies:
                source_name = os.path.basename(dep['source_file'])
                target_name = os.path.basename(dep['target_file'])
                dep_type = "系统" if dep['is_system'] else "项目"
                result += f"{source_name} -> {target_name} ({dep_type}头文件, 行 {dep['line_number']})\n"
            return result
        
        elif output_format == "dot":
            # 生成Graphviz DOT格式的依赖图
            dot = "digraph DependencyGraph {\n"
            dot += "    rankdir=LR;\n"
            dot += "    node [shape=box];\n\n"
            
            # 添加节点和边
            for dep in dependencies:
                source_id = f"f{hash(dep['source_file']) % 10000:04d}"
                target_id = f"f{hash(dep['target_file']) % 10000:04d}"
                source_name = os.path.basename(dep['source_file'])
                target_name = os.path.basename(dep['target_file'])
                
                # 添加节点
                dot += f'    {source_id} [label="{source_name}", style=filled, fillcolor=lightblue];\n'
                
                if dep['is_system']:
                    dot += f'    {target_id} [label="{target_name}", style=filled, fillcolor=lightpink];\n'
                else:
                    dot += f'    {target_id} [label="{target_name}", style=filled, fillcolor=lightblue];\n'
                
                # 添加边
                dot += f'    {source_id} -> {target_id};\n'
            
            dot += "}\n"
            return dot
        
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
    
    def _generate_module_dependency_graph(self, 
                                        dependencies: List[Dict[str, Any]], 
                                        output_format: str,
                                        focus_module: Optional[str] = None) -> str:
        """生成模块依赖图
        
        Args:
            dependencies: 模块依赖关系列表
            output_format: 输出格式
            focus_module: 聚焦的模块
            
        Returns:
            str: 依赖图表示
        """
        if not dependencies:
            if output_format == "ascii":
                return "模块依赖关系:\n(无依赖)"
            return "没有找到依赖关系"
        
        if output_format == "json":
            return json.dumps(dependencies, indent=2, ensure_ascii=False)
        
        elif output_format == "mermaid":
            # 生成Mermaid格式的依赖图
            mermaid = "graph LR\n"
            
            # 添加节点样式
            mermaid += "    %% 节点样式\n"
            mermaid += "    classDef normalModule fill:#bbf,stroke:#333,stroke-width:1px;\n"
            mermaid += "    classDef circularModule fill:#fbb,stroke:#f00,stroke-width:1px;\n"
            mermaid += "    classDef focusModule fill:#bfb,stroke:#0a0,stroke-width:2px;\n\n"
            
            # 添加节点和边
            added_nodes = set()
            for dep in dependencies:
                source_id = f"m{hash(dep['source_module']) % 10000:04d}"
                target_id = f"m{hash(dep['target_module']) % 10000:04d}"
                
                # 添加源模块节点
                if dep['source_module'] not in added_nodes:
                    mermaid += f"    {source_id}[\"{dep['source_module']}\"]\n"
                    added_nodes.add(dep['source_module'])
                
                # 添加目标模块节点
                if dep['target_module'] not in added_nodes:
                    mermaid += f"    {target_id}[\"{dep['target_module']}\"]\n"
                    added_nodes.add(dep['target_module'])
                
                # 添加依赖边
                edge_label = f" |{dep['file_count']}文件|"
                mermaid += f"    {source_id} -->|{dep['file_count']}文件| {target_id}\n"
            
            # 添加节点类型
            mermaid += "\n    %% 应用节点样式\n"
            for dep in dependencies:
                source_id = f"m{hash(dep['source_module']) % 10000:04d}"
                target_id = f"m{hash(dep['target_module']) % 10000:04d}"
                
                # 应用循环依赖样式
                if dep['is_circular']:
                    mermaid += f"    class {source_id} circularModule;\n"
                    mermaid += f"    class {target_id} circularModule;\n"
                else:
                    mermaid += f"    class {source_id} normalModule;\n"
                    mermaid += f"    class {target_id} normalModule;\n"
                
                # 应用焦点模块样式
                if focus_module:
                    if dep['source_module'] == focus_module:
                        mermaid += f"    class {source_id} focusModule;\n"
                    if dep['target_module'] == focus_module:
                        mermaid += f"    class {target_id} focusModule;\n"
            
            return mermaid
        
        elif output_format == "ascii":
            # 生成ASCII格式的依赖图
            result = "模块依赖关系:\n"
            for dep in dependencies:
                circular = " (循环依赖)" if dep['is_circular'] else ""
                result += f"{dep['source_module']} -> {dep['target_module']} ({dep['file_count']}文件, 强度{dep['strength']:.2f}){circular}\n"
            return result
        
        elif output_format == "dot":
            # 生成Graphviz DOT格式的依赖图
            dot = "digraph ModuleDependencyGraph {\n"
            dot += "    rankdir=LR;\n"
            dot += "    node [shape=box];\n\n"
            
            # 添加节点和边
            for dep in dependencies:
                source_id = f"m{hash(dep['source_module']) % 10000:04d}"
                target_id = f"m{hash(dep['target_module']) % 10000:04d}"
                
                # 添加节点
                if dep['is_circular']:
                    dot += f'    {source_id} [label="{dep["source_module"]}", style=filled, fillcolor=lightcoral];\n'
                    dot += f'    {target_id} [label="{dep["target_module"]}", style=filled, fillcolor=lightcoral];\n'
                else:
                    dot += f'    {source_id} [label="{dep["source_module"]}", style=filled, fillcolor=lightblue];\n'
                    dot += f'    {target_id} [label="{dep["target_module"]}", style=filled, fillcolor=lightblue];\n'
                
                # 添加边
                dot += f'    {source_id} -> {target_id} [label="{dep["file_count"]}文件"];\n'
            
            dot += "}\n"
            return dot
        
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")
    
    # ------------------------------------------------------------------
    # Export helper
    # ------------------------------------------------------------------
    def export_dependency_graph(self, output_path: Path, format_type: str = "json", scope: str = "module", focus_item: Optional[str] = None) -> bool:
        """生成依赖图并导出到文件

        Args:
            output_path: 输出文件路径
            format_type: 导出格式 (json / mermaid)
            scope: 范围 (file / module)
            focus_item: 聚焦项

        Returns:
            bool: 成功标志
        """
        graph_content = self.generate_dependency_graph(format_type, scope, focus_item)

        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 如果无后缀，根据格式添加
        if not output_path.suffix:
            if format_type == "json":
                output_path = output_path.with_suffix(".json")
            elif format_type == "mermaid":
                output_path = output_path.with_suffix(".md")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(graph_content)

        self.logger.info(f"依赖图已导出到 {output_path}")
        return True 