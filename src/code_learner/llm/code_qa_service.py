"""
代码问答服务

整合向量嵌入、向量存储和聊天机器人
提供统一的代码问答和摘要生成服务
支持repo级别的智能代码分析
"""
import logging
from typing import List, Dict, Any, Optional

from .service_factory import ServiceFactory
from .embedding_engine import JinaEmbeddingEngine
from .vector_store import ChromaVectorStore
from .chatbot import OpenRouterChatBot
from ..core.data_models import Function, EmbeddingData, ChatResponse
from ..core.exceptions import ServiceError, QueryError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CodeQAService:
    """代码问答服务
    
    整合所有LLM服务，提供统一的代码分析和问答接口
    支持repo级别的智能代码理解和交互
    """
    
    def __init__(self, service_factory: Optional[ServiceFactory] = None):
        """初始化代码问答服务"""
        self.service_factory = service_factory or ServiceFactory()
        
        # 延迟初始化服务
        self._embedding_engine: Optional[JinaEmbeddingEngine] = None
        self._vector_store: Optional[ChromaVectorStore] = None
        self._chatbot: Optional[OpenRouterChatBot] = None
        
    @property
    def embedding_engine(self) -> JinaEmbeddingEngine:
        """获取嵌入引擎（延迟加载）"""
        if self._embedding_engine is None:
            self._embedding_engine = self.service_factory.get_embedding_engine()
        return self._embedding_engine
    
    @property
    def vector_store(self) -> ChromaVectorStore:
        """获取向量存储（延迟加载）"""
        if self._vector_store is None:
            self._vector_store = self.service_factory.create_vector_store()
        return self._vector_store
    
    @property
    def chatbot(self) -> OpenRouterChatBot:
        """获取聊天机器人（延迟加载）"""
        if self._chatbot is None:
            self._chatbot = self.service_factory.get_chatbot()
        return self._chatbot
    
    def ask_code_question(self, question: str) -> str:
        """询问代码相关问题 - 简化版本"""
        try:
            response = self.chatbot.ask_question(question)
            return response.content
        except Exception as e:
            logger.error(f"代码问题回答失败: {e}")
            raise ServiceError(f"Failed to answer question: {str(e)}")
    
    # 兼容外部调用名称
    def ask_question(self, question: str, context: Optional[dict] = None) -> str:  # noqa
        return self.ask_code_question(question)
    
    def generate_code_summary(self, code_content: str, file_path: Optional[str] = None) -> str:
        """生成代码摘要 - 用户明确要求的功能"""
        try:
            response = self.chatbot.generate_summary(code_content, file_path)
            return response.content
        except Exception as e:
            logger.error(f"代码摘要生成失败: {e}")
            raise ServiceError(f"Failed to generate summary: {str(e)}")
 