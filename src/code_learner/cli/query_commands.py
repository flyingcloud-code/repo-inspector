"""
查询命令模块

实现智能问答功能，支持直接查询和交互式REPL两种模式
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

from ..project.project_registry import ProjectRegistry
from ..llm.code_qa_service import CodeQAService

logger = logging.getLogger(__name__)


class QueryCommands:
    """查询命令处理器"""
    
    def __init__(self):
        """初始化查询命令处理器"""
        self.registry = ProjectRegistry()
    
    def query_project(self, project_name_or_id: str, direct_query: Optional[str] = None,
                     history_file: Optional[str] = None, focus_function: Optional[str] = None,
                     focus_file: Optional[str] = None) -> int:
        """
        查询项目代码
        
        Args:
            project_name_or_id: 项目名称或ID
            direct_query: 直接执行的查询（不进入交互模式）
            history_file: 历史记录文件路径
            focus_function: 聚焦的函数
            focus_file: 聚焦的文件
            
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
            
            # 初始化问答服务
            qa_service = CodeQAService()
            
            # 构建焦点信息
            focus_info = ""
            if focus_function:
                focus_info = f" (聚焦函数: {focus_function})"
            elif focus_file:
                focus_info = f" (聚焦文件: {focus_file})"
            
            # 如果提供了直接查询，执行单次查询
            if direct_query:
                return self._execute_direct_query(
                    qa_service, project_info, direct_query, 
                    history_file, focus_function, focus_file
                )
            else:
                # 启动交互式会话
                return self._start_interactive_session(
                    qa_service, project_info, history_file, 
                    focus_function, focus_file
                )
                
        except Exception as e:
            logger.error(f"查询项目失败: {e}")
            print(f"❌ 查询项目时出错: {e}")
            return 1
    
    def _execute_direct_query(self, qa_service: CodeQAService, project_info: dict,
                             query: str, history_file: Optional[str] = None,
                             focus_function: Optional[str] = None,
                             focus_file: Optional[str] = None) -> int:
        """
        执行直接查询模式
        
        Args:
            qa_service: 问答服务
            project_info: 项目信息
            query: 查询问题
            history_file: 历史记录文件
            focus_function: 聚焦函数
            focus_file: 聚焦文件
            
        Returns:
            int: 退出码
        """
        try:
            project_id = project_info['id']
            project_name = project_info['name']
            
            print(f"📝 查询项目: {project_name} ({project_id})")
            
            if focus_function:
                print(f"🎯 聚焦函数: {focus_function}")
            elif focus_file:
                print(f"🎯 聚焦文件: {focus_file}")
            
            print(f"❓ 问题: {query}")
            print("🤔 处理中...")
            print()
            
            # 执行查询
            result = qa_service.ask_question(query, project_id)
            
            if "error" in result:
                print(f"❌ 查询失败: {result['error']}")
                return 1
            
            # 显示答案
            answer = result.get("answer", "未获得回答")
            print("💡 回答:")
            print(answer)
            print()
            
            # 保存到历史记录
            if history_file:
                self._save_to_history(history_file, query, answer)
                print(f"📝 已保存到历史记录: {history_file}")
            
            return 0
            
        except Exception as e:
            logger.error(f"执行直接查询失败: {e}")
            print(f"❌ 执行查询时出错: {e}")
            return 1
    
    def _start_interactive_session(self, qa_service: CodeQAService, project_info: dict,
                                  history_file: Optional[str] = None,
                                  focus_function: Optional[str] = None,
                                  focus_file: Optional[str] = None) -> int:
        """
        启动交互式查询会话
        
        Args:
            qa_service: 问答服务
            project_info: 项目信息
            history_file: 历史记录文件
            focus_function: 聚焦函数
            focus_file: 聚焦文件
            
        Returns:
            int: 退出码
        """
        try:
            project_id = project_info['id']
            project_name = project_info['name']
            project_path = project_info['path']
            
            # 加载历史记录
            history = []
            if history_file and os.path.exists(history_file):
                try:
                    with open(history_file, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except Exception as e:
                    logger.warning(f"无法加载历史记录: {e}")
            
            # 显示会话信息
            print(f"🚀 进入交互式查询模式")
            print(f"   项目: {project_name} ({project_id})")
            print(f"   路径: {project_path}")
            
            if focus_function:
                print(f"   聚焦函数: {focus_function}")
            elif focus_file:
                print(f"   聚焦文件: {focus_file}")
            
            if history_file:
                print(f"   历史记录: {history_file}")
            
            print()
            print("💡 输入 'exit' 或 'quit' 退出，输入 'help' 获取帮助")
            print("=" * 50)
            print()
            
            # 交互循环
            while True:
                try:
                    # 获取用户输入
                    question = input("❓ > ").strip()
                    
                    if not question:
                        continue
                    
                    # 处理特殊命令
                    if question.lower() in ['exit', 'quit', 'q']:
                        print("👋 再见!")
                        break
                    elif question.lower() in ['help', 'h']:
                        self._print_help()
                        continue
                    elif question.lower() == 'history':
                        self._print_history(history)
                        continue
                    elif question.lower() == 'clear':
                        os.system('clear' if os.name == 'posix' else 'cls')
                        continue
                    
                    print("🤔 处理中...")
                    
                    # 执行查询
                    result = qa_service.ask_question(question, project_id)
                    
                    if "error" in result:
                        print(f"❌ 查询失败: {result['error']}")
                        print()
                        continue
                    
                    # 显示答案
                    answer = result.get("answer", "未获得回答")
                    print("💡 回答:")
                    print(answer)
                    print()
                    print("-" * 50)
                    print()
                    
                    # 保存到历史记录
                    history.append({
                        "question": question,
                        "answer": answer,
                        "timestamp": self._get_timestamp()
                    })
                    
                except KeyboardInterrupt:
                    print("\n👋 会话被中断，再见!")
                    break
                except EOFError:
                    print("\n👋 再见!")
                    break
                except Exception as e:
                    logger.error(f"处理查询失败: {e}")
                    print(f"❌ 处理查询时出错: {e}")
                    print()
            
            # 保存历史记录
            if history_file and history:
                try:
                    os.makedirs(os.path.dirname(history_file), exist_ok=True)
                    with open(history_file, "w", encoding="utf-8") as f:
                        json.dump(history, f, ensure_ascii=False, indent=2)
                    print(f"📝 历史记录已保存到: {history_file}")
                except Exception as e:
                    logger.warning(f"保存历史记录失败: {e}")
            
            return 0
            
        except Exception as e:
            logger.error(f"交互式会话失败: {e}")
            print(f"❌ 交互式会话出错: {e}")
            return 1
    
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