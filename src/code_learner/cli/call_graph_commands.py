"""
调用图命令模块

实现函数调用图生成功能，整合现有的call_graph_cli功能
"""

import os
import logging
from typing import Optional

from ..project.project_registry import ProjectRegistry
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class CallGraphCommands:
    """调用图命令处理器"""
    
    def __init__(self):
        """初始化调用图命令处理器"""
        self.registry = ProjectRegistry()
        self.config_manager = ConfigManager()
    
    def generate_call_graph(self, project_name_or_id: str, function_name: str,
                           depth: int = 3, output_format: str = "ascii",
                           output_file: Optional[str] = None) -> int:
        """
        生成函数调用图
        
        Args:
            project_name_or_id: 项目名称或ID
            function_name: 根函数名称
            depth: 调用深度
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
            
            print(f"🔗 生成调用图...")
            print(f"   项目: {project_name} ({project_id})")
            print(f"   函数: {function_name}")
            print(f"   深度: {depth}")
            print(f"   格式: {output_format}")
            
            if output_file:
                print(f"   输出: {output_file}")
            
            # 创建调用图服务
            from ..llm.service_factory import ServiceFactory
            graph_store = ServiceFactory.get_graph_store(project_id=project_id)
            call_graph_service = ServiceFactory.get_call_graph_service()
            call_graph_service.graph_store = graph_store
            
            # 生成调用图
            try:
                graph_data = call_graph_service.build_graph(
                    root=function_name,
                    depth=depth
                )
                
                if not graph_data or not graph_data.get('nodes'):
                    print(f"❌ 未找到函数 '{function_name}' 或无法生成调用图")
                    return 1
                
                # 转换为指定格式
                if output_format == "mermaid":
                    call_graph = call_graph_service.to_mermaid(graph_data)
                elif output_format == "json":
                    call_graph = call_graph_service.to_json(graph_data)
                elif output_format == "ascii":
                    call_graph = call_graph_service.print_ascii_tree(graph_data)
                else:
                    print(f"❌ 不支持的输出格式: {output_format}")
                    return 1
                
                # 输出结果
                if output_file:
                    # 保存到文件
                    os.makedirs(os.path.dirname(output_file), exist_ok=True)
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(call_graph)
                    print(f"✅ 调用图已保存到: {output_file}")
                else:
                    # 输出到控制台
                    print()
                    print("📊 调用图:")
                    print("=" * 50)
                    print(call_graph)
                    print("=" * 50)
                
                return 0
                
            except Exception as e:
                logger.error(f"生成调用图失败: {e}")
                print(f"❌ 生成调用图失败: {e}")
                return 1
                
        except Exception as e:
            logger.error(f"调用图命令失败: {e}")
            print(f"❌ 调用图命令出错: {e}")
            return 1 