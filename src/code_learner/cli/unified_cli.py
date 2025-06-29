#!/usr/bin/env python3
"""
统一命令行工具

将代码分析、调用图和依赖分析功能整合到一个简单的命令行界面中
"""

import argparse
import sys
import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib

from ..config.config_manager import ConfigManager
from ..storage.neo4j_store import Neo4jGraphStore
from ..llm.service_factory import ServiceFactory
from ..core.exceptions import ServiceError, StorageError
from . import code_analyzer_cli
from . import call_graph_cli
from . import dependency_cli

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedCLI:
    """统一命令行界面"""
    
    def __init__(self):
        """初始化CLI"""
        self.config = ConfigManager()
        self.graph_store = None
        self.project_id = None
        
    def connect_to_database(self, project_id: str = None) -> bool:
        """连接到Neo4j数据库
        
        Args:
            project_id: 可选的项目ID
            
        Returns:
            bool: 连接是否成功
        """
        try:
            config = self.config.get_config()
            self.graph_store = Neo4jGraphStore(
                uri=config.database.neo4j_uri,
                user=config.database.neo4j_user,
                password=config.database.neo4j_password,
                project_id=project_id
            )
            
            success = self.graph_store.connect()
            
            if success:
                self.project_id = self.graph_store.project_id
                return True
            else:
                print("❌ 连接Neo4j数据库失败")
                return False
                
        except Exception as e:
            print(f"❌ 数据库连接错误: {e}")
            return False
    
    def run_full_analysis(self, project_path: str, output_dir: str = None, 
                         include_pattern: str = None, exclude_pattern: str = None,
                         threads: int = None, verbose: bool = False) -> bool:
        """运行完整分析
        
        执行代码分析、调用图分析和依赖分析
        
        Args:
            project_path: 项目路径
            output_dir: 输出目录
            include_pattern: 包含的文件模式
            exclude_pattern: 排除的文件模式
            threads: 并行处理线程数
            verbose: 是否显示详细日志
            
        Returns:
            bool: 分析是否成功
        """
        start_time = time.time()
        
        # 1. 设置输出目录
        if not output_dir:
            output_dir = f"data/{Path(project_path).name}_analysis"
        
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"🚀 开始对项目 {project_path} 进行全面分析")
        print(f"📂 分析结果将保存到 {output_dir}")
        
        # 2. 代码分析
        print("\n📊 第1步: 代码分析")
        analyze_args = ["analyze", project_path]
        
        if output_dir:
            analyze_args.extend(["--output-dir", output_dir])
        if include_pattern:
            analyze_args.extend(["--include", include_pattern])
        if exclude_pattern:
            analyze_args.extend(["--exclude", exclude_pattern])
        if threads:
            analyze_args.extend(["--threads", str(threads)])
        if verbose:
            analyze_args.append("--verbose")
            
        try:
            # 直接调用代码分析函数，而不是通过命令行参数
            from ..cli.code_analyzer_cli import analyze_code
            analyze_code(
                project_path=project_path,
                output_dir=output_dir,
                incremental=False,
                include_pattern=include_pattern,
                exclude_pattern=exclude_pattern,
                threads=threads,
                verbose=verbose
            )
        except Exception as e:
            print(f"❌ 代码分析失败: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return False
        
        # 获取生成的项目ID
        project_id = None
        analysis_info_path = Path(output_dir) / ".analysis" / "info.json"
        if analysis_info_path.exists():
            import json
            try:
                with open(analysis_info_path, "r") as f:
                    info = json.load(f)
                    project_id = info.get("project_id")
            except Exception as e:
                if verbose:
                    print(f"⚠️ 无法读取项目ID: {e}")
                # 生成项目ID
                project_id = "auto_" + hashlib.md5(project_path.encode()).hexdigest()[:8]
        else:
            # 生成项目ID
            project_id = "auto_" + hashlib.md5(project_path.encode()).hexdigest()[:8]
            
        print(f"📌 项目ID: {project_id}")
        
        # 连接到数据库
        if not self.connect_to_database(project_id):
            print("⚠️ 无法连接到数据库，跳过调用图和依赖分析")
            return False
            
        # 3. 依赖分析
        print("\n📊 第2步: 依赖分析")
        try:
            # 分析项目依赖
            from ..llm.dependency_service import DependencyService
            # 使用已连接的图存储
            dependency_service = DependencyService(graph_store=self.graph_store)
            
            print("分析项目依赖关系...")
            project_deps = dependency_service.analyze_project(project_path)
            
            # 输出统计信息
            stats = project_deps.get_stats()
            print("\n依赖关系统计:")
            print(f"文件依赖数: {stats['file_dependencies_count']}")
            print(f"模块依赖数: {stats['module_dependencies_count']}")
            print(f"循环依赖数: {stats['circular_dependencies_count']}")
            print(f"系统头文件数: {stats['system_headers_count']}")
            print(f"项目头文件数: {stats['project_headers_count']}")
            print(f"模块化评分: {stats['modularity_score']:.2f}/1.00")
            
            # 如果有循环依赖，输出警告
            if stats['circular_dependencies_count'] > 0:
                print("\n警告: 检测到循环依赖!")
                for i, cycle in enumerate(project_deps.circular_dependencies):
                    print(f"循环 {i+1}: {' -> '.join(cycle)}")
            
            # 生成依赖图
            graph_output = os.path.join(output_dir, "dependency_graph.md")
            print(f"\n生成依赖图: {graph_output}")
            
            graph = dependency_service.generate_dependency_graph(
                output_format="mermaid",
                scope="module"
            )
            
            with open(graph_output, "w") as f:
                f.write(graph)
            
            print(f"依赖图已保存到: {graph_output}")
            
        except Exception as e:
            print(f"⚠️ 依赖分析部分失败: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
        
        # 4. 调用图分析
        print("\n📊 第3步: 调用图分析")
        try:
            # 查找主要函数
            from ..llm.call_graph_service import CallGraphService
            call_graph_service = CallGraphService(self.graph_store)
            
            with self.graph_store.driver.session() as session:
                query = """
                MATCH (f:Function)
                WHERE f.project_id = $project_id
                RETURN f.name as name, count(*) as ref_count
                ORDER BY ref_count DESC
                LIMIT 5
                """
                result = session.run(query, project_id=project_id)
                
                top_functions = [record["name"] for record in result]
                
                if top_functions:
                    print(f"找到顶级函数: {', '.join(top_functions)}")
                    
                    # 为顶级函数生成调用图
                    for func in top_functions:
                        graph_output = os.path.join(output_dir, f"call_graph_{func}.md")
                        print(f"\n生成函数 {func} 的调用图: {graph_output}")
                        
                        # 构建图谱数据
                        graph_data = call_graph_service.build_graph(func, depth=3)
                        
                        # 导出到文件
                        call_graph_service.export_to_file(
                            graph_data, 
                            Path(graph_output), 
                            format_type="mermaid"
                        )
                        
                        print(f"调用图已保存到: {graph_output}")
                else:
                    print("⚠️ 未找到任何函数")
                    
        except Exception as e:
            print(f"⚠️ 调用图分析部分失败: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
        
        # 5. 总结
        elapsed_time = time.time() - start_time
        print(f"\n✅ 分析完成! 总耗时: {elapsed_time:.2f}秒")
        print(f"📂 分析结果保存在: {output_dir}")
        print(f"📌 项目ID: {project_id} (用于后续查询)")
        
        return True
    
    def run(self, args: argparse.Namespace) -> int:
        """运行CLI命令
        
        Args:
            args: 命令行参数
            
        Returns:
            int: 退出代码
        """
        try:
            # 设置日志级别
            if args.verbose:
                logging.basicConfig(level=logging.DEBUG)
            
            # 运行完整分析
            success = self.run_full_analysis(
                project_path=args.project_path,
                output_dir=args.output_dir,
                include_pattern=args.include,
                exclude_pattern=args.exclude,
                threads=args.threads,
                verbose=args.verbose
            )
            
            return 0 if success else 1
            
        except KeyboardInterrupt:
            print("\n⚠️ 用户取消操作")
            return 130
        except Exception as e:
            logger.exception("UnifiedCLI中发生意外错误")
            print(f"❌ 意外错误: {e}")
            return 1
        finally:
            if self.graph_store:
                self.graph_store.close()


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器
    
    Returns:
        argparse.ArgumentParser: 参数解析器
    """
    parser = argparse.ArgumentParser(
        prog='code-learner-all',
        description='统一代码分析工具 - 一键执行代码分析、调用图和依赖分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本分析
  code-learner-all /path/to/project
  
  # 指定输出目录
  code-learner-all /path/to/project --output-dir ./my_analysis
  
  # 过滤特定文件
  code-learner-all /path/to/project --include "*.c,*.h" --exclude "test/*"
  
  # 使用多线程加速
  code-learner-all /path/to/project --threads 8
        """
    )
    
    parser.add_argument(
        'project_path',
        help='项目路径'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        help='输出目录'
    )
    
    parser.add_argument(
        '--include',
        help='包含的文件模式 (例如: "*.c,*.h")'
    )
    
    parser.add_argument(
        '--exclude',
        help='排除的文件模式 (例如: "test/*")'
    )
    
    parser.add_argument(
        '--threads', '-t',
        type=int,
        help='并行处理线程数'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细日志'
    )
    
    return parser


def main(argv: Optional[list] = None) -> int:
    """主函数
    
    Args:
        argv: 命令行参数列表
        
    Returns:
        int: 退出代码
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # 运行CLI
    cli = UnifiedCLI()
    return cli.run(args)


if __name__ == '__main__':
    sys.exit(main()) 