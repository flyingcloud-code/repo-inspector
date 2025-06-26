#!/usr/bin/env python3
"""
依赖关系分析命令行工具

用于分析C项目的文件和模块依赖关系，支持多种输出格式
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..llm.service_factory import ServiceFactory
from ..utils.logger import get_logger


def parse_args(args: List[str]) -> argparse.Namespace:
    """解析命令行参数
    
    Args:
        args: 命令行参数列表
        
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="依赖关系分析工具 - 分析C项目的文件和模块依赖关系"
    )
    
    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # 分析项目命令
    analyze_parser = subparsers.add_parser("analyze", help="分析项目依赖关系")
    analyze_parser.add_argument("project_path", help="项目路径")
    
    # 分析文件命令
    file_parser = subparsers.add_parser("file", help="分析单个文件的依赖关系")
    file_parser.add_argument("file_path", help="文件路径")
    
    # 生成依赖图命令
    graph_parser = subparsers.add_parser("graph", help="生成依赖关系图")
    graph_parser.add_argument("--format", "-f", choices=["mermaid", "json", "dot", "ascii"], 
                            default="ascii", help="输出格式")
    graph_parser.add_argument("--scope", "-s", choices=["file", "module"], 
                            default="module", help="依赖范围")
    graph_parser.add_argument("--focus", "-i", help="聚焦的文件或模块")
    graph_parser.add_argument("--output", "-o", help="输出文件路径")
    
    # 检测循环依赖命令
    cycle_parser = subparsers.add_parser("cycle", help="检测循环依赖")
    
    # 通用选项
    for p in [analyze_parser, file_parser, graph_parser, cycle_parser]:
        p.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")
    
    return parser.parse_args(args)


def main(args: List[str] = None) -> int:
    """主函数
    
    Args:
        args: 命令行参数，默认为None（使用sys.argv）
        
    Returns:
        int: 退出码
    """
    if args is None:
        args = sys.argv[1:]
    
    parsed_args = parse_args(args)
    
    # 设置日志级别
    logger = get_logger(__name__)
    if parsed_args.verbose:
        logger.setLevel("DEBUG")
    else:
        logger.setLevel("INFO")
    
    # 获取依赖服务
    dependency_service = ServiceFactory.get_dependency_service()
    
    try:
        if parsed_args.command == "analyze":
            # 分析项目
            project_path = Path(parsed_args.project_path)
            if not project_path.exists() or not project_path.is_dir():
                logger.error(f"项目路径不存在: {project_path}")
                return 1
            
            logger.info(f"开始分析项目: {project_path}")
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
            
            return 0
        
        elif parsed_args.command == "file":
            # 分析单个文件
            file_path = Path(parsed_args.file_path)
            if not file_path.exists() or not file_path.is_file():
                logger.error(f"文件不存在: {file_path}")
                return 1
            
            logger.info(f"开始分析文件: {file_path}")
            dependencies = dependency_service.analyze_file(file_path)
            
            # 输出依赖信息
            print(f"\n文件 {file_path.name} 的依赖关系:")
            for i, dep in enumerate(dependencies):
                dep_type = "系统" if dep.is_system else "项目"
                print(f"{i+1}. {dep.target_file} ({dep_type}头文件, 行 {dep.line_number})")
            
            return 0
        
        elif parsed_args.command == "graph":
            # 生成依赖图
            graph = dependency_service.generate_dependency_graph(
                output_format=parsed_args.format,
                scope=parsed_args.scope,
                focus_item=parsed_args.focus
            )
            
            # 输出依赖图
            if parsed_args.output:
                with open(parsed_args.output, "w") as f:
                    f.write(graph)
                print(f"依赖图已保存到: {parsed_args.output}")
            else:
                print(graph)
            
            return 0
        
        elif parsed_args.command == "cycle":
            # 检测循环依赖
            cycles = dependency_service.get_circular_dependencies()
            
            if not cycles:
                print("没有检测到循环依赖")
            else:
                print(f"检测到 {len(cycles)} 个循环依赖:")
                for i, cycle in enumerate(cycles):
                    print(f"循环 {i+1}: {' -> '.join(cycle)}")
            
            return 0
        
        else:
            # 未指定命令，显示帮助
            parse_args(["--help"])
            return 1
    
    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}")
        if parsed_args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 