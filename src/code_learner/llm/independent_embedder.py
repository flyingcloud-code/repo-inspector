"""
独立的代码嵌入器

完全独立于Neo4j，直接从源代码文件生成嵌入
遵循KISS原则：简单、直接、有效
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import tiktoken

from ..storage.chroma_store import ChromaVectorStore
from ..llm.embedding_engine import JinaEmbeddingEngine
from ..config.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class IndependentCodeEmbedder:
    """独立代码嵌入器（简化版）
    
    核心功能：
    1. 直接从源代码文件生成嵌入
    2. 使用固定token大小分块（512 token，overlap 50）
    3. 完全独立于Neo4j
    4. 完善的metadata：file_name, module, start_line, end_line
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """初始化嵌入器
        
        Args:
            project_id: 项目ID，用于数据隔离
        """
        self.config = ConfigManager()
        
        # 初始化嵌入引擎
        self.embedding_engine = JinaEmbeddingEngine()
        self.embedding_engine.load_model("jinaai/jina-embeddings-v2-base-code")
        
        # 初始化向量存储
        self.vector_store = ChromaVectorStore(project_id=project_id)
        
        # 分块参数（按token计算）
        self.chunk_size_tokens = 512  # token数
        self.chunk_overlap_tokens = 50  # 重叠token数
        
        # 初始化tokenizer（使用tiktoken）
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4使用的编码
        except Exception as e:
            logger.warning(f"无法加载tiktoken，回退到字符计算: {e}")
            self.tokenizer = None
        
        logger.info(f"独立代码嵌入器初始化完成，项目ID: {project_id}")
        logger.info(f"分块配置: {self.chunk_size_tokens} tokens, overlap: {self.chunk_overlap_tokens} tokens")
    
    def embed_directory(self, directory_path: str, file_extensions: List[str] = None) -> bool:
        """嵌入整个目录的代码文件
        
        Args:
            directory_path: 目录路径
            file_extensions: 文件扩展名列表，默认为['.c', '.h']
            
        Returns:
            bool: 是否成功
        """
        if file_extensions is None:
            file_extensions = ['.c', '.h']
        
        directory = Path(directory_path)
        if not directory.exists():
            logger.error(f"目录不存在: {directory_path}")
            return False
        
        # 收集所有源代码文件
        source_files = []
        for ext in file_extensions:
            source_files.extend(directory.rglob(f"*{ext}"))
        
        if not source_files:
            logger.warning(f"在目录 {directory_path} 中没有找到源代码文件")
            return True
        
        logger.info(f"找到 {len(source_files)} 个源代码文件")
        
        # 处理每个文件
        total_chunks = 0
        for file_path in source_files:
            try:
                chunks = self._embed_file(file_path, directory)
                total_chunks += len(chunks)
                logger.info(f"文件 {file_path.name} 生成 {len(chunks)} 个代码块")
            except Exception as e:
                logger.error(f"处理文件 {file_path} 失败: {e}")
                continue
        
        logger.info(f"成功处理 {len(source_files)} 个文件，生成 {total_chunks} 个代码块")
        return True
    
    def _embed_file(self, file_path: Path, base_directory: Path) -> List[Dict[str, Any]]:
        """嵌入单个文件
        
        Args:
            file_path: 文件路径
            base_directory: 项目根目录
            
        Returns:
            List[Dict[str, Any]]: 生成的代码块列表
        """
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if not content.strip():
                logger.warning(f"文件 {file_path} 为空")
                return []
            
            # 计算相对路径作为模块名
            relative_path = file_path.relative_to(base_directory)
            module_name = str(relative_path.parent / relative_path.stem) if relative_path.parent != Path('.') else relative_path.stem
            
            # 按token分块
            chunks = self._chunk_content_by_tokens(content, str(file_path), file_path.name, module_name)
            
            if not chunks:
                return []
            
            # 生成嵌入
            texts = [chunk['content'] for chunk in chunks]
            embeddings = self.embedding_engine.encode_batch(texts)
            
            # 准备存储数据
            metadatas = [chunk['metadata'] for chunk in chunks]
            
            # 存储到Chroma
            success = self.vector_store.add_embeddings(
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                collection_name=None  # 使用默认集合名
            )
            
            if not success:
                logger.error(f"存储文件 {file_path} 的嵌入失败")
                return []
            
            return chunks
            
        except Exception as e:
            logger.error(f"嵌入文件 {file_path} 失败: {e}")
            return []
    
    def _chunk_content_by_tokens(self, content: str, file_path: str, file_name: str, module_name: str) -> List[Dict[str, Any]]:
        """按token数量将内容分块
        
        Args:
            content: 文件内容
            file_path: 完整文件路径
            file_name: 文件名
            module_name: 模块名
            
        Returns:
            List[Dict[str, Any]]: 代码块列表
        """
        chunks = []
        
        # 按行分割，便于计算行号
        lines = content.split('\n')
        
        current_chunk_lines = []
        current_tokens = 0
        start_line = 1
        
        for i, line in enumerate(lines, 1):
            line_tokens = self._count_tokens(line + '\n')
            
            # 如果当前行加入后超过token限制，保存当前chunk
            if current_tokens + line_tokens > self.chunk_size_tokens and current_chunk_lines:
                chunk_content = '\n'.join(current_chunk_lines)
                if chunk_content.strip():
                    chunk_id = self._generate_chunk_id(file_path, start_line, i-1)
                    chunks.append({
                        'id': chunk_id,
                        'content': chunk_content,
                        'metadata': {
                            'file_path': file_path,
                            'file_name': file_name,
                            'module': module_name,
                            'start_line': start_line,
                            'end_line': i - 1,
                            'chunk_tokens': current_tokens,
                            'chunk_type': 'fixed_token_size'
                        }
                    })
                
                # 开始新的chunk（有重叠）
                if self.chunk_overlap_tokens > 0 and current_chunk_lines:
                    # 保留最后几行作为重叠（按token数计算）
                    overlap_lines = []
                    overlap_tokens = 0
                    for j in range(len(current_chunk_lines) - 1, -1, -1):
                        line_token_count = self._count_tokens(current_chunk_lines[j] + '\n')
                        if overlap_tokens + line_token_count <= self.chunk_overlap_tokens:
                            overlap_lines.insert(0, current_chunk_lines[j])
                            overlap_tokens += line_token_count
                        else:
                            break
                    
                    current_chunk_lines = overlap_lines
                    current_tokens = overlap_tokens
                    # 计算新的起始行号
                    overlap_line_count = len(overlap_lines)
                    start_line = max(1, i - overlap_line_count)
                else:
                    current_chunk_lines = []
                    current_tokens = 0
                    start_line = i
            
            current_chunk_lines.append(line)
            current_tokens += line_tokens
        
        # 处理最后一个chunk
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines)
            if chunk_content.strip():
                chunk_id = self._generate_chunk_id(file_path, start_line, len(lines))
                chunks.append({
                    'id': chunk_id,
                    'content': chunk_content,
                    'metadata': {
                        'file_path': file_path,
                        'file_name': file_name,
                        'module': module_name,
                        'start_line': start_line,
                        'end_line': len(lines),
                        'chunk_tokens': current_tokens,
                        'chunk_type': 'fixed_token_size'
                    }
                })
        
        return chunks
    
    def _count_tokens(self, text: str) -> int:
        """计算文本的token数量
        
        Args:
            text: 输入文本
            
        Returns:
            int: token数量
        """
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Token计算失败，回退到字符估算: {e}")
                return len(text) // 4  # 粗略估算：1 token ≈ 4 字符
        else:
            # 回退到字符估算
            return len(text) // 4
    
    def _generate_chunk_id(self, file_path: str, start_line: int, end_line: int) -> str:
        """生成代码块ID
        
        Args:
            file_path: 文件路径
            start_line: 起始行号
            end_line: 结束行号
            
        Returns:
            str: 代码块ID
        """
        content = f"{file_path}_{start_line}_{end_line}"
        return hashlib.md5(content.encode()).hexdigest()[:16] 