"""
Chroma向量数据库存储实现

提供Chroma向量数据库的存储功能：
- 连接管理
- 向量存储和检索
- 集合管理
- 项目隔离支持
"""

import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import uuid

# 尝试导入 chromadb，如果不可用则直接抛出异常，要求在真实环境安装依赖
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError as e:
    raise ImportError("chromadb library is required for ChromaVectorStore but is not installed. Please install 'chromadb' package.")

from ..core.interfaces import IVectorStore
from ..core.exceptions import DatabaseConnectionError, QueryError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChromaVectorStore(IVectorStore):
    """Chroma向量数据库存储实现
    
    支持持久化存储和项目级别多集合管理
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
        self.client = None
        self.collections = {}
        
        # 确保存储目录存在
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self._initialize_client()
        
        if self.project_id:
            logger.info(f"项目隔离已启用，项目ID: {self.project_id}")
    
    def get_collection_name(self, base_name: str = "code_embeddings") -> str:
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
                logger.info(f"发现现有集合: {[c.name for c in existing_collections]}")
            
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
                metadata = {
                    "hnsw:space": "cosine"  # 余弦相似度
                }
                
                # 添加描述，确保是字符串类型
                metadata["description"] = f"Code embeddings collection: {collection_name}"
                
                # 仅当project_id不为None时添加到元数据
                if self.project_id:
                    metadata["project_id"] = str(self.project_id)
                
                # 创建集合
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata=metadata
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
                metadata = {
                    "hnsw:space": "cosine"  # 余弦相似度
                }
                
                # 添加描述，确保是字符串类型
                metadata["description"] = f"Code embeddings collection: {collection_name}"
                
                # 仅当project_id不为None时添加到元数据
                if self.project_id:
                    metadata["project_id"] = str(self.project_id)
                
                # 创建集合
                collection = self.client.create_collection(
                    name=collection_name,
                    metadata=metadata
                )
                self.collections[collection_name] = collection
                logger.info(f"✅ 新集合创建成功: {collection_name}")
            
            # 获取集合信息
            count = collection.count()
            logger.info(f"📊 集合 '{collection_name}' 当前包含 {count} 个向量")
            
            # 生成唯一ID
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
        """查询向量嵌入
        
        Args:
            query_vector: 查询向量
            n_results: 返回结果数量
            collection_name: 集合名称
            
        Returns:
            List[Dict]: 查询结果
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        # 如果未指定集合名称，使用默认值
        if collection_name is None:
            collection_name = self.get_collection_name()
            
        # 确保集合名称格式正确
        if self.project_id and not collection_name.startswith(self.project_id):
            collection_name = self.get_collection_name(collection_name)
            
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
            
            # 执行查询
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # 将结果转换为标准格式
            formatted_results = []
            
            if results and "documents" in results and results["documents"]:
                documents = results["documents"][0]  # 第一个查询的结果
                metadatas = results["metadatas"][0] if "metadatas" in results else [{}] * len(documents)
                distances = results["distances"][0] if "distances" in results else [1.0] * len(documents)
                
                for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
                    formatted_results.append({
                        "document": doc,
                        "metadata": meta,
                        "distance": dist,
                        "index": i
                    })
                
                logger.info(f"✅ 查询成功: 找到 {len(formatted_results)} 个结果")
            else:
                logger.warning("⚠️ 查询未返回结果")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 查询失败: {str(e)}")
            raise QueryError(collection_name, f"Failed to query embeddings: {str(e)}")
    
    def similarity_search(self, query: str, top_k: int = 5, 
                        collection_name: Optional[str] = None, 
                        embedding_engine=None) -> List[Dict[str, Any]]:
        """相似度搜索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            collection_name: 集合名称
            embedding_engine: 嵌入引擎，用于将查询文本转换为向量
            
        Returns:
            List[Dict]: 查询结果
        """
        if not embedding_engine:
            raise ValueError("embedding_engine is required for similarity_search")
            
        # 将查询文本转换为向量
        query_vector = embedding_engine.embed_text(query)
        
        # 使用向量查询
        return self.query_embeddings(query_vector, n_results=top_k, collection_name=collection_name)
    
    def delete_collection(self, name: str) -> bool:
        """删除集合
        
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
            logger.info(f"删除集合: {collection_name}")
            
            # 检查集合是否存在
            existing_collections = self.client.list_collections()
            existing_names = [c.name for c in existing_collections]
            
            if collection_name not in existing_names:
                logger.warning(f"集合 '{collection_name}' 不存在，无需删除")
                return True
            
            # 删除集合
            self.client.delete_collection(collection_name)
            
            # 从缓存中移除
            if collection_name in self.collections:
                del self.collections[collection_name]
            
            logger.info(f"✅ 集合 '{collection_name}' 已删除")
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除集合失败 '{name}': {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to delete collection '{name}': {str(e)}")
    
    def get_collection_info(self, name: str) -> Dict[str, Any]:
        """获取集合信息
        
        Args:
            name: 集合名称
            
        Returns:
            Dict[str, Any]: 集合信息
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
            
        try:
            # 应用项目隔离
            collection_name = self.get_collection_name(name)
            logger.info(f"获取集合信息: {collection_name}")
            
            # 获取集合
            if collection_name not in self.collections:
                # 尝试获取现有集合
                try:
                    collection = self.client.get_collection(collection_name)
                    self.collections[collection_name] = collection
                except:
                    raise QueryError(collection_name, f"集合不存在")
            
            collection = self.collections[collection_name]
            
            # 获取集合信息
            count = collection.count()
            
            return {
                "name": collection_name,
                "count": count,
                "metadata": collection.metadata
            }
            
        except Exception as e:
            logger.error(f"❌ 获取集合信息失败 '{name}': {e}")
            raise QueryError(collection_name, f"Failed to get collection info '{name}': {str(e)}")
    
    def list_collections(self) -> List[str]:
        """列出所有集合
        
        Returns:
            List[str]: 集合名称列表
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
            
        try:
            logger.info("列出所有集合")
            
            # 获取所有集合
            all_collections = self.client.list_collections()
            collection_names = [c.name for c in all_collections]
            
            # 如果启用了项目隔离，只返回当前项目的集合
            if self.project_id:
                prefix = f"{self.project_id}_"
                collection_names = [name for name in collection_names if name.startswith(prefix)]
                logger.info(f"应用项目隔离过滤，找到 {len(collection_names)} 个属于项目 {self.project_id} 的集合")
            
            logger.info(f"✅ 找到 {len(collection_names)} 个集合")
            return collection_names
            
        except Exception as e:
            logger.error(f"❌ 列出集合失败: {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to list collections: {str(e)}")
    
    def count_documents(self, collection_name: Optional[str] = None) -> int:
        """计算集合中的文档数量
        
        Args:
            collection_name: 集合名称，如果为None则使用默认集合名称
            
        Returns:
            int: 文档数量
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
            
        # 如果未指定集合名称，使用默认值
        if collection_name is None:
            collection_name = self.get_collection_name()
            
        try:
            logger.info(f"计算集合 '{collection_name}' 中的文档数量")
            
            # 获取集合
            if collection_name not in self.collections:
                # 尝试获取现有集合
                try:
                    collection = self.client.get_collection(collection_name)
                    self.collections[collection_name] = collection
                except:
                    raise QueryError(collection_name, f"集合不存在")
            
            collection = self.collections[collection_name]
            
            # 获取文档数量
            count = collection.count()
            
            logger.info(f"✅ 集合 '{collection_name}' 包含 {count} 个文档")
            return count
            
        except Exception as e:
            logger.error(f"❌ 计算文档数量失败: {e}")
            raise QueryError(collection_name, f"Failed to count documents: {str(e)}")
    
    def close(self) -> None:
        """关闭连接"""
        # Chroma客户端不需要显式关闭
        self.collections = {}
        logger.info("Chroma连接已关闭")

    def search_similar(self, query_vector: List[float], top_k: int = 5, 
                      collection_name: str = "code_embeddings") -> List[Dict[str, Any]]:
        """搜索相似的向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            collection_name: 集合名称
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        return self.query_embeddings(query_vector, top_k, collection_name)

    def semantic_search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """语义搜索
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        # 这个方法需要嵌入引擎，但我们不在这里实现
        # 在实际使用时，应该由上层服务提供嵌入功能
        logger.warning("semantic_search方法需要嵌入引擎，请使用上层服务的语义搜索功能")
        return []

    def store_function_embeddings(self, functions: List[Any], collection_name: str = "code_embeddings") -> bool:
        """存储函数嵌入
        
        Args:
            functions: 函数列表
            collection_name: 集合名称
            
        Returns:
            bool: 存储是否成功
        """
        # 这个方法需要嵌入引擎，但我们不在这里实现
        # 在实际使用时，应该由上层服务提供嵌入功能
        logger.warning("store_function_embeddings方法需要嵌入引擎，请使用上层服务的存储功能")
        return True

    def store_documentation_embeddings(self, documentation: Any, collection_name: str = "code_embeddings") -> bool:
        """存储文档嵌入
        
        Args:
            documentation: 文档
            collection_name: 集合名称
            
        Returns:
            bool: 存储是否成功
        """
        # 这个方法需要嵌入引擎，但我们不在这里实现
        # 在实际使用时，应该由上层服务提供嵌入功能
        logger.warning("store_documentation_embeddings方法需要嵌入引擎，请使用上层服务的存储功能")
        return True
