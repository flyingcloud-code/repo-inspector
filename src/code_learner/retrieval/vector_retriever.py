"""
向量检索器实现

基于Chroma向量数据库的语义相似度检索。
"""

import logging
from typing import List, Dict, Any

from ..core.context_models import ContextItem, SourceType
from ..core.retriever_interfaces import IContextRetriever
from ..storage.chroma_store import ChromaVectorStore
from ..config.config_manager import ConfigManager
from ..llm.embedding_engine import JinaEmbeddingEngine
import os

logger = logging.getLogger(__name__)

class VectorContextRetriever(IContextRetriever):
    """
    Retrieves context by performing semantic search on a vector database.
    """
    def __init__(self, project_id: str):
        """Initializes the VectorContextRetriever."""
        self.logger = logging.getLogger(__name__)
        self.config = ConfigManager()
        # Initialize embedding engine for similarity search
        self.embedding_engine = JinaEmbeddingEngine()
        
        # Load the correct embedding model
        config = self.config.get_config()
        model_name = config.llm.embedding_model_name
        if not self.embedding_engine.load_model(model_name):
            self.logger.error(f"Failed to load embedding model: {model_name}")
            raise RuntimeError(f"Failed to load embedding model: {model_name}")
        
        # Initialize vector store with project isolation
        self.vector_store = ChromaVectorStore(project_id=project_id)
        logger.info("VectorContextRetriever initialized.")

    def get_source_type(self) -> SourceType:
        """Returns the source type of this retriever."""
        return SourceType.VECTOR

    def is_available(self) -> bool:
        """Checks if the vector store is available."""
        return self.vector_store.is_available()

    def retrieve(self, query: str, intent: Dict[str, Any]) -> List[ContextItem]:
        """
        Retrieves context from the vector database based on the query and intent.
        """
        config = self.config.get_config()
        # 从新配置中读取 top_k 值
        retriever_top_k = config.retrieval.vector_store_top_k
        
        sub_queries = self._generate_sub_queries(query, intent)
        
        all_results: List[Dict[str, Any]] = []
        for sub_query in sub_queries:
            try:
                # 将 top_k 和嵌入引擎传递给查询
                results = self.vector_store.query(
                    query_texts=[sub_query], 
                    top_k=retriever_top_k,
                    embedding_engine=self.embedding_engine
                )
                if results:
                    all_results.extend(results)
            except Exception as e:
                self.logger.error(f"Vector search for sub-query '{sub_query}' failed: {e}", exc_info=True)
                continue
            
        return self._deduplicate_and_convert(all_results, retriever_top_k)
    
    def _generate_sub_queries(self, query: str, intent: Dict[str, Any]) -> List[str]:
        """Generates multiple search queries based on the intent."""
        queries = {query}  # Use a set to handle duplicates automatically
        
        # 1. Add queries for each identified function
        for func_name in intent.get("functions", []):
            queries.add(func_name)
            queries.add(f"function definition for {func_name}")
            queries.add(f"how is {func_name} used")
            queries.add(f"code example for {func_name}")

        # 2. Add queries for each identified file
        for file_name in intent.get("files", []):
            queries.add(file_name)
            queries.add(f"summary of file {file_name}")

        # 3. Add general search terms from intent
        for term in intent.get("search_terms", []):
            queries.add(term)
                    
        self.logger.info(f"Generated {len(queries)} sub-queries for vector search: {queries}")
        return list(queries)
    
    def _deduplicate_and_convert(self, results: List[Dict[str, Any]], top_k: int) -> List[ContextItem]:
        """Deduplicates search results and converts them to ContextItem objects."""
        seen_content = set()
        context_items = []
        
        # Sort by distance ascending (lower distance = higher similarity)
        results.sort(key=lambda x: x.get("distance", 1.0))
        
        for result in results:
            # The key for the content is 'content', not 'document'.
            content = result.get("content")
            distance = result.get("distance", 1.0)
            # Convert distance to similarity score (1 - distance)
            score = max(0.0, 1.0 - distance)
            
            if not content or content in seen_content:
                continue
            
            seen_content.add(content)
            context_items.append(
                ContextItem(
                    content=content,
                    source="vector_search",
                    score=score,
                    metadata=result.get("metadata", {})
                )
            )
            
            if len(context_items) >= top_k:
                break
        
        return context_items