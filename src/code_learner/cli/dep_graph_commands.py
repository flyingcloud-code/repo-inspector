"""
依赖图命令模块

实现模块依赖图生成功能，整合现有的dependency_cli功能
"""

import os
import logging
from typing import Optional

from ..project.project_registry import ProjectRegistry
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class DepGraphCommands:
    """依赖图命令处理器"""
    
    def __init__(self):
        """初始化依赖图命令处理器"""
        self.registry = ProjectRegistry()
        self.config_manager = ConfigManager()
    
    def generate_dependency_graph(self, project_name_or_id: str, scope: str = "module",
                                 output_format: str = "ascii", 
                                 output_file: Optional[str] = None) -> int:
        """
        生成依赖图
        
        Args:
            project_name_or_id: 项目名称或ID
            scope: 依赖范围（module或file）
            output_format: 输出格式
            output_file: 输出文件路径
            
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
            
            project_name = project_info['name']
            project_id = project_info['id']
            project_path = project_info['path']
            
            print(f"🔗 生成依赖图...")
            print(f"   项目: {project_name} ({project_id})")
            print(f"   路径: {project_path}")
            print(f"   范围: {scope}")
            print(f"   格式: {output_format}")
            
            if output_file:
                print(f"   输出: {output_file}")
            
            # 创建依赖服务
            from ..llm.service_factory import ServiceFactory
            graph_store = ServiceFactory.get_graph_store(project_id=project_id)
            parser = ServiceFactory.get_parser()
            
            from ..llm.dependency_service import DependencyService
            dependency_service = DependencyService(parser=parser, graph_store=graph_store)
            
            # 生成依赖图
            try:
                print("🎨 生成依赖图...")
                dependency_graph = dependency_service.generate_dependency_graph(
                    output_format=output_format,
                    scope=scope
                )
                
                if not dependency_graph:
                    print("❌ 无法生成依赖图")
                    return 1
                
                # 输出结果
                if output_file:
                    # 保存到文件
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(dependency_graph)
                    print(f"✅ 依赖图已保存到: {output_file}")
                else:
                    # 输出到控制台
                    print()
                    print("📊 依赖图:")
                    print("=" * 50)
                    print(dependency_graph)
                    print("=" * 50)
                
                return 0
                
            except Exception as e:
                logger.error(f"生成依赖图失败: {e}")
                print(f"❌ 生成依赖图失败: {e}")
                return 1
                
        except Exception as e:
            logger.error(f"依赖图命令失败: {e}")
            print(f"❌ 依赖图命令出错: {e}")
            return 1 