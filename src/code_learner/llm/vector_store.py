"""
向量数据库存储实现

使用Chroma进行向量存储和语义搜索
支持repo级别多集合管理和持久化存储
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
    """
    
    def __init__(self, persist_directory: str = "./data/chroma"):
        """初始化Chroma向量存储
        
        Args:
            persist_directory: 持久化存储目录
        """
        self.persist_directory = Path(persist_directory)
        self.client: Optional[chromadb.PersistentClient] = None
        self.collections: Dict[str, Any] = {}
        
        # 确保存储目录存在
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self._initialize_client()
    
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
            logger.info(f"创建向量集合: {name}")
            
            # 检查集合是否已存在
            existing_collections = self.client.list_collections()
            existing_names = [c.name for c in existing_collections]
            
            if name in existing_names:
                logger.info(f"📚 集合 '{name}' 已存在，获取现有集合")
                collection = self.client.get_collection(name)
            else:
                # 创建新集合，使用余弦相似度
                collection = self.client.create_collection(
                    name=name,
                    metadata={
                        "hnsw:space": "cosine",  # 余弦相似度
                        "description": f"Code embeddings collection: {name}"
                    }
                )
                logger.info(f"✅ 新集合创建成功: {name}")
            
            # 缓存集合对象
            self.collections[name] = collection
            
            # 获取集合信息
            count = collection.count()
            logger.info(f"📊 集合 '{name}' 当前包含 {count} 个向量")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 集合创建失败 '{name}': {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to create collection '{name}': {str(e)}")
    
    def add_embeddings(self, embeddings: List[EmbeddingData]) -> bool:
        """批量添加向量嵌入
        
        Args:
            embeddings: 嵌入数据列表
            
        Returns:
            bool: 添加是否成功
        """
        if not embeddings:
            logger.warning("嵌入列表为空，跳过添加")
            return True
        
        try:
            logger.info(f"🚀 开始批量添加 {len(embeddings)} 个向量嵌入")
            
            # 默认集合名称
            collection_name = "code_embeddings"
            
            # 如果调用方之前创建了集合且尚未创建默认集合，则使用现有集合
            if collection_name not in self.collections and self.collections:
                # 取第一个已存在的集合名称
                collection_name = next(iter(self.collections.keys()))
            
            # 确保集合存在
            if collection_name not in self.collections:
                self.create_collection(collection_name)
            
            collection = self.collections[collection_name]
            
            # 准备批量数据
            ids = [emb.id for emb in embeddings]
            documents = [emb.text for emb in embeddings]
            embeddings_vectors = [emb.embedding for emb in embeddings]
            metadatas = [emb.metadata for emb in embeddings]
            
            # 批量添加到Chroma
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings_vectors,
                metadatas=metadatas
            )
            
            logger.info(f"✅ 批量添加完成: {len(embeddings)} 个向量")
            logger.info(f"📊 集合 '{collection_name}' 现在包含 {collection.count()} 个向量")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 批量添加失败: {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to add embeddings: {str(e)}")
    
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
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            logger.info(f"🔍 开始语义搜索: top_k={top_k}, collection='{collection_name}'")
            
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
            
            # 执行向量搜索
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=min(top_k, collection.count()),
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
            
            logger.info(f"✅ 搜索完成: 找到 {len(formatted_results)} 个相似结果")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 语义搜索失败: {e}")
            raise QueryError(collection_name, f"Vector search failed: {str(e)}")
    
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
            logger.info(f"删除向量集合: {name}")
            
            # 从Chroma删除集合
            self.client.delete_collection(name)
            
            # 从缓存中移除
            if name in self.collections:
                del self.collections[name]
            
            logger.info(f"✅ 集合删除成功: {name}")
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
            if name not in self.collections:
                collection = self.client.get_collection(name)
                self.collections[name] = collection
            else:
                collection = self.collections[name]
            
            return {
                "name": name,
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
            return [c.name for c in collections]
            
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
    
    # -------------------------- Story 2.1 额外接口 --------------------------
    def store_function_embeddings(self, functions: List[Function]) -> bool:  # type: ignore
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
            return self.add_embeddings(embeddings)
        except Exception as e:
            logger.error(f"store_function_embeddings failed: {e}")
            return False
    
    def store_documentation_embeddings(self, documentation):  # type: ignore
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
            return self.add_embeddings(embeddings)
        except Exception as e:
            logger.error(f"store_documentation_embeddings failed: {e}")
            return False 