"""
依赖图检索器实现

基于Neo4j图数据库的文件依赖关系检索。
"""

import time
import logging
from typing import List, Dict, Any, Set
from ..core.context_models import (
    ContextItem, 
    IntentAnalysis, 
    RetrievalConfig, 
    RetrievalResult,
    SourceType
)
from ..core.retriever_interfaces import IContextRetriever
from ..storage.neo4j_store import Neo4jGraphStore

logger = logging.getLogger(__name__)


class DependencyContextRetriever(IContextRetriever):
    """依赖图检索器
    
    基于文件依赖关系从Neo4j图数据库检索相关上下文。
    提供文件包含关系、模块依赖、循环依赖等信息。
    """
    
    def __init__(self, graph_store: Neo4jGraphStore):
        """初始化依赖图检索器
        
        Args:
            graph_store: Neo4j图存储实例
        """
        self.graph_store = graph_store
        self.source_type = SourceType.DEPENDENCY
        
    def retrieve(
        self, 
        query: str, 
        intent_analysis: IntentAnalysis, 
        config: RetrievalConfig
    ) -> RetrievalResult:
        """检索依赖关系相关的上下文
        
        Args:
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 检索配置
            
        Returns:
            检索结果
        """
        start_time = time.time()
        
        try:
            context_items = []
            
            # 如果意图分析中包含文件名，执行依赖关系检索
            if intent_analysis.has_file_names():
                file_names = intent_analysis.get_file_names()
                for file_name in file_names:
                    context_items.extend(
                        self._retrieve_by_file_name(file_name, config)
                    )
            
            # 如果包含函数名，检索函数所在文件的依赖
            if intent_analysis.has_function_names():
                function_names = intent_analysis.get_function_names()
                for function_name in function_names:
                    context_items.extend(
                        self._retrieve_by_function_name(function_name, config)
                    )
            
            # 如果没有明确的文件名或函数名，尝试关键词匹配
            if not context_items:
                context_items.extend(
                    self._retrieve_by_keywords(query, intent_analysis, config)
                )
            
            # 限制结果数量
            context_items = context_items[:config.top_k]
            
            query_time = time.time() - start_time
            
            logger.info(f"Dependency retrieval completed: {len(context_items)} items in {query_time:.3f}s")
            
            return RetrievalResult(
                items=context_items,
                source_type=self.source_type,
                query_time=query_time,
                total_candidates=len(context_items)
            )
            
        except Exception as e:
            logger.error(f"Dependency retrieval failed: {e}")
            return RetrievalResult(
                items=[],
                source_type=self.source_type,
                query_time=time.time() - start_time,
                total_candidates=0
            )
    
    def _retrieve_by_file_name(self, file_name: str, config: RetrievalConfig) -> List[ContextItem]:
        """根据文件名检索依赖关系
        
        Args:
            file_name: 文件名
            config: 检索配置
            
        Returns:
            上下文项列表
        """
        logger.info(f"根据文件名检索依赖关系: {file_name}")
        
        try:
            # 获取文件的依赖关系
            includes = self.graph_store.get_file_includes(file_name)
            included_by = self.graph_store.get_file_included_by(file_name)
            
            context_items = []
            
            # 添加文件包含的头文件
            if includes:
                includes_content = f"File {file_name} includes:\n"
                for include in includes:
                    includes_content += f"- {include.get('path', '')}\n"
                
                context_items.append(ContextItem(
                    content=includes_content,
                    source_type=self.source_type,
                    relevance_score=0.8,
                    metadata={
                        "file_name": file_name,
                        "relation_type": "includes",
                        "include_count": len(includes)
                    }
                ))
            
            # 添加包含该文件的文件
            if included_by:
                included_by_content = f"File {file_name} is included by:\n"
                for include in included_by:
                    included_by_content += f"- {include.get('path', '')}\n"
                
                context_items.append(ContextItem(
                    content=included_by_content,
                    source_type=self.source_type,
                    relevance_score=0.7,
                    metadata={
                        "file_name": file_name,
                        "relation_type": "included_by",
                        "included_by_count": len(included_by)
                    }
                ))
            
            return context_items
            
        except Exception as e:
            logger.error(f"检索文件依赖关系失败: {e}")
            return []
    
    def _retrieve_by_function_name(self, function_name: str, config: RetrievalConfig) -> List[ContextItem]:
        """根据函数名检索所在文件的依赖关系
        
        Args:
            function_name: 函数名
            config: 检索配置
            
        Returns:
            上下文项列表
        """
        logger.info(f"根据函数名检索文件依赖关系: {function_name}")
        
        try:
            # 获取函数所在文件
            function = self.graph_store.get_function_by_name(function_name)
            if not function or "file_path" not in function:
                logger.warning(f"函数不存在或无法获取文件路径: {function_name}")
                return []
            
            # 检索文件的依赖关系
            file_path = function["file_path"]
            return self._retrieve_by_file_name(file_path, config)
            
        except Exception as e:
            logger.error(f"检索函数所在文件依赖关系失败: {e}")
            return []
    
    def _retrieve_by_keywords(self, query: str, intent_analysis: IntentAnalysis, config: RetrievalConfig) -> List[ContextItem]:
        """根据关键词检索依赖关系
        
        Args:
            query: 用户查询
            intent_analysis: 意图分析结果
            config: 检索配置
            
        Returns:
            上下文项列表
        """
        logger.info(f"根据关键词检索依赖关系")
        
        # 使用简单的启发式规则：如果查询中包含"include"、"header"、"dependency"等关键词，
        # 尝试查找项目中最重要的几个头文件
        
        if any(word in query.lower() for word in ["include", "header", "dependency", "dependencies"]):
            try:
                # 获取项目中被包含次数最多的头文件
                top_headers = self.graph_store.get_top_included_files(limit=config.top_k)
                
                if not top_headers:
                    return []
                
                content = "Most frequently included header files:\n"
                for header in top_headers:
                    content += f"- {header.get('path', '')}: included {header.get('include_count', 0)} times\n"
                
                return [ContextItem(
                    content=content,
                    source_type=self.source_type,
                    relevance_score=0.6,
                    metadata={
                        "relation_type": "top_headers",
                        "header_count": len(top_headers)
                    }
                )]
                
            except Exception as e:
                logger.error(f"检索热门头文件失败: {e}")
        
        return []
    
    def get_source_type(self) -> str:
        """获取检索器的源类型标识"""
        return self.source_type.value
    
    def is_available(self) -> bool:
        """检查图数据库是否可用"""
        try:
            with self.graph_store.driver.session() as session:
                result = session.run("RETURN 1 as test")
                result.single()
                return True
        except Exception as e:
            logger.warning(f"Graph store not available: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取依赖图统计信息"""
        try:
            with self.graph_store.driver.session() as session:
                # 获取文件总数
                file_count_result = session.run("MATCH (f:File) RETURN count(f) as count")
                file_count = file_count_result.single()["count"]
                
                # 获取包含关系总数
                include_count_result = session.run("MATCH ()-[r:INCLUDES]->() RETURN count(r) as count")
                include_count = include_count_result.single()["count"]
                
                # 检查是否有循环依赖
                circular_query = """
                MATCH path = (start:File)-[:INCLUDES*2..5]->(start)
                RETURN count(DISTINCT start) as circular_files
                """
                circular_result = session.run(circular_query)
                circular_count = circular_result.single()["circular_files"]
                
                return {
                    "source_type": self.get_source_type(),
                    "available": True,
                    "file_count": file_count,
                    "include_relationship_count": include_count,
                    "circular_dependency_files": circular_count
                }
        except Exception as e:
            logger.error(f"Failed to get dependency statistics: {e}")
            return {
                "source_type": self.get_source_type(),
                "available": False,
                "error": str(e)
            } 