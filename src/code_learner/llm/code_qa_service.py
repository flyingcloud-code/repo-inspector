"""
代码问答服务

整合向量嵌入、向量存储和聊天机器人
提供统一的代码问答和摘要生成服务
支持repo级别的智能代码分析
"""
import logging
import os
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
    
    def __init__(self, service_factory: Optional[ServiceFactory] = None, project_id: str = None):
        """初始化代码问答服务
        
        Args:
            service_factory: 服务工厂
            project_id: 项目ID，用于项目隔离
        """
        self.service_factory = service_factory or ServiceFactory()
        self.project_id = project_id
        
        # 延迟初始化服务
        self._embedding_engine: Optional[JinaEmbeddingEngine] = None
        self._vector_store: Optional[ChromaVectorStore] = None
        self._chatbot: Optional[OpenRouterChatBot] = None
        self._graph_store: Optional = None
        
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
            self._vector_store = self.service_factory.create_vector_store(project_id=self.project_id)
        return self._vector_store
    
    @property
    def chatbot(self) -> OpenRouterChatBot:
        """获取聊天机器人（延迟加载）"""
        if self._chatbot is None:
            self._chatbot = self.service_factory.get_chatbot()
        return self._chatbot
    
    @property
    def graph_store(self):
        """获取图存储（延迟加载）"""
        if self._graph_store is None:
            self._graph_store = self.service_factory.get_graph_store(project_id=self.project_id)
        return self._graph_store
    
    def ask_code_question(self, question: str) -> str:
        """询问代码相关问题 - 简化版本"""
        try:
            response = self.chatbot.ask_question(question)
            return response.content
        except Exception as e:
            logger.error(f"代码问题回答失败: {e}")
            raise ServiceError(f"Failed to answer question: {str(e)}")
    
    def ask_question(self, question: str, context: Optional[dict] = None) -> str:
        """询问代码相关问题
        
        Args:
            question: 用户问题
            context: 上下文信息，包含project_path, focus_function, focus_file
            
        Returns:
            str: 回答内容
        """
        try:
            logger.info(f"收到代码问题: {question}")
            
            # 初始化代码上下文
            code_context = self._build_code_context(question, context)
            
            # 调用聊天机器人，传入代码上下文
            response = self.chatbot.ask_question(question, code_context)
            
            logger.info("问题回答完成")
            return response.content
            
        except Exception as e:
            logger.error(f"代码问题回答失败: {e}")
            raise ServiceError(f"Failed to answer question: {str(e)}")
    
    def _build_code_context(self, question: str, context: Optional[dict] = None) -> str:
        """构建代码上下文，从多个来源获取相关代码
        
        Args:
            question: 用户问题
            context: 上下文信息
            
        Returns:
            str: 代码上下文
        """
        code_context = ""
        
        # 1. 从Neo4j获取函数代码
        if context and context.get("focus_function"):
            function_context = self._get_function_context(context["focus_function"])
            if function_context:
                code_context += function_context
        
        # 2. 从文件获取代码
        if context and context.get("focus_file"):
            file_context = self._get_file_context(context["focus_file"])
            if file_context:
                code_context += file_context
        
        # 3. 使用向量检索找到相关代码片段
        try:
            vector_context = self._get_vector_context(question)
            if vector_context:
                code_context += vector_context
        except Exception as e:
            logger.warning(f"向量检索相关代码片段失败: {e}")
        
        # 4. 从项目路径获取相关信息
        if context and context.get("project_path"):
            code_context += f"项目路径: {context['project_path']}\n\n"
        
        if not code_context:
            logger.warning("未找到相关代码上下文")
            code_context = "未找到相关代码上下文。请提供更多信息。"
        
        return code_context
    
    def _get_function_context(self, function_name: str) -> str:
        """获取函数上下文
        
        Args:
            function_name: 函数名
            
        Returns:
            str: 函数上下文
        """
        context = ""
        try:
            # 使用项目特定的图存储
            graph_store = self.graph_store
            
            # 从Neo4j检索函数代码
            function_code = graph_store.get_function_code(function_name)
            if function_code:
                context += f"函数 '{function_name}' 的代码:\n```c\n{function_code}\n```\n\n"
                
                # 只有当函数存在时，才检索函数调用关系
                try:
                    callers = graph_store.query_function_callers(function_name)
                    if callers:
                        context += f"调用 '{function_name}' 的函数: {', '.join(callers)}\n\n"
                except NotImplementedError:
                    logger.debug("函数调用者查询功能未实现")
                
                try:
                    callees = graph_store.query_function_calls(function_name)
                    if callees:
                        context += f"'{function_name}' 调用的函数: {', '.join(callees)}\n\n"
                except NotImplementedError:
                    logger.debug("函数被调用查询功能未实现")
            else:
                logger.warning(f"函数 '{function_name}' 未找到或没有代码")
                
        except Exception as e:
            logger.warning(f"获取函数上下文失败: {e}")
            
        return context
    
    def _get_file_context(self, file_path: str) -> str:
        """获取文件上下文
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件上下文
        """
        context = ""
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在: {file_path}")
                return context
            
            # 读取文件内容
            with open(file_path, 'r') as f:
                file_content = f.read()
                
            # 添加文件内容到上下文
            context += f"文件 '{file_path}' 的代码:\n```c\n{file_content}\n```\n\n"
                
        except Exception as e:
            logger.warning(f"获取文件上下文失败: {e}")
            
        return context
    
    def _get_vector_context(self, question: str, top_k: int = 3) -> str:
        """获取向量上下文
        
        使用向量检索找到与问题相关的代码片段
        
        Args:
            question: 问题文本
            top_k: 返回结果数量
            
        Returns:
            str: 向量上下文
        """
        # 延迟加载嵌入引擎
        if not self.embedding_engine:
            self.embedding_engine = JinaEmbeddingEngine()
            if not self.embedding_engine.model:
                self.embedding_engine.load_model("jinaai/jina-embeddings-v2-base-code")
        
        # 检查向量存储是否已初始化
        if not self.vector_store or not self.vector_store.client:
            logger.warning("向量存储未初始化，跳过向量检索")
            return ""
        
        try:
            # 生成问题的嵌入向量
            question_embedding = self.embedding_engine.encode_text(question)
            
            # 从向量存储中检索相关代码片段
            results = self.vector_store.search_similar(
                query_vector=question_embedding,
                top_k=top_k,
                collection_name="code_embeddings"
            )
            
            if not results:
                logger.info("未找到相关代码片段")
                return ""
            
            # 构建上下文
            context = "## 相关代码片段\n\n"
            
            for i, result in enumerate(results):
                # 获取代码片段元数据
                metadata = result.get('metadata', {})
                file_path = metadata.get('file_path', 'unknown')
                start_line = metadata.get('start_line', 0)
                end_line = metadata.get('end_line', 0)
                function_name = metadata.get('function_name', '')
                similarity = result.get('similarity', 0.0)
                
                # 添加代码片段信息
                context += f"### 片段 {i+1} (相似度: {similarity:.2f})\n"
                if function_name:
                    context += f"函数: `{function_name}`\n"
                context += f"位置: `{file_path}:{start_line}-{end_line}`\n\n"
                
                # 添加代码内容
                context += f"```\n{result['document']}\n```\n\n"
            
            return context
            
        except Exception as e:
            logger.warning(f"向量检索相关代码片段失败: {e}")
            return ""
    
    def generate_code_summary(self, code_content: str, file_path: Optional[str] = None) -> str:
        """生成代码摘要 - 用户明确要求的功能"""
        try:
            response = self.chatbot.generate_summary(code_content, file_path)
            return response.content
        except Exception as e:
            logger.error(f"代码摘要生成失败: {e}")
            raise ServiceError(f"Failed to generate summary: {str(e)}")
 