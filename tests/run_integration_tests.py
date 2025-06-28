#!/usr/bin/env python
"""
运行所有集成测试的脚本

使用方法：
    python tests/run_integration_tests.py
"""
import os
import sys
import unittest
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))


def run_tests(test_pattern=None, verbose=False):
    """运行集成测试"""
    # 设置测试目录
    test_dir = os.path.join(root_dir, "tests", "integration")
    
    # 创建测试加载器
    loader = unittest.TestLoader()
    
    # 根据模式加载测试
    if test_pattern:
        # 加载匹配模式的测试
        pattern = f"test_{test_pattern}.py"
        suite = loader.discover(test_dir, pattern=pattern)
    else:
        # 加载所有测试
        suite = loader.discover(test_dir)
    
    # 创建测试运行器
    runner = unittest.TextTestRunner(verbosity=2 if verbose else 1)
    
    # 运行测试
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行集成测试")
    parser.add_argument(
        "-p", "--pattern", 
        help="测试文件名模式（不包括 'test_' 前缀和 '.py' 后缀）"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="显示详细输出"
    )
    
    args = parser.parse_args()
    
    # 运行测试
    success = run_tests(args.pattern, args.verbose)
    
    # 根据测试结果设置退出代码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 