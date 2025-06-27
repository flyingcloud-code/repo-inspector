"""
Code Embedding Command

命令行工具，用于生成代码嵌入并将其存储到向量数据库中。
支持三种策略：
1. semantic: 从Neo4j数据库中提取语义单元（函数、结构体）进行嵌入。
2. fixed_size: 将文件按固定大小分块进行嵌入。
3. tree_sitter: 使用tree-sitter直接进行语义分块，不依赖Neo4j。
"""

import argparse
import os
import sys
from typing import List

# 调整路径以允许从项目根目录导入
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from code_learner.llm.code_chunker import CodeChunker, CodeChunk, ChunkingStrategy
from code_learner.llm.code_embedder import CodeEmbedder
from code_learner.llm.embedding_engine import JinaEmbeddingEngine
from code_learner.llm.vector_store import ChromaVectorStore
from code_learner.storage.neo4j_store import Neo4jGraphStore
from code_learner.utils.logger import get_logger

logger = get_logger(__name__)

# 默认嵌入模型名称
DEFAULT_EMBEDDING_MODEL = "jinaai/jina-embeddings-v2-base-code"


def main():
    """主函数：解析参数并执行嵌入过程"""
    parser = argparse.ArgumentParser(description="生成代码嵌入并存储到向量数据库。")
    parser.add_argument(
        '--strategy',
        type=str,
        choices=['semantic', 'fixed_size', 'tree_sitter'],
        default='tree_sitter',
        help="嵌入策略：'semantic'（从Neo4j获取）、'fixed_size'（按大小分块）或'tree_sitter'（使用tree-sitter进行语义分块，不依赖Neo4j）。"
    )
    parser.add_argument(
        '--dir',
        type=str,
        help="要处理的目录路径（用于 'fixed_size' 和 'tree_sitter' 策略）。"
    )
    parser.add_argument(
        '--collection',
        type=str,
        default='code_embeddings',
        help="ChromaDB中的集合名称。"
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=512,
        help="块大小（字符数，仅用于 'fixed_size' 策略）。"
    )
    parser.add_argument(
        '--chunk-overlap',
        type=int,
        default=100,
        help="块重叠（字符数，仅用于 'fixed_size' 策略）。"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help="嵌入处理的批处理大小。"
    )
    parser.add_argument(
        '--file-extensions',
        type=str,
        default='.c,.h,.cpp,.hpp,.cc,.py',
        help="要处理的文件扩展名（逗号分隔，用于 'fixed_size' 和 'tree_sitter' 策略）。"
    )
    parser.add_argument(
        '--model',
        type=str,
        default=DEFAULT_EMBEDDING_MODEL,
        help="嵌入模型名称。"
    )

    args = parser.parse_args()

    logger.info(f"🚀 开始执行嵌入任务，策略: {args.strategy}")

    chunks = []
    if args.strategy == 'semantic':
        chunks = get_semantic_chunks()
    elif args.strategy == 'fixed_size':
        if not args.dir:
            logger.error("使用 'fixed_size' 策略时必须提供 '--dir' 参数。")
            sys.exit(1)
        chunks = get_fixed_size_chunks(args.dir, args.chunk_size, args.chunk_overlap, args.file_extensions)
    elif args.strategy == 'tree_sitter':
        if not args.dir:
            logger.error("使用 'tree_sitter' 策略时必须提供 '--dir' 参数。")
            sys.exit(1)
        chunks = get_tree_sitter_chunks(args.dir, args.chunk_size, args.chunk_overlap, args.file_extensions)

    if not chunks:
        logger.warning("未能生成任何代码块，任务终止。")
        return

    embed_chunks(chunks, args.collection, args.batch_size, args.model)


def get_semantic_chunks() -> List[CodeChunk]:
    """从Neo4j获取语义块"""
    logger.info("🚚 从Neo4j数据库获取语义代码单元...")
    try:
        store = Neo4jGraphStore()
        store.connect()
        code_units = store.get_all_code_units()
        store.close()

        chunks = []
        for unit in code_units:
            chunk_id = f"{unit['file_path']}_{unit['name']}"
            chunks.append(CodeChunk(
                id=chunk_id,
                content=unit['code'],
                metadata={
                    "source": unit['file_path'],
                    "strategy": "semantic",
                    "node_type": unit['node_type'],
                    "function_name": unit['name'] if unit['node_type'] == 'Function' else None
                },
                start_line=unit['start_line'],
                end_line=unit['end_line'],
                file_path=unit['file_path'],
                function_name=unit['name'] if unit['node_type'] == 'Function' else None
            ))
        logger.info(f"✅ 从Neo4j成功转换 {len(chunks)} 个语义块。")
        return chunks
    except Exception as e:
        logger.error(f"❌ 从Neo4j获取语义块失败: {e}", exc_info=True)
        return []


def get_fixed_size_chunks(directory: str, chunk_size: int, chunk_overlap: int, file_extensions: str) -> List[CodeChunk]:
    """获取固定大小的块"""
    logger.info(f"📁 按固定大小扫描目录: {directory}")
    chunker = CodeChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = []
    
    # 解析文件扩展名
    extensions = [ext.strip() for ext in file_extensions.split(',')]
    
    for root, _, files in os.walk(directory):
        for file in files:
            # 过滤文件扩展名
            if not any(file.endswith(ext) for ext in extensions):
                continue
                
            file_path = os.path.join(root, file)
            chunks = chunker.chunk_file_by_size(file_path)
            all_chunks.extend(chunks)
            
    logger.info(f"✅ 从目录 {directory} 成功生成 {len(all_chunks)} 个固定大小的块。")
    return all_chunks


def get_tree_sitter_chunks(directory: str, chunk_size: int, chunk_overlap: int, file_extensions: str) -> List[CodeChunk]:
    """使用tree-sitter获取语义块"""
    logger.info(f"🌳 使用tree-sitter扫描目录: {directory}")
    chunker = CodeChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = []
    
    # 解析文件扩展名
    extensions = [ext.strip() for ext in file_extensions.split(',')]
    
    for root, _, files in os.walk(directory):
        for file in files:
            # 过滤文件扩展名
            if not any(file.endswith(ext) for ext in extensions):
                continue
                
            file_path = os.path.join(root, file)
            chunks = chunker.chunk_file_by_tree_sitter(file_path)
            all_chunks.extend(chunks)
            
    logger.info(f"✅ 从目录 {directory} 成功生成 {len(all_chunks)} 个tree-sitter语义块。")
    return all_chunks


def embed_chunks(chunks: List[CodeChunk], collection_name: str, batch_size: int, model_name: str):
    """嵌入代码块"""
    logger.info(f"🧠 开始嵌入 {len(chunks)} 个代码块...")
    try:
        embedding_engine = JinaEmbeddingEngine()
        embedding_engine.load_model(model_name)
        
        vector_store = ChromaVectorStore()
        
        embedder = CodeEmbedder(
            embedding_engine=embedding_engine,
            vector_store=vector_store,
            batch_size=batch_size
        )
        
        success = embedder.embed_code_chunks(chunks, collection_name)
        if success:
            logger.info("🎉 嵌入任务成功完成！")
        else:
            logger.error("❌ 嵌入任务失败。")
    except Exception as e:
        logger.error(f"❌ 嵌入过程中发生严重错误: {e}", exc_info=True)


if __name__ == '__main__':
    main() 