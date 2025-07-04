"""
项目管理命令模块

实现项目的创建、列表、删除等功能。
"""

import argparse
import logging
from .helpers import confirm_action
from ..project.project_registry import ProjectRegistry

logger = logging.getLogger(__name__)

class ProjectCommands:
    """项目管理命令处理器"""

    def __init__(self):
        """初始化项目命令处理器"""
        self.registry = ProjectRegistry()

    def create_project(self, args: argparse.Namespace) -> int:
        """创建新项目"""
        try:
            project = self.registry.create_project(args.path, args.name)
            print("✅ 项目创建成功!")
            print(f"   名称: {project['name']}")
            print(f"   ID:   {project['id']}")
            print(f"   路径: {project['path']}")
            print("\n📝 下一步: 运行分析")
            print(f"   python code_learner.py analyze --project {project['name']}")
            return 0
        except ValueError as e:
            print(f"❌ 错误: {e}")
            return 1
        except Exception as e:
            logger.error(f"创建项目时发生意外错误: {e}", exc_info=True)
            print(f"❌ 创建项目时发生意外错误: {e}")
            return 1

    def list_projects(self, args: argparse.Namespace) -> int:
        """列出所有项目"""
        try:
            projects = self.registry.list_projects()
            if not projects:
                print("ℹ️  系统中没有项目。")
                print("💡 使用 'code_learner.py project create' 来创建一个新项目。")
                return 0

            print("📚 已注册的项目:")
            print("-" * 60)
            print(f"{'项目名称':<20} {'项目ID':<15} {'项目路径'}")
            print("-" * 60)
            for project in projects:
                print(f"{project['name']:<20} {project['id']:<15} {project['path']}")
            print("-" * 60)
            return 0
        except Exception as e:
            logger.error(f"列出项目时发生意外错误: {e}", exc_info=True)
            print(f"❌ 列出项目时发生意外错误: {e}")
            return 1

    def delete_project(self, args: argparse.Namespace) -> int:
        """删除项目"""
        try:
            project = self.registry.find_project(args.name_or_id)
            if not project:
                print(f"❌ 错误: 项目 '{args.name_or_id}' 不存在。")
                return 1

            print(f"即将删除项目: {project['name']} ({project['id']})")
            print(f"路径: {project['path']}")
            
            if not args.force:
                if not confirm_action("这也会删除所有相关的分析数据，此操作不可逆。确定要继续吗?"):
                    print("操作已取消。")
                    return 1
            
            deleted_project = self.registry.delete_project(args.name_or_id)
            print(f"✅ 项目 '{deleted_project['name']}' 已成功删除。")
            return 0
        except ValueError as e:
            print(f"❌ 错误: {e}")
            return 1
        except Exception as e:
            logger.error(f"删除项目时发生意外错误: {e}", exc_info=True)
            print(f"❌ 删除项目时发生意外错误: {e}")
            return 1 