"""
向量数据库存储实现

使用Chroma进行向量存储和语义搜索
支持repo级别多集合管理和持久化存储
支持项目隔离
"""
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# 尝试导入 chromadb，如果不可用则直接抛出异常，要求在真实环境安装依赖
try:
    import chromadb  # type: ignore
    from chromadb.config import Settings  # type: ignore
    CHROMADB_AVAILABLE = True
except ImportError as e:  # pragma: no cover
    raise ImportError("chromadb library is required for ChromaVectorStore but is not installed. Please install 'chromadb' package.")

from ..core.interfaces import IVectorStore
from ..core.data_models import EmbeddingData, EmbeddingVector, Function
from ..core.exceptions import DatabaseConnectionError, QueryError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChromaVectorStore(IVectorStore):
    """Chroma向量数据库存储实现
    
    支持持久化存储和repo级别多集合管理
    支持项目隔离
    """
    
    def __init__(self, persist_directory: str = "./data/chroma", project_id: Optional[str] = None):
        """初始化Chroma向量存储
        
        Args:
            persist_directory: 持久化存储目录
            project_id: 项目ID，用于隔离不同项目的数据
        """
        self.persist_directory = Path(persist_directory)
        self.project_id = project_id
        self.client: Optional[chromadb.PersistentClient] = None
        self.collections: Dict[str, Any] = {}
        
        # 确保存储目录存在
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self._initialize_client()
        
        if self.project_id:
            logger.info(f"项目隔离已启用，项目ID: {self.project_id}")
    
    def get_collection_name(self, base_name: str = "code_chunks") -> str:
        """根据项目ID生成集合名称
        
        Args:
            base_name: 基础集合名称
            
        Returns:
            str: 项目特定的集合名称
        """
        if self.project_id:
            return f"{self.project_id}_{base_name}"
        return base_name
    
    def _initialize_client(self) -> None:
        """初始化Chroma客户端"""
        try:
            logger.info(f"正在初始化Chroma客户端: {self.persist_directory}")
            
            # 创建持久化客户端
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,  # 禁用遥测
                    allow_reset=True  # 允许重置（测试用）
                )
            )
            
            logger.info(f"✅ Chroma客户端初始化成功")
            logger.info(f"💾 存储目录: {self.persist_directory}")
            
            # 列出现有集合
            existing_collections = self.client.list_collections()
            if existing_collections:
                logger.info(f"📚 发现现有集合: {[c.name for c in existing_collections]}")
            
        except Exception as e:
            logger.error(f"❌ Chroma客户端初始化失败: {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to initialize Chroma client: {str(e)}")
    
    def create_collection(self, name: str) -> bool:
        """创建向量集合
        
        Args:
            name: 集合名称
            
        Returns:
            bool: 创建是否成功
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            # 应用项目隔离
            collection_name = self.get_collection_name(name)
            logger.info(f"创建向量集合: {collection_name}")
            
            # 检查集合是否已存在
            existing_collections = self.client.list_collections()
            existing_names = [c.name for c in existing_collections]
            
            if collection_name in existing_names:
                logger.info(f"📚 集合 '{collection_name}' 已存在，获取现有集合")
                collection = self.client.get_collection(collection_name)
            else:
                # 创建新集合，使用余弦相似度
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={
                        "hnsw:space": "cosine",  # 余弦相似度
                        "description": f"Code embeddings collection: {collection_name}",
                        "project_id": self.project_id  # 添加项目ID到元数据
                    }
                )
                logger.info(f"✅ 新集合创建成功: {collection_name}")
            
            # 缓存集合对象
            self.collections[collection_name] = collection
            
            # 获取集合信息
            count = collection.count()
            logger.info(f"📊 集合 '{collection_name}' 当前包含 {count} 个向量")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 集合创建失败 '{name}': {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to create collection '{name}': {str(e)}")
    
    def add_embeddings(self, texts: List[str], embeddings: List[List[float]], 
                      metadatas: Optional[List[Dict[str, Any]]] = None, 
                      collection_name: Optional[str] = None) -> bool:
        """添加嵌入到指定集合
        
        Args:
            texts: 文本列表
            embeddings: 嵌入向量列表
            metadatas: 元数据列表
            collection_name: 集合名称，如果为None则使用默认集合名称
            
        Returns:
            bool: 添加是否成功
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
            
        if not texts or not embeddings:
            logger.warning("嵌入列表为空，跳过添加")
            return True
            
        # 如果未指定集合名称，使用默认值
        if collection_name is None:
            collection_name = self.get_collection_name()
        
        # 确保集合名称格式正确
        if self.project_id and not collection_name.startswith(self.project_id):
            collection_name = self.get_collection_name(collection_name)
            
        try:
            logger.info(f"🚀 开始添加 {len(texts)} 个向量嵌入到集合 '{collection_name}'")
            
            # 确保集合存在
            try:
                # 尝试获取现有集合
                collection = self.client.get_collection(collection_name)
                self.collections[collection_name] = collection
                logger.info(f"✅ 成功获取现有集合: {collection_name}")
            except Exception as e:
                logger.info(f"集合不存在，将创建新集合: {collection_name} (错误: {str(e)})")
                # 创建新集合
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata={
                        "hnsw:space": "cosine",  # 余弦相似度
                        "description": f"Code embeddings collection: {collection_name}",
                        "project_id": self.project_id  # 添加项目ID到元数据
                    }
                )
                self.collections[collection_name] = collection
                logger.info(f"✅ 新集合创建成功: {collection_name}")
            
            # 获取集合信息
            count = collection.count()
            logger.info(f"📊 集合 '{collection_name}' 当前包含 {count} 个向量")
            
            # 生成唯一ID
            import uuid
            ids = [str(uuid.uuid4()) for _ in range(len(texts))]
            
            # 批量添加到Chroma
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ 批量添加完成: {len(texts)} 个向量")
            logger.info(f"📊 集合 '{collection_name}' 现在包含 {collection.count()} 个向量")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 批量添加失败: {str(e)}")
            raise DatabaseConnectionError("chromadb", f"Failed to add embeddings: {str(e)}")
    
    def query_embeddings(self, query_vector: List[float], n_results: int = 5, 
                        collection_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询嵌入
        
        Args:
            query_vector: 查询向量
            n_results: 返回结果数量
            collection_name: 集合名称，如果为None则使用默认集合名称
            
        Returns:
            List[Dict]: 查询结果列表
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
            
        # 如果未指定集合名称，使用默认值
        if collection_name is None:
            collection_name = self.get_collection_name()
            
        try:
            logger.info(f"🔍 开始向量查询: top_k={n_results}, collection='{collection_name}'")
            
            # 获取集合
            if collection_name not in self.collections:
                # 尝试获取现有集合
                try:
                    collection = self.client.get_collection(collection_name)
                    self.collections[collection_name] = collection
                except:
                    raise QueryError(collection_name, f"集合不存在")
            
            collection = self.collections[collection_name]
            
            # 检查集合是否为空
            if collection.count() == 0:
                logger.warning(f"集合 '{collection_name}' 为空，返回空结果")
                return []
            
            # 执行向量查询
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=min(n_results, collection.count()),
                include=["documents", "metadatas", "distances"]
            )
            
            # 格式化结果
            formatted_results = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    result = {
                        'id': doc_id,
                        'document': results['documents'][0][i] if results['documents'] else "",
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0,
                        'similarity': 1.0 - results['distances'][0][i] if results['distances'] else 1.0
                    }
                    formatted_results.append(result)
            
            logger.info(f"✅ 查询完成: 找到 {len(formatted_results)} 个结果")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 向量查询失败: {e}")
            raise QueryError(collection_name, f"Vector query failed: {str(e)}")
    
    def search_similar(self, query_vector: EmbeddingVector, top_k: int = 5, 
                      collection_name: str = "code_embeddings") -> List[Dict[str, Any]]:
        """搜索相似向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            collection_name: 集合名称
            
        Returns:
            List[Dict]: 相似结果列表
        """
        # 应用项目隔离
        collection_name = self.get_collection_name(collection_name)
        return self.query_embeddings(query_vector, n_results=top_k, collection_name=collection_name)
    
    def delete_collection(self, name: str) -> bool:
        """删除向量集合
        
        Args:
            name: 集合名称
            
        Returns:
            bool: 删除是否成功
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            # 应用项目隔离
            collection_name = self.get_collection_name(name)
            logger.info(f"删除向量集合: {collection_name}")
            
            # 从Chroma删除集合
            self.client.delete_collection(collection_name)
            
            # 从缓存中移除
            if collection_name in self.collections:
                del self.collections[collection_name]
            
            logger.info(f"✅ 集合删除成功: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 集合删除失败 '{name}': {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to delete collection '{name}': {str(e)}")
    
    def get_collection_info(self, name: str) -> Dict[str, Any]:
        """获取集合信息
        
        Args:
            name: 集合名称
            
        Returns:
            Dict: 集合信息
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            # 应用项目隔离
            collection_name = self.get_collection_name(name)
            
            if collection_name not in self.collections:
                collection = self.client.get_collection(collection_name)
                self.collections[collection_name] = collection
            else:
                collection = self.collections[collection_name]
            
            return {
                "name": collection_name,
                "count": collection.count(),
                "metadata": collection.metadata if hasattr(collection, 'metadata') else {}
            }
            
        except Exception as e:
            logger.error(f"获取集合信息失败 '{name}': {e}")
            return {"name": name, "count": 0, "error": str(e)}
    
    def list_collections(self) -> List[str]:
        """列出所有集合
        
        Returns:
            List[str]: 集合名称列表
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            collections = self.client.list_collections()
            all_collections = [c.name for c in collections]
            
            # 如果启用了项目隔离，只返回该项目的集合
            if self.project_id:
                prefix = f"{self.project_id}_"
                return [c for c in all_collections if c.startswith(prefix)]
            
            return all_collections
            
        except Exception as e:
            logger.error(f"列出集合失败: {e}")
            return [] 
    
    def semantic_search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """语义搜索

        将查询文本转换为向量后执行相似度搜索。
        """
        # 延迟导入，避免循环依赖
        from .embedding_engine import JinaEmbeddingEngine  # noqa

        engine = JinaEmbeddingEngine()
        if not engine.model:
            engine.load_model("jinaai/jina-embeddings-v2-base-code")

        query_vec = engine.encode_text(query)
        return self.search_similar(query_vec, top_k=n_results)
    
    def store_function_embeddings(self, functions: List[Function], collection_name: str = "code_embeddings") -> bool:  # type: ignore
        """存储函数级向量嵌入（简化实现）"""
        if not functions:
            return True
        try:
            from .embedding_engine import JinaEmbeddingEngine  # noqa
            engine = JinaEmbeddingEngine()
            if not engine.model:
                engine.load_model("jinaai/jina-embeddings-v2-base-code")
            embeddings: List[EmbeddingData] = []
            for func in functions:
                emb = engine.encode_function(func)
                embeddings.append(emb)
            return self.add_embeddings(embeddings, collection_name)
        except Exception as e:
            logger.error(f"store_function_embeddings failed: {e}")
            return False
    
    def store_documentation_embeddings(self, documentation, collection_name: str = "code_embeddings"):  # type: ignore
        """存储文档向量嵌入（简化实现）"""
        try:
            texts: List[str] = []
            if hasattr(documentation, "get_all_text"):
                texts.append(documentation.get_all_text())
            if not texts:
                return True
            from .embedding_engine import JinaEmbeddingEngine  # noqa
            engine = JinaEmbeddingEngine()
            if not engine.model:
                engine.load_model("jinaai/jina-embeddings-v2-base-code")
            embeddings: List[EmbeddingData] = []
            for idx, text in enumerate(texts):
                vec = engine.encode_text(text)
                embeddings.append(
                    EmbeddingData(
                        id=f"doc_{idx}",
                        text=text,
                        embedding=vec,
                        metadata={"type": "documentation"}
                    )
                )
            return self.add_embeddings(embeddings, collection_name)
        except Exception as e:
            logger.error(f"store_documentation_embeddings failed: {e}")
            return False
    
    def query_collection(self, query_texts: List[str], collection_name: str = None, 
                      n_results: int = 10) -> Dict[str, Any]:
        """查询集合中的嵌入
        
        Args:
            query_texts: 查询文本列表
            collection_name: 集合名称，如果为None则使用默认集合名称
            n_results: 返回结果数量
            
        Returns:
            Dict[str, Any]: 查询结果
            
        Raises:
            DatabaseConnectionError: 查询失败时抛出异常
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
            
        # 如果未指定集合名称，使用默认值
        if collection_name is None:
            collection_name = self.get_collection_name()
        else:
            collection_name = self.get_collection_name(collection_name)
            
        try:
            # 获取集合
            collection = self.client.get_collection(name=collection_name)
            if not collection:
                logger.error(f"集合不存在: {collection_name}")
                return {"ids": [], "embeddings": [], "documents": [], "metadatas": []}
                
            # 查询集合
            logger.info(f"🔍 查询集合 '{collection_name}' 中的嵌入")
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results
            )
            
            logger.info(f"✅ 查询完成，返回 {len(results['ids'])} 条结果")
            return results
            
        except Exception as e:
            logger.error(f"查询集合失败: {e}")
            raise DatabaseConnectionError("chromadb", f"查询集合失败: {e}") 