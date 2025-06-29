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
from ..core.interfaces import IParser, IGraphStore, IEmbeddingEngine, IChatBot, ICallGraphService, IDependencyService, IVectorStore
from ..parser.c_parser import CParser
from ..storage.neo4j_store import Neo4jGraphStore
from .call_graph_service import CallGraphService
from .dependency_service import DependencyService

logger = logging.getLogger(__name__)


class ServiceFactory:
    """服务工厂类 - 单例模式
    
    负责创建和管理所有服务实例，包括LLM、向量存储、图存储等
    """
    
    # 类级别的服务缓存
    _services = {}
    _embedding_engine = None
    _graph_store = None
    _chatbot = None
    _vector_store = None

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
    def get_graph_store(cls, project_id: str = None) -> IGraphStore:
        """获取图存储实例
        
        Args:
            project_id: 项目ID，用于项目隔离
        """
        # 如果有项目ID，使用带项目ID的键来缓存不同的实例
        cache_key = f"graph_store_{project_id}" if project_id else "graph_store"
        
        if cache_key not in cls._services:
            # 获取配置
            config = ConfigManager().get_config()
            
            # 创建Neo4j存储实例
            store = Neo4jGraphStore(project_id=project_id)
            
            # 纯查询场景可跳过schema init，提高速度
            os.environ.setdefault("SKIP_NEO4J_SCHEMA_INIT", "true")
            
            # 使用配置中的连接参数进行连接
            success = store.connect(
                config.database.neo4j_uri,
                config.database.neo4j_user,
                config.database.neo4j_password
            )
            
            if not success:
                raise ConnectionError("无法连接到Neo4j数据库")
            
            cls._services[cache_key] = store
        return cls._services[cache_key]

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
    def get_vector_store(cls, project_id: Optional[str] = None) -> IVectorStore:
        """获取向量存储实例（单例模式）
        
        Args:
            project_id: 项目ID，用于隔离不同项目的数据
            
        Returns:
            IVectorStore: 向量存储实例
        """
        if not cls._vector_store:
            logger.info("创建向量存储实例...")
            factory = cls()
            cls._vector_store = factory.create_vector_store(project_id=project_id)
            
        return cls._vector_store
    
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

    def create_vector_store(self, project_id: Optional[str] = None) -> IVectorStore:
        """创建向量存储实例
        
        Args:
            project_id: 项目ID，用于隔离不同项目的数据
            
        Returns:
            IVectorStore: 向量存储实例
        """
        try:
            logger.info("🏭 创建向量存储服务")
            
            # 获取配置
            config = ConfigManager().get_config()
            vector_config = {
                "persist_directory": config.vector_store.chroma_persist_directory,
                "collection_name": config.vector_store.chroma_collection_name
            }
            
            # 导入存储实现
            from ..storage.chroma_store import ChromaVectorStore
            
            # 创建向量存储，传入项目ID
            store = ChromaVectorStore(
                persist_directory=vector_config.get("persist_directory", "./data/chroma"),
                project_id=project_id
            )
            
            # 创建默认集合（会自动使用项目ID前缀）
            collection_name = vector_config.get("collection_name", "code_embeddings")
            store.create_collection(collection_name)
            
            logger.info(f"✅ 向量存储创建成功: {store.get_collection_name(collection_name)}")
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
            raise ValueError(f"Unknown service: {service_name}")
    
    def reset_services(self) -> None:
        """重置所有服务实例"""
        for service_name in list(self._services.keys()):
            if hasattr(self._services[service_name], 'close'):
                try:
                    self._services[service_name].close()
                except Exception as e:
                    logger.warning(f"Error closing service {service_name}: {e}")
        self._services.clear()
        logger.info("所有服务实例已重置")
    
    def get_services_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务的状态
        
        Returns:
            Dict[str, Dict[str, Any]]: 服务状态字典
        """
        status = {}
        
        # 检查Neo4j连接
        try:
            graph_store = self.get_graph_store()
            node_count = graph_store.count_nodes()
            rel_count = graph_store.count_relationships()
            status["neo4j"] = {
                "status": "healthy" if node_count > 0 else "warning",
                "nodes": node_count,
                "relationships": rel_count
            }
        except Exception as e:
            status["neo4j"] = {"status": "error", "message": str(e)}
        
        # 检查向量存储
        try:
            vector_store = self.create_vector_store()
            collections = vector_store.list_collections()
            status["vector_store"] = {
                "status": "healthy",
                "collections": len(collections),
                "collection_names": collections
            }
        except Exception as e:
            status["vector_store"] = {"status": "error", "message": str(e)}
        
        return status
    
    def create_embedding_engine(self) -> IEmbeddingEngine:  # alias
        """创建嵌入引擎实例"""
        return self.get_embedding_engine()
    
    def create_chatbot(self) -> IChatBot:
        """创建聊天机器人实例"""
        return self.get_chatbot()
    
    def create_service(self, name: str):
        """创建指定服务实例
        
        Args:
            name: 服务名称
            
        Returns:
            服务实例
        """
        if name == "embedding_engine":
            return self.create_embedding_engine()
        elif name == "vector_store":
            return self.create_vector_store()
        elif name == "chatbot":
            return self.create_chatbot()
        elif name == "code_qa":
            return self.get_code_qa_service()
        else:
            raise ValueError(f"Unknown service: {name}") 