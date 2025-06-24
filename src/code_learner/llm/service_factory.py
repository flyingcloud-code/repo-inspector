"""
LLM服务工厂

统一管理和配置所有LLM相关服务
支持从配置文件创建服务实例
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path

from .embedding_engine import JinaEmbeddingEngine
from .vector_store import ChromaVectorStore
from .chatbot import OpenRouterChatBot
from ..config.config_manager import ConfigManager
from ..core.exceptions import ConfigurationError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class LLMServiceFactory:
    """LLM服务工厂类
    
    负责创建和配置所有LLM相关服务实例
    """
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """初始化服务工厂
        
        Args:
            config_manager: 配置管理器，如果为None则创建默认实例
        """
        self.config_manager = config_manager or ConfigManager()
        self._services: Dict[str, Any] = {}
        
    def create_embedding_engine(self) -> JinaEmbeddingEngine:
        """创建嵌入引擎
        
        Returns:
            JinaEmbeddingEngine: 嵌入引擎实例
        """
        if "embedding_engine" in self._services:
            return self._services["embedding_engine"]
        
        try:
            logger.info("🏭 创建嵌入引擎服务")
            
            # 获取配置
            config = self.config_manager.get_config()
            embedding_config = {
                "cache_dir": config.llm.embedding_cache_dir,
                "model_name": config.llm.embedding_model_name
            }
            
            # 创建嵌入引擎
            engine = JinaEmbeddingEngine(
                cache_dir=embedding_config.get("cache_dir")
            )
            
            # 加载模型
            model_name = embedding_config.get("model_name", "jinaai/jina-embeddings-v2-base-code")
            engine.load_model(model_name)
            
            # 缓存服务实例
            self._services["embedding_engine"] = engine
            
            logger.info(f"✅ 嵌入引擎创建成功: {model_name}")
            return engine
            
        except Exception as e:
            logger.error(f"❌ 嵌入引擎创建失败: {e}")
            raise ConfigurationError("embedding_engine", f"Failed to create embedding engine: {str(e)}")
    
    def create_vector_store(self) -> ChromaVectorStore:
        """创建向量存储
        
        Returns:
            ChromaVectorStore: 向量存储实例
        """
        if "vector_store" in self._services:
            return self._services["vector_store"]
        
        try:
            logger.info("🏭 创建向量存储服务")
            
            # 获取配置
            config = self.config_manager.get_config()
            vector_config = {
                "persist_directory": config.vector_store.chroma_persist_directory,
                "collection_name": config.vector_store.chroma_collection_name
            }
            
            # 创建向量存储
            store = ChromaVectorStore(
                persist_directory=vector_config.get("persist_directory", "./data/chroma")
            )
            
            # 创建默认集合
            collection_name = vector_config.get("collection_name", "code_embeddings")
            store.create_collection(collection_name)
            
            # 缓存服务实例
            self._services["vector_store"] = store
            
            logger.info(f"✅ 向量存储创建成功: {collection_name}")
            return store
            
        except Exception as e:
            logger.error(f"❌ 向量存储创建失败: {e}")
            raise ConfigurationError("vector_store", f"Failed to create vector store: {str(e)}")
    
    def create_chatbot(self) -> OpenRouterChatBot:
        """创建聊天机器人
        
        Returns:
            OpenRouterChatBot: 聊天机器人实例
        """
        if "chatbot" in self._services:
            return self._services["chatbot"]
        
        try:
            logger.info("🏭 创建聊天机器人服务")
            
            # 获取配置
            config = self.config_manager.get_config()
            chat_config = {
                "api_key": config.llm.chat_api_key,
                "base_url": config.llm.chat_base_url,
                "model": config.llm.chat_model,
                "max_tokens": config.llm.chat_max_tokens,
                "temperature": config.llm.chat_temperature,
                "top_p": config.llm.chat_top_p
            }
            
            # 获取API密钥
            api_key = os.getenv("OPENROUTER_API_KEY") or chat_config.get("api_key")
            if not api_key:
                raise ConfigurationError("api_key", "OpenRouter API密钥未配置，请设置环境变量 OPENROUTER_API_KEY")
            
            # 创建聊天机器人
            chatbot = OpenRouterChatBot(
                api_key=api_key,
                base_url=chat_config.get("base_url", "https://openrouter.ai/api/v1/chat/completions")
            )
            
            # 配置模型参数
            chatbot.configure_model(
                model_name=chat_config.get("model", "google/gemini-2.0-flash-001"),
                max_tokens=chat_config.get("max_tokens", 8192),
                temperature=chat_config.get("temperature", 1.0),
                top_p=chat_config.get("top_p", 0.95)
            )
            
            # 缓存服务实例
            self._services["chatbot"] = chatbot
            
            logger.info(f"✅ 聊天机器人创建成功: {chat_config.get('model', 'google/gemini-2.0-flash-001')}")
            return chatbot
            
        except Exception as e:
            logger.error(f"❌ 聊天机器人创建失败: {e}")
            raise ConfigurationError("chatbot", f"Failed to create chatbot: {str(e)}")
    
    def create_all_services(self) -> Dict[str, Any]:
        """创建所有LLM服务
        
        Returns:
            Dict[str, Any]: 所有服务实例的字典
        """
        logger.info("🏭 创建所有LLM服务")
        
        services = {
            "embedding_engine": self.create_embedding_engine(),
            "vector_store": self.create_vector_store(),
            "chatbot": self.create_chatbot()
        }
        
        logger.info("✅ 所有LLM服务创建完成")
        return services
    
    def get_service(self, service_name: str) -> Any:
        """获取指定服务实例
        
        Args:
            service_name: 服务名称 (embedding_engine, vector_store, chatbot)
            
        Returns:
            Any: 服务实例
        """
        if service_name in self._services:
            return self._services[service_name]
        
        # 按需创建服务
        if service_name == "embedding_engine":
            return self.create_embedding_engine()
        elif service_name == "vector_store":
            return self.create_vector_store()
        elif service_name == "chatbot":
            return self.create_chatbot()
        else:
            raise ValueError(f"Unknown service name: {service_name}")
    
    def reset_services(self) -> None:
        """重置所有服务实例
        
        用于测试或重新配置
        """
        logger.info("🔄 重置所有LLM服务")
        self._services.clear()
        logger.info("✅ 服务重置完成")
    
    def get_services_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务状态
        
        Returns:
            Dict: 服务状态信息
        """
        status = {}
        
        for service_name in ["embedding_engine", "vector_store", "chatbot"]:
            if service_name in self._services:
                service = self._services[service_name]
                
                if hasattr(service, 'get_model_info'):
                    status[service_name] = service.get_model_info()
                elif hasattr(service, 'list_collections'):
                    status[service_name] = {
                        "collections": service.list_collections(),
                        "status": "active"
                    }
                else:
                    status[service_name] = {"status": "active"}
            else:
                status[service_name] = {"status": "not_created"}
        
        return status 