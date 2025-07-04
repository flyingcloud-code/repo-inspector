"""
分析命令模块

实现项目代码分析功能，整合现有的code_analyzer_cli功能
"""

import os
import logging
from pathlib import Path
from typing import Optional

from ..project.project_registry import ProjectRegistry
from .code_analyzer_cli import analyze_code
from ..llm.service_factory import ServiceFactory
from ..storage.neo4j_store import Neo4jGraphStore
from ..config.config_manager import ConfigManager


logger = logging.getLogger(__name__)


class AnalyzeCommands:
    """分析命令处理器"""
    
    def __init__(self):
        """初始化分析命令处理器"""
        self.registry = ProjectRegistry()
        self.config_manager = ConfigManager()

    def analyze_project(self, project_name_or_id: str, incremental: bool = False,
                       include_pattern: Optional[str] = None, 
                       exclude_pattern: Optional[str] = None,
                       threads: Optional[int] = None, verbose: bool = False) -> int:
        """
        分析项目代码
        
        Args:
            project_name_or_id: 项目名称或ID
            incremental: 是否增量分析
            include_pattern: 包含的文件模式
            exclude_pattern: 排除的文件模式
            threads: 并行线程数
            verbose: 是否显示详细日志
            
        Returns:
            int: 退出码（0表示成功）
        """
        try:
            # 查找项目
            project_info = self.registry.find_project(project_name_or_id)
            if not project_info:
                print(f"❌ 错误: 项目 '{project_name_or_id}' 不存在")
                print("💡 使用 'code-learner project list' 查看所有项目")
                return 1
            
            project_path = project_info['path']
            project_name = project_info['name']
            project_id = project_info['id']
            
            print(f"🚀 开始分析项目...")
            print(f"   名称: {project_name}")
            print(f"   ID: {project_id}")
            print(f"   路径: {project_path}")
            
            if incremental:
                print("   模式: 增量分析")
            else:
                print("   模式: 完整分析")
            
            # 设置输出目录
            output_dir = f"data/{project_name}_analysis"
            os.makedirs(output_dir, exist_ok=True)

            # 1. 核心代码分析
            print("\n📊 第1步: 核心代码分析 (代码解析、向量化)")
            success = analyze_code(
                project_path=project_path,
                output_dir=output_dir,
                incremental=incremental,
                include_pattern=include_pattern,
                exclude_pattern=exclude_pattern,
                threads=threads,
                verbose=verbose,
                project_id=project_id  # 传递项目ID以确保数据隔离
            )
            
            if not success:
                print("❌ 核心代码分析失败。后续步骤将跳过。")
                return 1

            # 2. 连接数据库
            print("\n📊 第2步: 连接数据库以生成报告")
            try:
                config = self.config_manager.get_config()
                graph_store = Neo4jGraphStore(
                    uri=config.database.neo4j_uri,
                    user=config.database.neo4j_user,
                    password=config.database.neo4j_password,
                    project_id=project_id
                )
                if not graph_store.connect():
                    print("⚠️ 无法连接到Neo4j，跳过报告生成")
                    return 0 # 分析本身是成功的
            except Exception as e:
                print(f"⚠️ 连接数据库时出错，跳过报告生成: {e}")
                return 0

            # 3. 生成依赖图
            self._generate_dependency_report(graph_store, output_dir, verbose)

            # 4. 生成调用图
            self._generate_call_graph_reports(graph_store, output_dir, verbose)
            
            graph_store.close()
            
            print(f"\n✅ 项目 '{project_name}' 分析和报告生成完成!")
            print(f"   所有报告已保存到: {output_dir}")
            print("\n📝 下一步:")
            print(f"   1. 开始查询: code-learner query --project {project_name}")
            print(f"   2. 查看调用图: code-learner call-graph --project {project_name} <function_name>")
            return 0
                
        except Exception as e:
            logger.error(f"分析项目失败: {e}")
            print(f"❌ 分析项目时发生意外错误: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return 1

    def _generate_dependency_report(self, graph_store: Neo4jGraphStore, output_dir: str, verbose: bool):
        """生成依赖关系报告"""
        print("\n📊 第3步: 生成依赖关系图")
        try:
            dep_service = ServiceFactory.get_dependency_service(graph_store)
            mermaid_graph = dep_service.generate_dependency_graph(output_format="mermaid", scope="module")
            
            report_path = Path(output_dir) / "dependency_graph.md"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("# 项目模块依赖图\n\n")
                f.write(mermaid_graph)
            
            print(f"   ✅ 依赖图已保存到: {report_path}")
        except Exception as e:
            print(f"   ⚠️  生成依赖图失败: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    def _generate_call_graph_reports(self, graph_store: Neo4jGraphStore, output_dir: str, verbose: bool, top_n: int = 5):
        """为引用最多的N个函数生成调用图"""
        print(f"\n📊 第4步: 为引用最多的 {top_n} 个函数生成调用图")
        try:
            call_graph_service = ServiceFactory.get_call_graph_service(graph_store)
            
            # 查找引用最多的函数
            top_functions = call_graph_service.get_top_called_functions(top_n)

            if not top_functions:
                print("   ⚠️ 未找到可供分析的函数。")
                return

            print(f"   🔍 找到顶级函数: {', '.join([f['name'] for f in top_functions])}")

            for func in top_functions:
                func_name = func['name']
                try:
                    graph_data = call_graph_service.build_graph(func_name, depth=3)
                    
                    report_path = Path(output_dir) / f"call_graph_{func_name}.md"
                    
                    call_graph_service.export_to_file(graph_data, report_path, "mermaid")
                    print(f"   ✅ 函数 '{func_name}' 的调用图已保存到: {report_path}")
                except Exception as e_inner:
                    print(f"   ⚠️ 生成函数 '{func_name}' 的调用图失败: {e_inner}")

        except Exception as e:
            print(f"   ⚠️  生成调用图报告失败: {e}")
            if verbose:
                import traceback
                traceback.print_exc() 