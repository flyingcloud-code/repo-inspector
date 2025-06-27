#!/usr/bin/env python3
"""
测试tree-sitter分块策略

这个脚本用于测试基于tree-sitter的代码分块策略，不依赖Neo4j。
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.code_learner.llm.code_chunker import CodeChunker, ChunkingStrategy
from src.code_learner.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试tree-sitter分块策略")
    parser.add_argument("--file", type=str, help="要分析的文件路径")
    parser.add_argument("--dir", type=str, help="要分析的目录路径")
    parser.add_argument("--chunk-size", type=int, default=512, help="块大小（字符数）")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="块重叠（字符数）")
    parser.add_argument("--verbose", action="store_true", help="输出详细信息")
    
    args = parser.parse_args()
    
    if not args.file and not args.dir:
        parser.error("必须提供--file或--dir参数")
    
    chunker = CodeChunker(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    
    if not chunker.ts_initialized:
        logger.error("tree-sitter未初始化，无法进行测试")
        return
    
    if args.file:
        test_file(chunker, args.file, args.verbose)
    
    if args.dir:
        test_directory(chunker, args.dir, args.verbose)


def test_file(chunker: CodeChunker, file_path: str, verbose: bool = False):
    """测试单个文件的分块"""
    logger.info(f"测试文件: {file_path}")
    
    # 使用tree-sitter分块
    chunks = chunker.chunk_file_by_tree_sitter(file_path)
    
    logger.info(f"生成了 {len(chunks)} 个tree-sitter语义块")
    
    # 统计各类型块的数量
    type_counts = {}
    for chunk in chunks:
        chunk_type = chunk.metadata.get("type", "unknown")
        if chunk_type not in type_counts:
            type_counts[chunk_type] = 0
        type_counts[chunk_type] += 1
    
    logger.info(f"块类型统计: {type_counts}")
    
    # 输出详细信息
    if verbose:
        for i, chunk in enumerate(chunks):
            chunk_type = chunk.metadata.get("type", "unknown")
            chunk_name = chunk.metadata.get("name", "")
            logger.info(f"块 {i+1}/{len(chunks)}: 类型={chunk_type}, 名称={chunk_name}, 行={chunk.start_line}-{chunk.end_line}")
            if chunk_type == "function":
                logger.info(f"函数内容: {chunk.content[:100]}...")
            elif chunk_type == "header_comment":
                logger.info(f"注释内容: {chunk.content}")


def test_directory(chunker: CodeChunker, dir_path: str, verbose: bool = False):
    """测试目录中所有文件的分块"""
    logger.info(f"测试目录: {dir_path}")
    
    # 收集所有C文件
    c_files = []
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith((".c", ".h", ".cpp", ".hpp")):
                c_files.append(os.path.join(root, file))
    
    logger.info(f"找到 {len(c_files)} 个C/C++文件")
    
    # 统计信息
    total_chunks = 0
    all_type_counts = {}
    
    # 处理每个文件
    for file_path in c_files:
        logger.info(f"处理文件: {file_path}")
        
        # 使用tree-sitter分块
        chunks = chunker.chunk_file_by_tree_sitter(file_path)
        
        total_chunks += len(chunks)
        
        # 统计各类型块的数量
        for chunk in chunks:
            chunk_type = chunk.metadata.get("type", "unknown")
            if chunk_type not in all_type_counts:
                all_type_counts[chunk_type] = 0
            all_type_counts[chunk_type] += 1
    
    logger.info(f"总共生成了 {total_chunks} 个tree-sitter语义块")
    logger.info(f"块类型统计: {all_type_counts}")


if __name__ == "__main__":
    main() 