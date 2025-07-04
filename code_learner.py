#!/usr/bin/env python3
"""
C语言智能代码分析调试工具 - 单一文件CLI入口
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from typing import Optional

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# 调整Python路径以找到src模块
# This makes the script runnable from the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.code_learner.cli.project_commands import ProjectCommands
from src.code_learner.cli.analyze_commands import AnalyzeCommands
from src.code_learner.cli.query_commands import QueryCommands
from src.code_learner.cli.call_graph_commands import CallGraphCommands
from src.code_learner.cli.dep_graph_commands import DepGraphCommands
from src.code_learner.cli.status_commands import StatusCommands


class MainCLI:
    """主命令行界面"""
    
    def __init__(self):
        """初始化主CLI"""
        pass
    
    def create_parser(self) -> argparse.ArgumentParser:
        """创建主命令解析器"""
        parser = argparse.ArgumentParser(
            prog='code_learner.py',
            description='C语言智能代码分析调试工具',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  # 项目管理
  python code_learner.py project create /path/to/project --name my-project
  python code_learner.py project list
  python code_learner.py project delete my-project
  
  # 代码分析
  python code_learner.py analyze --project my-project
  
  # 智能问答
  python code_learner.py query --project my-project
  python code_learner.py query --project my-project --query "sbi_init函数的作用是什么？"
  
  # 调用图分析
  python code_learner.py call-graph --project my-project main
  
  # 依赖图分析
  python code_learner.py dep-graph --project my-project
  
  # 系统状态检查
  python code_learner.py status
"""
        )
        
        # 创建子命令解析器
        subparsers = parser.add_subparsers(
            dest='command',
            help='可用命令',
            metavar='COMMAND',
            required=True
        )
        
        # 项目管理子命令
        self._add_project_commands(subparsers)
        
        # 分析命令
        self._add_analyze_command(subparsers)
        
        # 查询命令
        self._add_query_command(subparsers)
        
        # 调用图命令
        self._add_call_graph_command(subparsers)
        
        # 依赖图命令
        self._add_dep_graph_command(subparsers)
        
        # 状态检查命令
        self._add_status_command(subparsers)
        
        return parser
    
    def _add_project_commands(self, subparsers):
        """添加项目管理命令"""
        project_parser = subparsers.add_parser(
            'project',
            help='项目管理',
            description='管理代码分析项目的生命周期'
        )
        
        project_subparsers = project_parser.add_subparsers(
            dest='project_command',
            help='项目操作',
            metavar='OPERATION',
            required=True
        )
        
        # project create
        create_parser = project_subparsers.add_parser(
            'create',
            help='创建新项目',
            description='将代码库注册为新项目'
        )
        create_parser.add_argument(
            'path',
            help='项目路径'
        )
        create_parser.add_argument(
            '--name', '-n',
            required=True,
            help='项目短名称'
        )
        
        # project list
        project_subparsers.add_parser(
            'list',
            help='列出所有项目',
            description='显示所有已注册的项目'
        )
        
        # project delete
        delete_parser = project_subparsers.add_parser(
            'delete',
            help='删除项目',
            description='从系统中彻底删除项目及其所有数据'
        )
        delete_parser.add_argument(
            'name_or_id',
            help='项目名称或ID'
        )
        delete_parser.add_argument(
            '--force', '-f',
            action='store_true',
            help='跳过确认提示'
        )
    
    def _add_analyze_command(self, subparsers):
        """添加分析命令"""
        analyze_parser = subparsers.add_parser(
            'analyze',
            help='分析项目',
            description='对已注册的项目执行完整的代码分析'
        )
        analyze_parser.add_argument(
            '--project', '-p',
            required=True,
            help='项目名称或ID'
        )
        analyze_parser.add_argument(
            '--incremental', '-i',
            action='store_true',
            help='增量分析，只处理变更文件'
        )
        analyze_parser.add_argument(
            '--include',
            help='包含的文件模式，逗号分隔（默认: "*.c,*.h"）'
        )
        analyze_parser.add_argument(
            '--exclude',
            help='排除的文件模式，逗号分隔'
        )
        analyze_parser.add_argument(
            '--threads', '-t',
            type=int,
            help='并行处理线程数'
        )
        analyze_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='显示详细日志'
        )
    
    def _add_query_command(self, subparsers):
        """添加查询命令"""
        query_parser = subparsers.add_parser(
            'query',
            help='智能问答',
            description='与代码库进行智能对话'
        )
        query_parser.add_argument(
            '--project', '-p',
            required=True,
            help='项目名称或ID'
        )
        query_parser.add_argument(
            '--query', '-q',
            help='直接执行的查询（不进入交互模式）'
        )
        query_parser.add_argument(
            '--history', '-H',
            help='历史记录文件路径'
        )
        query_parser.add_argument(
            '--function', '-f',
            help='聚焦于特定函数'
        )
        query_parser.add_argument(
            '--file',
            help='聚焦于特定文件'
        )
        query_parser.add_argument(
            '--verbose-rag',
            action='store_true',
            help='为RAG检索步骤启用详细输出'
        )
    
    def _add_call_graph_command(self, subparsers):
        """添加调用图命令"""
        call_graph_parser = subparsers.add_parser(
            'call-graph',
            help='调用图分析',
            description='生成函数调用关系图'
        )
        call_graph_parser.add_argument(
            '--project', '-p',
            required=True,
            help='项目名称或ID'
        )
        call_graph_parser.add_argument(
            'function',
            help='根函数名称'
        )
        call_graph_parser.add_argument(
            '--depth', '-d',
            type=int,
            default=3,
            help='调用深度（默认: 3）'
        )
        call_graph_parser.add_argument(
            '--format', '-f',
            choices=['ascii', 'mermaid', 'json', 'dot'],
            default='ascii',
            help='输出格式（默认: ascii）'
        )
        call_graph_parser.add_argument(
            '--output', '-o',
            help='输出文件路径'
        )
    
    def _add_dep_graph_command(self, subparsers):
        """添加依赖图命令"""
        dep_graph_parser = subparsers.add_parser(
            'dep-graph',
            help='依赖图分析',
            description='生成模块依赖关系图'
        )
        dep_graph_parser.add_argument(
            '--project', '-p',
            required=True,
            help='项目名称或ID'
        )
        dep_graph_parser.add_argument(
            '--scope',
            choices=['module', 'file'],
            default='module',
            help='依赖范围（默认: module）'
        )
        dep_graph_parser.add_argument(
            '--format', '-f',
            choices=['ascii', 'mermaid', 'json', 'dot'],
            default='ascii',
            help='输出格式（默认: ascii）'
        )
        dep_graph_parser.add_argument(
            '--output', '-o',
            help='输出文件路径'
        )
    
    def _add_status_command(self, subparsers):
        """添加状态检查命令"""
        status_parser = subparsers.add_parser(
            'status',
            help='系统状态检查',
            description='检查所有后端服务的健康状况'
        )
        status_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='显示详细信息'
        )
    
    def run(self, args: argparse.Namespace) -> int:
        """执行命令"""
        try:
            # 根据命令分发到相应的处理器
            if args.command == 'project':
                return self._handle_project_command(args)
            elif args.command == 'analyze':
                return self._handle_analyze_command(args)
            elif args.command == 'query':
                return self._handle_query_command(args)
            elif args.command == 'call-graph':
                return self._handle_call_graph_command(args)
            elif args.command == 'dep-graph':
                return self._handle_dep_graph_command(args)
            elif args.command == 'status':
                return self._handle_status_command(args)
            else:
                logger.error(f"未知命令: {args.command}")
                return 1
                
        except KeyboardInterrupt:
            logger.info("操作被用户中断")
            return 130
        except Exception as e:
            logger.error(f"执行命令时出错: {e}")
            if hasattr(args, 'verbose') and args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def _handle_project_command(self, args: argparse.Namespace) -> int:
        """处理项目管理命令"""
        cmd = ProjectCommands()
        if args.project_command == 'create':
            return cmd.create_project(args)
        elif args.project_command == 'list':
            return cmd.list_projects(args)
        elif args.project_command == 'delete':
            return cmd.delete_project(args)
        return 1
    
    def _handle_analyze_command(self, args: argparse.Namespace) -> int:
        """处理分析命令"""
        return AnalyzeCommands().run_analysis(args)
    
    def _handle_query_command(self, args: argparse.Namespace) -> int:
        """处理查询命令"""
        return QueryCommands().run_query(args)
    
    def _handle_call_graph_command(self, args: argparse.Namespace) -> int:
        """处理调用图命令"""
        call_graph_commands = CallGraphCommands()
        return call_graph_commands.generate_call_graph(
            project_name_or_id=args.project,
            function_name=args.function,
            depth=args.depth,
            output_format=args.format,
            output_file=args.output
        )
    
    def _handle_dep_graph_command(self, args: argparse.Namespace) -> int:
        """处理依赖图命令"""
        dep_graph_commands = DepGraphCommands()
        return dep_graph_commands.generate_dependency_graph(
            project_name_or_id=args.project,
            scope=args.scope,
            output_format=args.format,
            output_file=args.output
        )
    
    def _handle_status_command(self, args: argparse.Namespace) -> int:
        """处理状态检查命令"""
        status_commands = StatusCommands()
        return status_commands.check_status(verbose=args.verbose)


def main(argv: Optional[list] = None) -> int:
    """主入口函数"""
    # 确保我们在项目根目录运行
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    cli = MainCLI()
    parser = cli.create_parser()
    
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        parser.print_help()
        return 1
    
    args = parser.parse_args(argv)
    return cli.run(args)

if __name__ == '__main__':
    sys.exit(main()) 