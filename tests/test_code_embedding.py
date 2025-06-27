#!/usr/bin/env python
"""
代码嵌入和向量检索测试脚本

用于测试代码嵌入和向量检索功能：
- 代码分块
- 嵌入生成
- 向量存储
- 相似度搜索
"""
import os
import sys
import argparse
import time
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.code_learner.llm.code_chunker import CodeChunker
from src.code_learner.llm.code_embedder import CodeEmbedder
from src.code_learner.llm.embedding_engine import JinaEmbeddingEngine
from src.code_learner.llm.vector_store import ChromaVectorStore
from src.code_learner.utils.logger import get_logger
from src.code_learner.config.config_manager import ConfigManager

logger = get_logger(__name__)


def test_code_chunking(file_path: str, chunk_size: int = 50, chunk_overlap: int = 10) -> None:
    """测试代码分块
    
    Args:
        file_path: 文件路径
        chunk_size: 块大小
        chunk_overlap: 块重叠
    """
    print(f"\n=== 测试代码分块: {file_path} ===")
    
    # 创建分块器
    chunker = CodeChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # 分块
    chunks = chunker.chunk_file(file_path)
    
    # 输出结果
    print(f"分块结果: {len(chunks)}个块")
    
    for i, chunk in enumerate(chunks[:3]):  # 只显示前3个
        print(f"\n块 {i+1}/{len(chunks)}:")
        print(f"ID: {chunk.id}")
        print(f"行范围: {chunk.start_line}-{chunk.end_line}")
        if chunk.function_name:
            print(f"函数名: {chunk.function_name}")
        print(f"内容 (前100字符): {chunk.content[:100]}...")
    
    if len(chunks) > 3:
        print(f"\n... 省略 {len(chunks) - 3} 个块 ...")


def clean_collection(collection_name: str) -> None:
    """清理集合
    
    Args:
        collection_name: 集合名称
    """
    print(f"\n=== 清理集合: {collection_name} ===")
    
    try:
        # 创建向量存储
        vector_store = ChromaVectorStore()
        vector_store.delete_collection(collection_name)
        print("清理完成")
    except Exception as e:
        print(f"清理失败: {e}")


def test_code_embedding(file_path: str, chunk_size: int = 50, chunk_overlap: int = 10, batch_size: int = 10) -> None:
    """测试代码嵌入
    
    Args:
        file_path: 文件路径
        chunk_size: 块大小
        chunk_overlap: 块重叠
        batch_size: 批处理大小
    """
    print(f"\n=== 测试代码嵌入: {file_path} ===")
    
    # 创建分块器
    chunker = CodeChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # 创建嵌入器
    embedder = CodeEmbedder(
        chunker=chunker,
        batch_size=batch_size,
        collection_name="test_embeddings"
    )
    
    # 处理文件
    start_time = time.time()
    success = embedder.process_file(file_path, force_update=True)
    elapsed = time.time() - start_time
    
    # 输出结果
    if success:
        print(f"嵌入成功，耗时: {elapsed:.2f}秒")
    else:
        print(f"嵌入失败，耗时: {elapsed:.2f}秒")


def test_vector_search(query: str, top_k: int = 3) -> None:
    """测试向量搜索
    
    Args:
        query: 查询文本
        top_k: 返回结果数量
    """
    print(f"\n=== 测试向量搜索: '{query}' ===")
    
    # 创建嵌入引擎
    embedding_engine = JinaEmbeddingEngine()
    if not embedding_engine.model:
        embedding_engine.load_model("jinaai/jina-embeddings-v2-base-code")
    
    # 创建向量存储
    vector_store = ChromaVectorStore()
    
    # 生成查询向量
    start_time = time.time()
    query_vector = embedding_engine.encode_text(query)
    
    # 搜索
    results = vector_store.search_similar(
        query_vector=query_vector,
        top_k=top_k,
        collection_name="test_embeddings"
    )
    elapsed = time.time() - start_time
    
    # 输出结果
    print(f"搜索完成，耗时: {elapsed:.2f}秒，找到 {len(results)} 个结果")
    
    for i, result in enumerate(results):
        print(f"\n结果 {i+1}/{len(results)}:")
        metadata = result.get('metadata', {})
        print(f"相似度: {result.get('similarity', 0.0):.4f}")
        print(f"文件: {metadata.get('file_path', 'unknown')}")
        print(f"行范围: {metadata.get('start_line', 0)}-{metadata.get('end_line', 0)}")
        if metadata.get('function_name'):
            print(f"函数名: {metadata.get('function_name')}")
        print(f"内容 (前100字符): {result['document'][:100]}...")


def main() -> int:
    """主函数
    
    Returns:
        int: 退出代码
    """
    parser = argparse.ArgumentParser(description="测试代码嵌入和向量检索功能")
    parser.add_argument("--file", help="要处理的文件路径")
    parser.add_argument("--chunk", action="store_true", help="测试代码分块")
    parser.add_argument("--embed", action="store_true", help="测试代码嵌入")
    parser.add_argument("--search", help="测试向量搜索，提供查询文本")
    parser.add_argument("--clean", action="store_true", help="清理测试集合")
    parser.add_argument("--top-k", type=int, default=3, help="向量搜索返回结果数量")
    parser.add_argument("--chunk-size", type=int, default=50, help="代码块大小")
    parser.add_argument("--chunk-overlap", type=int, default=10, help="代码块重叠")
    parser.add_argument("--batch-size", type=int, default=10, help="批处理大小")
    
    args = parser.parse_args()
    
    # 检查参数
    if args.chunk or args.embed:
        if not args.file:
            print("错误: 测试代码分块或嵌入时必须指定文件路径")
            return 1
    
    if args.clean:
        clean_collection("test_embeddings")

    # 执行测试
    if args.chunk:
        test_code_chunking(args.file, args.chunk_size, args.chunk_overlap)
    
    if args.embed:
        test_code_embedding(args.file, args.chunk_size, args.chunk_overlap, args.batch_size)
    
    if args.search:
        test_vector_search(args.search, args.top_k)
    
    # 如果没有指定任何操作，显示帮助信息
    if not (args.chunk or args.embed or args.search):
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 