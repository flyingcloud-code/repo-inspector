"""
查询命令模块

实现智能问答功能，支持直接查询和交互式REPL两种模式
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional
import argparse

from ..project.project_registry import ProjectRegistry
from ..llm.code_qa_service import CodeQAService

logger = logging.getLogger(__name__)


class QueryCommands:
    """查询命令处理器"""
    
    def __init__(self):
        """初始化查询命令处理器"""
        self.registry = ProjectRegistry()
    
    def run_query(self, args: argparse.Namespace) -> int:
        """执行查询"""
        project_name_or_id = args.project
        query = args.query

        project_info = self.registry.find_project(project_name_or_id)
        if not project_info:
            print(f"❌ 错误: 项目 '{project_name_or_id}' 未找到。")
            return 1

        project_id = project_info['id']
        project_name = project_info['name']
        
        # 获取 verbose_rag 标志，如果不存在则默认为 False
        verbose_rag = getattr(args, 'verbose_rag', False)
        
        # 使用项目ID和verbose标志正确初始化服务
        qa_service = CodeQAService(project_id=project_id, verbose_rag=verbose_rag)

        if query:
            return self._run_single_query(qa_service, project_name, project_id, query)
        else:
            return self._run_interactive_query(qa_service, project_name, project_id)

    def _run_single_query(self, qa_service: CodeQAService, project_name: str, project_id: str, query: str) -> int:
        """运行单个查询"""
        print(f"📝 查询项目: {project_name} ({project_id})")
        print(f"❓ 问题: {query}")
        print("🤔 处理中...\n")

        result = qa_service.ask_question(query)

        if "error" in result:
            print(f"❌ 查询失败: {result['error']}")
            return 1
        
        print(f"💡 回答:\n{result['answer']}")
        return 0

    def _run_interactive_query(self, qa_service: CodeQAService, project_name: str, project_id: str) -> int:
        """运行交互式查询"""
        print("🚀 进入交互式查询模式")
        print(f"   项目: {project_name} ({project_id})")
        
        project_path = self.registry.find_project(project_id)['path']
        print(f"   路径: {project_path}")

        print("\n💡 输入 'exit' 或 'quit' 退出，输入 'help' 获取帮助")
        print("=" * 50)

        while True:
            try:
                user_query = input("\n❓ > ").strip()
                if not user_query:
                    continue
                if user_query.lower() in ['exit', 'quit']:
                    break
                if user_query.lower() == 'help':
                    print("这是一个交互式查询会话。直接输入您关于代码的问题即可。")
                    continue

                print("🤔 处理中...")
                result = qa_service.ask_question(user_query)

                if "error" in result:
                    print(f"❌ 查询失败: {result['error']}")
                else:
                    print(f"💡 回答:\n{result['answer']}")
                
                print("-" * 50)

            except KeyboardInterrupt:
                print("\n操作已取消。")
                break
            except Exception as e:
                logger.error(f"交互式查询出错: {e}", exc_info=True)
                print(f"❌ 发生意外错误: {e}")

        return 0
    
    def _print_help(self):
        """打印帮助信息"""
        help_text = """
🆘 可用命令:
   exit, quit, q  - 退出会话
   help, h        - 显示此帮助
   history        - 显示查询历史
   clear          - 清空屏幕

💡 示例问题:
   - sbi_init函数的作用是什么？
   - 哪些函数调用了sbi_console_putc？
   - 文件lib/sbi/sbi_init.c中定义了哪些函数？
   - 项目中有哪些循环依赖？
   - 哪个模块依赖最多？
   - 文件A和文件B之间的依赖关系是什么？
   - what is sbi_system_suspend_set_device？ (支持英文)

🔍 查询技巧:
   - 可以询问函数的功能、参数、返回值
   - 可以查询调用关系和依赖关系
   - 可以分析代码逻辑和潜在问题
   - 支持中英文混合查询
"""
        print(help_text)
    
    def _print_history(self, history: list):
        """打印查询历史"""
        if not history:
            print("📝 暂无查询历史")
            return
        
        print(f"📝 查询历史 (最近 {min(len(history), 10)} 条):")
        print()
        
        # 显示最近的10条记录
        recent_history = history[-10:]
        
        for i, item in enumerate(recent_history, 1):
            question = item.get("question", "")
            timestamp = item.get("timestamp", "")
            
            print(f"{i:2d}. {question}")
            if timestamp:
                print(f"    时间: {timestamp}")
            print()
    
    def _save_to_history(self, history_file: str, question: str, answer: str):
        """保存查询到历史记录"""
        try:
            # 加载现有历史
            history = []
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            
            # 添加新记录
            history.append({
                "question": question,
                "answer": answer,
                "timestamp": self._get_timestamp()
            })
            
            # 保存历史
            os.makedirs(os.path.dirname(history_file), exist_ok=True)
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"保存历史记录失败: {e}")
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().isoformat() 