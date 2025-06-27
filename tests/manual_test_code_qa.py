#!/usr/bin/env python
"""
代码问答功能手动测试脚本

用于验证代码问答功能的手动测试脚本，包括：
- 函数上下文检索
- 文件上下文检索
- 向量检索
"""
import os
import sys
import argparse
from dotenv import load_dotenv
import logging

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.code_learner.llm.code_qa_service import CodeQAService
from src.code_learner.llm.service_factory import ServiceFactory
from src.code_learner.config.config_manager import ConfigManager


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_function_query(service, function_name):
    """测试函数查询"""
    print(f"\n=== 测试函数查询: {function_name} ===")
    
    # 构建上下文
    context = {"focus_function": function_name}
    
    # 询问问题
    question = f"函数 {function_name} 的功能是什么？它的实现有什么特点？"
    print(f"问题: {question}")
    
    # 获取回答
    try:
        answer = service.ask_question(question, context)
        print(f"回答:\n{answer}")
    except Exception as e:
        print(f"错误: {e}")


def test_file_query(service, file_path):
    """测试文件查询"""
    print(f"\n=== 测试文件查询: {file_path} ===")
    
    # 构建上下文
    context = {"focus_file": file_path}
    
    # 询问问题
    question = f"文件 {file_path} 的主要功能是什么？它包含哪些关键函数？"
    print(f"问题: {question}")
    
    # 获取回答
    try:
        answer = service.ask_question(question, context)
        print(f"回答:\n{answer}")
    except Exception as e:
        print(f"错误: {e}")


def test_general_query(service, project_path):
    """测试一般查询"""
    print(f"\n=== 测试一般查询 ===")
    
    # 构建上下文
    context = {"project_path": project_path}
    
    # 询问问题
    question = "这个项目的主要功能是什么？"
    print(f"问题: {question}")
    
    # 获取回答
    try:
        answer = service.ask_question(question, context)
        print(f"回答:\n{answer}")
    except Exception as e:
        print(f"错误: {e}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="代码问答功能手动测试脚本")
    parser.add_argument("--function", help="要查询的函数名")
    parser.add_argument("--file", help="要查询的文件路径")
    parser.add_argument("--project", help="项目路径")
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    
    # 加载环境变量
    load_dotenv()
    
    # 创建服务
    config_manager = ConfigManager()
    service_factory = ServiceFactory()
    service = CodeQAService(service_factory)
    
    print("=== 代码问答功能手动测试 ===")
    
    # 测试函数查询
    if args.function:
        test_function_query(service, args.function)
    
    # 测试文件查询
    if args.file:
        test_file_query(service, args.file)
    
    # 测试一般查询
    if args.project:
        test_general_query(service, args.project)
    
    # 如果没有提供任何参数，显示帮助信息
    if not (args.function or args.file or args.project):
        parser.print_help()


if __name__ == "__main__":
    main() 