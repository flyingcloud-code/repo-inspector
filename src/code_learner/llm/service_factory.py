"""
LLM服务工厂

统一管理和配置所有LLM相关服务
支持从配置文件创建服务实例
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

from .embedding_engine import JinaEmbeddingEngine
from .vector_store import ChromaVectorStore
from .chatbot import OpenRouterChatBot
from ..config.config_manager import ConfigManager
from ..core.exceptions import ConfigurationError
from ..utils.logger import get_logger
from ..core.interfaces import IParser, IGraphStore, IEmbeddingEngine, IChatBot, ICallGraphService, IDependencyService
from ..parser.c_parser import CParser
from ..storage.neo4j_store import Neo4jGraphStore
from .call_graph_service import CallGraphService
from .dependency_service import DependencyService

logger = logging.getLogger(__name__)


class ServiceFactory:
    """服务工厂类 - 单例模式
    
    负责创建和管理所有服务实例，包括LLM相关服务
    """
    _services: Dict[str, Any] = {}

    @classmethod
    def get_embedding_engine(cls) -> IEmbeddingEngine:
        """获取嵌入引擎实例"""
        if "embedding_engine" not in cls._services:
            config = ConfigManager().get_config()
            engine = JinaEmbeddingEngine(
                cache_dir=config.llm.embedding_cache_dir
            )
            engine.load_model(config.llm.embedding_model_name)
            cls._services["embedding_engine"] = engine
        return cls._services["embedding_engine"]

    @classmethod
    def get_chatbot(cls) -> IChatBot:
        """获取聊天机器人实例"""
        if "chatbot" not in cls._services:
            config = ConfigManager().get_config()
            chatbot = OpenRouterChatBot(
                api_key=config.llm.chat_api_key
            )
            chatbot.configure_model(
                model_name=config.llm.chat_model,
                max_tokens=config.llm.chat_max_tokens
            )
            cls._services["chatbot"] = chatbot
        return cls._services["chatbot"]

    @classmethod
    def get_parser(cls) -> IParser:
        """获取解析器实例"""
        if "parser" not in cls._services:
            cls._services["parser"] = CParser()
        return cls._services["parser"]

    @classmethod
    def get_graph_store(cls) -> IGraphStore:
        """获取图存储实例"""
        if "graph_store" not in cls._services:
            store = Neo4jGraphStore()
            if not store.connect():
                raise ConnectionError("无法连接到Neo4j数据库")
            cls._services["graph_store"] = store
        return cls._services["graph_store"]

    @classmethod
    def get_call_graph_service(cls) -> ICallGraphService:
        """获取调用图服务实例"""
        if "call_graph_service" not in cls._services:
            graph_store = cls.get_graph_store()
            cls._services["call_graph_service"] = CallGraphService(graph_store)
        return cls._services["call_graph_service"]

    @classmethod
    def get_dependency_service(cls) -> IDependencyService:
        """获取依赖服务实例"""
        if "dependency_service" not in cls._services:
            parser = cls.get_parser()
            graph_store = cls.get_graph_store()
            cls._services["dependency_service"] = DependencyService(parser, graph_store)
        return cls._services["dependency_service"]
    
    @classmethod
    def get_code_qa_service(cls):
        """获取代码问答服务实例"""
        if "code_qa_service" not in cls._services:
            from .code_qa_service import CodeQAService
            cls._services["code_qa_service"] = CodeQAService()
        return cls._services["code_qa_service"]
    
    @classmethod
    def reset(cls) -> None:
        """重置所有服务实例"""
        cls._services.clear()
        logger.info("所有服务实例已重置")

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
            config = ConfigManager().get_config()
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
    
    def create_all_services(self) -> Dict[str, Any]:
        """创建所有LLM服务
        
        Returns:
            Dict[str, Any]: 所有服务实例的字典
        """
        logger.info("🏭 创建所有LLM服务")
        
        services = {
            "embedding_engine": self.get_embedding_engine(),
            "vector_store": self.create_vector_store(),
            "chatbot": self.get_chatbot()
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
            return self.get_embedding_engine()
        elif service_name == "vector_store":
            return self.create_vector_store()
        elif service_name == "chatbot":
            return self.get_chatbot()
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

    # ------------------------------------------------------------------
    # 兼容 CodeQAService 中的 create_* 命名
    # ------------------------------------------------------------------
    def create_embedding_engine(self) -> IEmbeddingEngine:  # alias
        return self.get_embedding_engine()

    def create_chatbot(self) -> IChatBot:
        return self.get_chatbot()

    # 提供通用 create_service 接口
    def create_service(self, name: str):
        if name == "embedding_engine":
            return self.get_embedding_engine()
        elif name == "chatbot":
            return self.get_chatbot()
        elif name == "vector_store":
            return self.create_vector_store()
        else:
            raise ValueError(f"Unknown service name: {name}") 