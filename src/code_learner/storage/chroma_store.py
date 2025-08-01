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
    from chromadb.utils import embedding_functions
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
            persist_directory: 持久化目录路径
            project_id: 项目ID，用于数据隔离
        """
        self.logger = logging.getLogger(__name__)
        self.persist_directory = Path(persist_directory)
        self.project_id = project_id
        self.client: Optional[chromadb.Client] = None
        self.collections: Dict[str, chromadb.Collection] = {}
        self.embedding_function = None
        
        # 确保存储目录存在
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self._initialize_client()
        
        if self.project_id:
            logger.info(f"项目隔离已启用，项目ID: {self.project_id}")
    
    def set_embedding_function(self, model_name: str, cache_dir: str):
        """设置并创建嵌入函数"""
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name,
            cache_folder=cache_dir
        )
        self.logger.info(f"ChromaDB embedding function set to use model: {model_name}")
    
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
                # 创建新集合，使用我们指定的嵌入函数
                if not self.embedding_function:
                    raise ValueError("Embedding function not set. Please call set_embedding_function() first.")
                
                collection = self.client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function, # 指定嵌入函数
                    metadata={"hnsw:space": "cosine"}  # 确保使用余弦相似度
                )
                self.logger.info(f"✅ 新集合 '{collection_name}' 创建成功，使用cosine相似度。")
            
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
            except Exception:
                logger.info(f"集合不存在，将创建新集合: {collection_name}")
                # 创建新集合
                if not self.embedding_function:
                    raise ValueError("Embedding function not set. Please call set_embedding_function() first.")
                
                collection = self.client.create_collection(
                    name=collection_name,
                    embedding_function=self.embedding_function, # 指定嵌入函数
                    metadata={"hnsw:space": "cosine"}  # 确保使用余弦相似度
                )
                self.collections[collection_name] = collection
                self.logger.info(f"✅ 新集合 '{collection_name}' 创建成功。")
            
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

    def is_available(self) -> bool:
        """检查ChromaDB是否可用"""
        try:
            return self.client is not None and self.client.heartbeat() > 0
        except Exception:
            return False
    
    # 项目管理方法
    def create_project(self, project_id: str) -> bool:
        """创建新项目
        
        Args:
            project_id: 项目ID
            
        Returns:
            bool: 创建是否成功
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            logger.info(f"🆕 创建项目: {project_id}")
            
            # 创建项目特定的默认集合
            collection_name = f"{project_id}_code_embeddings"
            
            # 检查集合是否已存在
            existing_collections = self.client.list_collections()
            existing_names = [c.name for c in existing_collections]
            
            if collection_name in existing_names:
                logger.info(f"📚 项目 '{project_id}' 的集合已存在")
                return True
            
            # 创建新集合
            metadata = {
                "hnsw:space": "cosine",
                "description": f"Code embeddings for project: {project_id}",
                "project_id": project_id,
                "created_by": "IndependentCodeEmbedder"
            }
            
            collection = self.client.create_collection(
                name=collection_name,
                metadata=metadata
            )
            
            self.collections[collection_name] = collection
            logger.info(f"✅ 项目 '{project_id}' 创建成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建项目失败 '{project_id}': {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to create project '{project_id}': {str(e)}")
    
    def delete_project(self, project_id: str) -> bool:
        """删除项目及其所有数据
        
        Args:
            project_id: 项目ID
            
        Returns:
            bool: 删除是否成功
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            logger.info(f"🗑️ 删除项目: {project_id}")
            
            # 获取所有属于该项目的集合
            all_collections = self.client.list_collections()
            project_collections = [c.name for c in all_collections if c.name.startswith(f"{project_id}_")]
            
            if not project_collections:
                logger.info(f"项目 '{project_id}' 不存在或已被删除")
                return True
            
            # 删除所有项目集合
            deleted_count = 0
            for collection_name in project_collections:
                try:
                    self.client.delete_collection(collection_name)
                    if collection_name in self.collections:
                        del self.collections[collection_name]
                    deleted_count += 1
                    logger.info(f"✅ 删除集合: {collection_name}")
                except Exception as e:
                    logger.error(f"❌ 删除集合失败 '{collection_name}': {e}")
            
            logger.info(f"✅ 项目 '{project_id}' 删除完成，共删除 {deleted_count} 个集合")
            return deleted_count > 0
            
        except Exception as e:
            logger.error(f"❌ 删除项目失败 '{project_id}': {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to delete project '{project_id}': {str(e)}")
    
    def cleanup_project(self, project_id: str) -> bool:
        """清理项目数据（清空但不删除集合）
        
        Args:
            project_id: 项目ID
            
        Returns:
            bool: 清理是否成功
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            logger.info(f"🧹 清理项目数据: {project_id}")
            
            # 获取所有属于该项目的集合
            all_collections = self.client.list_collections()
            project_collections = [c for c in all_collections if c.name.startswith(f"{project_id}_")]
            
            if not project_collections:
                logger.info(f"项目 '{project_id}' 不存在")
                return True
            
            # 清理所有项目集合的数据
            cleaned_count = 0
            total_deleted = 0
            
            for collection in project_collections:
                try:
                    # 获取集合中的所有文档ID
                    results = collection.get()
                    if results and 'ids' in results and results['ids']:
                        # 批量删除所有文档
                        collection.delete(ids=results['ids'])
                        total_deleted += len(results['ids'])
                        logger.info(f"✅ 清理集合 '{collection.name}': 删除 {len(results['ids'])} 个文档")
                    else:
                        logger.info(f"📚 集合 '{collection.name}' 已为空")
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ 清理集合失败 '{collection.name}': {e}")
            
            logger.info(f"✅ 项目 '{project_id}' 清理完成，共清理 {cleaned_count} 个集合，删除 {total_deleted} 个文档")
            return cleaned_count > 0
            
        except Exception as e:
            logger.error(f"❌ 清理项目失败 '{project_id}': {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to cleanup project '{project_id}': {str(e)}")
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """列出所有项目
        
        Returns:
            List[Dict[str, Any]]: 项目信息列表
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            logger.info("📋 列出所有项目")
            
            # 获取所有集合
            all_collections = self.client.list_collections()
            
            # 按项目ID分组
            projects = {}
            for collection in all_collections:
                # 解析项目ID（假设格式为 project_id_collection_name）
                if '_' in collection.name:
                    parts = collection.name.split('_', 1)
                    if len(parts) >= 2:
                        project_id = parts[0]
                        if project_id not in projects:
                            projects[project_id] = {
                                'project_id': project_id,
                                'collections': [],
                                'total_documents': 0
                            }
                        
                        # 获取集合文档数量
                        try:
                            count = collection.count()
                            collection_info = {
                                'name': collection.name,
                                'document_count': count,
                                'metadata': collection.metadata
                            }
                            projects[project_id]['collections'].append(collection_info)
                            projects[project_id]['total_documents'] += count
                        except Exception as e:
                            logger.warning(f"获取集合 '{collection.name}' 信息失败: {e}")
            
            project_list = list(projects.values())
            logger.info(f"✅ 找到 {len(project_list)} 个项目")
            
            return project_list
            
        except Exception as e:
            logger.error(f"❌ 列出项目失败: {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to list projects: {str(e)}")
    
    def get_project_info(self, project_id: str) -> Dict[str, Any]:
        """获取项目详细信息
        
        Args:
            project_id: 项目ID
            
        Returns:
            Dict[str, Any]: 项目信息
        """
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            logger.info(f"📊 获取项目信息: {project_id}")
            
            # 获取属于该项目的所有集合
            all_collections = self.client.list_collections()
            project_collections = [c for c in all_collections if c.name.startswith(f"{project_id}_")]
            
            if not project_collections:
                return {
                    'project_id': project_id,
                    'exists': False,
                    'collections': [],
                    'total_documents': 0
                }
            
            collections_info = []
            total_documents = 0
            
            for collection in project_collections:
                try:
                    count = collection.count()
                    collection_info = {
                        'name': collection.name,
                        'document_count': count,
                        'metadata': collection.metadata
                    }
                    collections_info.append(collection_info)
                    total_documents += count
                except Exception as e:
                    logger.warning(f"获取集合 '{collection.name}' 信息失败: {e}")
            
            project_info = {
                'project_id': project_id,
                'exists': True,
                'collections': collections_info,
                'total_documents': total_documents,
                'collection_count': len(collections_info)
            }
            
            logger.info(f"✅ 项目 '{project_id}' 信息: {len(collections_info)} 个集合, {total_documents} 个文档")
            return project_info
            
        except Exception as e:
            logger.error(f"❌ 获取项目信息失败 '{project_id}': {e}")
            raise DatabaseConnectionError("chromadb", f"Failed to get project info '{project_id}': {str(e)}")

    def query(self, query_texts: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        在向量数据库中查询与给定文本最相似的嵌入。
        此版本将使用ChromaDB的内置文本查询和嵌入，以确保归一化正确。
        """
        if not query_texts:
            return []

        collection_name = self.get_collection_name()
        collection = self.get_collection(collection_name)

        if not collection:
            self.logger.warning(f"查询失败：无法获取Chroma集合 '{collection_name}'。")
            return []

        try:
            self.logger.info(f"🔍 开始向量查询: top_k={top_k}, collection='{collection.name}'")
            # 必须使用 query_texts 让chroma处理嵌入和归一化
            results = collection.query(
                query_texts=query_texts,
                n_results=top_k,
                include=["metadatas", "documents", "distances"]
            )
            self.logger.info(f"✅ 查询成功: 找到 {len(results.get('ids', [[]])[0])} 个结果")
            
            # 展平结果
            flattened_results = []
            if not results or not results.get('ids') or not results['ids'][0]:
                self.logger.info("查询返回空结果。")
                return []

            ids = results['ids'][0]
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]

            for i, doc_id in enumerate(ids):
                # score is 1 - distance for cosine similarity
                score = 1 - distances[i]
                flattened_results.append({
                    "id": doc_id,
                    "content": documents[i],
                    "metadata": metadatas[i],
                    "score": score
                })
            
            self.logger.debug(f"展平后的查询结果: {flattened_results}")
            return flattened_results

        except Exception as e:
            self.logger.error(f"❌ 在集合 '{collection_name}' 中查询失败: {e}", exc_info=True)
            raise QueryError("chromadb", f"Failed to query collection '{collection_name}': {str(e)}")

    def add(self, documents: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
        """通用添加方法，处理文本、元数据和ID。"""
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        if not documents or not metadatas or not ids:
            raise ValueError("documents, metadatas, and ids must be provided")
        
        collection_name = self.get_collection_name()
        collection = self.get_collection(collection_name)
        
        if not collection:
            raise DatabaseConnectionError("chromadb", f"集合 '{collection_name}' 不存在")
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def get_collection(self, name: str) -> Optional[Any]:
        """获取已缓存或远程的集合对象"""
        if name in self.collections:
            return self.collections[name]
        
        if not self.client:
            raise DatabaseConnectionError("chromadb", "Chroma客户端未初始化")
        
        try:
            # 修正：获取集合时不应再提供嵌入函数。
            # ChromaDB会从持久化存储中自动加载已配置的函数。
            # 重复提供会导致冲突错误。
            collection = self.client.get_collection(name=name)
            self.collections[name] = collection
            return collection
        except Exception as e:
            self.logger.warning(f"获取集合 '{name}' 失败: {e}")
            return None
