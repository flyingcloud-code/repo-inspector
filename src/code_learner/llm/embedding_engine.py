"""
嵌入生成引擎实现

使用jina-embeddings-v2-base-code模型进行代码向量化
支持repo级别批量处理优化
"""
import logging
from typing import List, Optional
from pathlib import Path

from sentence_transformers import SentenceTransformer
import numpy as np

from ..core.interfaces import IEmbeddingEngine
from ..core.data_models import Function, EmbeddingData, EmbeddingVector
from ..core.exceptions import ModelLoadError, EmbeddingError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class JinaEmbeddingEngine(IEmbeddingEngine):
    """jina-embeddings-v2-base-code嵌入引擎
    
    专门针对代码优化的嵌入模型，支持repo级别批量处理
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        """初始化嵌入引擎
        
        Args:
            cache_dir: 模型缓存目录
        """
        self.model: Optional[SentenceTransformer] = None
        self.cache_dir = cache_dir or "~/.cache/torch/sentence_transformers/"
        self.model_name: Optional[str] = None
        
    def load_model(self, model_name: str) -> bool:
        """加载嵌入模型
        
        Args:
            model_name: 模型名称，推荐 "jinaai/jina-embeddings-v2-base-code"
            
        Returns:
            bool: 加载是否成功
        """
        try:
            logger.info(f"正在加载嵌入模型: {model_name}")
            
            # 加载sentence-transformers模型
            self.model = SentenceTransformer(
                model_name,
                cache_folder=self.cache_dir
            )
            self.model_name = model_name
            
            # 验证模型加载
            test_embedding = self.model.encode("test")
            embedding_dim = len(test_embedding)
            
            logger.info(f"✅ 模型加载成功: {model_name}")
            logger.info(f"📊 嵌入维度: {embedding_dim}")
            logger.info(f"💾 缓存目录: {self.cache_dir}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {e}")
            raise ModelLoadError(model_name, f"Failed to load model: {str(e)}")
    
    def encode_text(self, text: str) -> EmbeddingVector:
        """编码文本为向量
        
        Args:
            text: 输入文本
            
        Returns:
            EmbeddingVector: 向量嵌入
            
        Raises:
            ModelLoadError: 模型未加载
            EmbeddingError: 编码失败
        """
        if not self.model:
            raise ModelLoadError("模型未加载，请先调用load_model()")
        
        if not text.strip():
            raise EmbeddingError(text, "输入文本不能为空")
        
        try:
            # 使用sentence-transformers编码
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"文本编码失败: {e}")
            raise EmbeddingError(text, f"编码失败: {str(e)}")
    
    def encode_function(self, function: Function) -> EmbeddingData:
        """编码函数为向量嵌入
        
        Args:
            function: 函数对象
            
        Returns:
            EmbeddingData: 嵌入数据
        """
        if not self.model:
            raise ModelLoadError("模型未加载，请先调用load_model()")
        
        try:
            # 构建函数的文档文本
            doc_text = self._create_function_document(function)
            
            # 生成向量嵌入
            embedding = self.encode_text(doc_text)
            
            # 创建嵌入数据对象
            embedding_data = EmbeddingData(
                id=f"{function.file_path}_{function.name}_{function.start_line}",
                text=doc_text,
                embedding=embedding,
                metadata={
                    "type": "function",
                    "file_path": function.file_path,
                    "function_name": function.name,
                    "start_line": function.start_line,
                    "end_line": function.end_line,
                    "code_length": len(function.code)
                }
            )
            
            return embedding_data
            
        except Exception as e:
            logger.error(f"函数编码失败: {function.name} in {function.file_path}: {e}")
            raise EmbeddingError(function.code, f"函数编码失败: {str(e)}")
    
    def encode_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """批量编码文本 - repo级别优化
        
        Args:
            texts: 文本列表
            
        Returns:
            List[EmbeddingVector]: 向量列表
        """
        if not self.model:
            raise ModelLoadError("模型未加载，请先调用load_model()")
        
        if not texts:
            return []
        
        try:
            logger.info(f"🚀 开始批量编码 {len(texts)} 个文本")
            
            # 使用sentence-transformers的批量编码优化
            # batch_size=32 是一个平衡内存和速度的选择
            embeddings = self.model.encode(
                texts,
                batch_size=32,
                show_progress_bar=True,
                convert_to_numpy=True
            )
            
            # 转换为列表格式
            embedding_list = [embedding.tolist() for embedding in embeddings]
            
            logger.info(f"✅ 批量编码完成: {len(embedding_list)} 个向量")
            return embedding_list
            
        except Exception as e:
            logger.error(f"❌ 批量编码失败: {e}")
            raise EmbeddingError(f"batch_{len(texts)}_texts", f"批量编码失败: {str(e)}")
    
    def _create_function_document(self, function: Function) -> str:
        """为函数创建文档文本
        
        Args:
            function: 函数对象
            
        Returns:
            str: 格式化的文档文本
        """
        # 创建结构化的函数文档
        doc_parts = [
            f"文件路径: {function.file_path}",
            f"函数名称: {function.name}",
            f"行号范围: {function.start_line}-{function.end_line}",
            "函数代码:",
            function.code.strip()
        ]
        
        return "\n".join(doc_parts)
    
    def get_model_info(self) -> dict:
        """获取模型信息
        
        Returns:
            dict: 模型信息
        """
        if not self.model:
            return {"status": "not_loaded"}
        
        # 获取嵌入维度
        test_embedding = self.model.encode("test")
        
        return {
            "status": "loaded",
            "model_name": self.model_name,
            "embedding_dimension": len(test_embedding),
            "cache_dir": self.cache_dir,
            "device": str(self.model.device) if hasattr(self.model, 'device') else "cpu"
        } 