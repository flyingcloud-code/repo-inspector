"""
代码嵌入批量处理器

负责将代码块转换为嵌入向量并存储到Chroma数据库。
实现批量处理和增量更新机制。
"""
import os
import time
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import hashlib
import json

from .code_chunker import CodeChunk, CodeChunker
from .embedding_engine import JinaEmbeddingEngine
from .vector_store import ChromaVectorStore
from ..core.data_models import EmbeddingData
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CodeEmbedder:
    """代码嵌入器
    
    负责将预处理好的代码块(CodeChunk)列表转换为嵌入向量并存储到向量数据库。
    """
    
    def __init__(self, 
                embedding_engine: JinaEmbeddingEngine,
                vector_store: ChromaVectorStore,
                batch_size: int = 50
                ):
        """初始化代码嵌入器
        
        Args:
            embedding_engine: 嵌入引擎实例
            vector_store: 向量存储实例
            batch_size: 批处理大小
        """
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store
        self.batch_size = batch_size
        
        logger.info(f"初始化代码嵌入器: batch_size={self.batch_size}")
    
    def embed_code_chunks(self, chunks: List[CodeChunk], collection_name: str) -> bool:
        """处理代码块
        
        Args:
            chunks: 代码块列表
            collection_name: 要使用的集合名称
            
        Returns:
            bool: 处理是否成功
        """
        if not chunks:
            logger.warning("没有要处理的代码块")
            return True
        
        logger.info(f"▶️ 开始处理 {len(chunks)} 个代码块，存入集合 '{collection_name}'...")
        
        try:
            # 确保集合存在
            self.vector_store.create_collection(collection_name)

            # 批量处理
            num_batches = (len(chunks) + self.batch_size - 1) // self.batch_size
            logger.info(f"将创建 {num_batches} 个批次")

            for i in range(0, len(chunks), self.batch_size):
                batch_chunks = chunks[i:i+self.batch_size]
                batch_idx = i // self.batch_size
                logger.info(f"▶️ 开始处理批次 {batch_idx+1}/{num_batches}，包含 {len(batch_chunks)} 个块")
                
                # 提取批次内容
                batch_content = [chunk.content for chunk in batch_chunks]
                
                # 生成嵌入向量
                batch_embeddings = self.embedding_engine.encode_batch(batch_content)
                
                if len(batch_embeddings) != len(batch_chunks):
                    logger.error(f"嵌入结果数量与块数量不匹配: {len(batch_embeddings)} vs {len(batch_chunks)}")
                    return False
                
                # 准备要存储的数据
                embeddings_to_store = []
                for chunk, vector in zip(batch_chunks, batch_embeddings):
                    # 清理元数据，确保没有None值
                    clean_metadata = self._clean_metadata({
                        "source": chunk.file_path or "",
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "function_name": chunk.function_name or "",
                        "embedding_time": time.time(),
                        "strategy": chunk.metadata.get("strategy", "unknown"),
                        "type": chunk.metadata.get("type", "unknown"),
                        "name": chunk.metadata.get("name", "")
                    })
                    
                    embedding_data = EmbeddingData(
                        id=chunk.id,
                        text=chunk.content,
                        embedding=vector,
                        metadata=clean_metadata
                    )
                    embeddings_to_store.append(embedding_data)
                
                logger.info(f"批次 {batch_idx+1}/{num_batches} 的 {len(embeddings_to_store)} 个嵌入向量生成完毕")

                # 存储嵌入
                if embeddings_to_store:
                    logger.info(f"存储批次 {batch_idx+1}/{num_batches} 的 {len(embeddings_to_store)} 个嵌入")
                    
                    # 格式化数据为ChromaVectorStore期望的格式
                    texts = [emb.text for emb in embeddings_to_store]
                    vectors = [emb.embedding for emb in embeddings_to_store]
                    metadatas = [emb.metadata for emb in embeddings_to_store]
                    
                    success = self.vector_store.add_embeddings(texts, vectors, metadatas, collection_name)
                    if not success:
                        logger.error(f"批次 {batch_idx+1}/{num_batches} 嵌入存储失败")
                        return False
                    
                    logger.info(f"批次 {batch_idx+1}/{num_batches} 嵌入存储成功: {len(embeddings_to_store)} 个")
            
            logger.info(f"✅ 所有 {len(chunks)} 个代码块处理完成")
            return True
            
        except Exception as e:
            logger.error(f"代码块处理失败: {e}", exc_info=True)
            return False

    def process_file(self, file_path: str, force_update: bool = False) -> bool:
        """处理单个文件
        
        Args:
            file_path: 文件路径
            force_update: 是否强制更新
            
        Returns:
            bool: 处理是否成功
        """
        logger.info(f"▶️ 开始处理文件: {file_path}")
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return False
        
        try:
            # 检查文件是否已处理且未更改
            if not force_update and self._is_file_processed(file_path):
                logger.info(f"文件已处理且未更改，跳过: {file_path}")
                return True
            
            # 分块
            logger.info(f"分块文件: {file_path}")
            chunks = self.chunker.chunk_file(file_path)
            if not chunks:
                logger.warning(f"文件分块为空: {file_path}")
                return False
            
            logger.info(f"文件分块完成: {file_path}, 共{len(chunks)}个块")
            
            # 批量处理
            success = self._process_chunks(chunks)
            
            if success:
                logger.info(f"✅ 文件处理成功: {file_path}")
            else:
                logger.error(f"❌ 文件处理失败: {file_path}")
                
            return success
            
        except Exception as e:
            logger.error(f"文件处理失败: {file_path}, 错误: {e}")
            return False
    
    def process_directory(self, directory: str, 
                         extensions: List[str] = ['.c', '.h', '.cpp', '.hpp', '.cc', '.py'],
                         exclude_patterns: List[str] = ['test', 'build', 'dist', 'node_modules', '.git'],
                         force_update: bool = False) -> bool:
        """处理目录
        
        Args:
            directory: 目录路径
            extensions: 文件扩展名列表
            exclude_patterns: 排除模式列表
            force_update: 是否强制更新
            
        Returns:
            bool: 处理是否成功
        """
        if not os.path.isdir(directory):
            logger.warning(f"目录不存在: {directory}")
            return False
        
        try:
            # 收集文件
            files = []
            for root, dirs, filenames in os.walk(directory):
                # 排除目录
                dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
                
                # 收集文件
                for filename in filenames:
                    if any(filename.endswith(ext) for ext in extensions):
                        file_path = os.path.join(root, filename)
                        files.append(file_path)
            
            logger.info(f"目录扫描完成: {directory}, 共找到{len(files)}个文件")
            
            # 批量处理文件
            success_count = 0
            for file_path in files:
                if self.process_file(file_path, force_update):
                    success_count += 1
            
            logger.info(f"目录处理完成: {directory}, 成功处理{success_count}/{len(files)}个文件")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"目录处理失败: {directory}, 错误: {e}")
            return False
    
    def _process_chunks(self, chunks: List[CodeChunk]) -> bool:
        """处理代码块
        
        Args:
            chunks: 代码块列表
            
        Returns:
            bool: 处理是否成功
        """
        if not chunks:
            return True
        
        logger.info(f"▶️ 开始处理 {len(chunks)} 个代码块...")
        
        try:
            # 批量处理
            num_batches = (len(chunks) + self.batch_size - 1) // self.batch_size
            logger.info(f"将创建 {num_batches} 个批次")

            for i in range(0, len(chunks), self.batch_size):
                batch = chunks[i:i+self.batch_size]
                batch_idx = i // self.batch_size
                logger.info(f"▶️ 开始处理批次 {batch_idx+1}/{num_batches}，包含 {len(batch)} 个块")
                
                # 生成嵌入
                embeddings = []
                
                for chunk in batch:
                    # 生成嵌入向量
                    embedding_vector = self.embedding_engine.encode_text(chunk.content)
                    
                    # 创建嵌入数据
                    embedding_data = EmbeddingData(
                        id=chunk.id,
                        text=chunk.content,
                        embedding=embedding_vector,
                        metadata={
                            **chunk.metadata,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "file_path": chunk.file_path,
                            "function_name": chunk.function_name,
                            "embedding_time": time.time()
                        }
                    )
                    
                    embeddings.append(embedding_data)
                
                logger.info(f"批次 {batch_idx+1}/{num_batches} 的 {len(embeddings)} 个嵌入向量生成完毕")

                # 存储嵌入
                if embeddings:
                    logger.info(f"存储批次 {batch_idx+1}/{num_batches} 的 {len(embeddings)} 个嵌入")
                    
                    # 格式化数据为ChromaVectorStore期望的格式
                    texts = [emb.text for emb in embeddings]
                    vectors = [emb.embedding for emb in embeddings]
                    metadatas = [emb.metadata for emb in embeddings]
                    
                    success = self.vector_store.add_embeddings(texts, vectors, metadatas)
                    if not success:
                        logger.error(f"批次{batch_idx+1}/{num_batches}嵌入存储失败")
                        return False
                    
                    logger.info(f"批次{batch_idx+1}/{num_batches}嵌入存储成功: {len(embeddings)}个")
            
            logger.info(f"✅ 所有 {len(chunks)} 个代码块处理完成")

            # 更新处理记录
            self._update_processed_files(chunks)
            
            return True
            
        except Exception as e:
            logger.error(f"代码块处理失败: {e}", exc_info=True)
            return False
    
    def _is_file_processed(self, file_path: str) -> bool:
        """检查文件是否已处理且未更改
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否已处理且未更改
        """
        try:
            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_path)
            
            # 检查缓存
            cache_file = self.cache_dir / "processed_files.json"
            if not cache_file.exists():
                return False
            
            # 读取缓存
            with open(cache_file, 'r') as f:
                processed_files = json.load(f)
            
            # 检查文件是否在缓存中且哈希值匹配
            return file_path in processed_files and processed_files[file_path] == file_hash
            
        except Exception as e:
            logger.error(f"检查文件处理状态失败: {file_path}, 错误: {e}")
            return False
    
    def _update_processed_files(self, chunks: List[CodeChunk]) -> None:
        """更新处理记录
        
        Args:
            chunks: 代码块列表
        """
        try:
            # 获取文件路径
            file_paths = set()
            for chunk in chunks:
                if chunk.file_path and os.path.exists(chunk.file_path):
                    file_paths.add(chunk.file_path)
            
            # 读取现有缓存
            cache_file = self.cache_dir / "processed_files.json"
            processed_files = {}
            
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    processed_files = json.load(f)
            
            # 更新缓存
            for file_path in file_paths:
                processed_files[file_path] = self._calculate_file_hash(file_path)
            
            # 写入缓存
            with open(cache_file, 'w') as f:
                json.dump(processed_files, f, indent=2)
            
        except Exception as e:
            logger.error(f"更新处理记录失败: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件哈希
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件哈希值
        """
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            return file_hash
        except Exception as e:
            logger.error(f"计算文件哈希失败: {file_path}, 错误: {e}")
            return ""
    
    def clear_cache(self) -> bool:
        """清除缓存
        
        Returns:
            bool: 是否成功
        """
        try:
            cache_file = self.cache_dir / "processed_files.json"
            if cache_file.exists():
                os.remove(cache_file)
            return True
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """清理元数据，确保没有None值
        
        Args:
            metadata: 原始元数据
            
        Returns:
            Dict[str, Any]: 清理后的元数据
        """
        clean_data = {}
        for key, value in metadata.items():
            if value is None:
                clean_data[key] = ""  # 将None转换为空字符串
            elif isinstance(value, (str, int, float, bool)):
                clean_data[key] = value  # 保留基本类型
            else:
                clean_data[key] = str(value)  # 将其他类型转换为字符串
        return clean_data 