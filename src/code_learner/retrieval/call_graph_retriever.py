"""
调用图检索器实现

基于Neo4j图数据库的函数调用关系检索。
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


class CallGraphContextRetriever(IContextRetriever):
    """调用图检索器
    
    基于函数调用关系从Neo4j图数据库检索相关上下文。
    提供调用者、被调用者、调用链等多维度信息。
    """
    
    def __init__(self, graph_store: Neo4jGraphStore):
        """初始化调用图检索器
        
        Args:
            graph_store: Neo4j图存储实例
        """
        self.graph_store = graph_store
        self.source_type = SourceType.CALL_GRAPH
        
    def retrieve(
        self, 
        query: str, 
        intent_analysis: IntentAnalysis, 
        config: RetrievalConfig
    ) -> RetrievalResult:
        """检索调用关系相关的上下文
        
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
            
            # 如果意图分析包含函数名，检索函数调用关系
            if intent_analysis.has_function_names():
                function_names = intent_analysis.get_function_names()
                for function_name in function_names:
                    context_items.extend(
                        self._retrieve_by_function_name(function_name, config)
                    )
            
            # 如果没有明确的函数名，尝试模糊匹配
            if not context_items:
                context_items.extend(
                    self._retrieve_by_fuzzy_match(query, intent_analysis, config)
                )
            
            # 限制结果数量
            context_items = context_items[:config.top_k]
            
            query_time = time.time() - start_time
            
            logger.info(f"Call graph retrieval completed: {len(context_items)} items in {query_time:.3f}s")
            
            return RetrievalResult(
                items=context_items,
                source_type=self.source_type,
                query_time=query_time,
                total_candidates=len(context_items)
            )
            
        except Exception as e:
            logger.error(f"Call graph retrieval failed: {e}")
            query_time = time.time() - start_time
            return RetrievalResult(
                items=[],
                source_type=self.source_type,
                query_time=query_time,
                total_candidates=0
            )
    
    def _retrieve_by_function_name(self, function_name: str, config: RetrievalConfig) -> List[ContextItem]:
        """根据函数名检索相关的调用关系
        
        Args:
            function_name: 函数名
            config: 检索配置
            
        Returns:
            上下文项列表
        """
        logger.info(f"根据函数名检索调用关系: {function_name}")
        
        try:
            # 获取函数节点
            function_node = self.graph_store.get_function_by_name(function_name)
            if not function_node:
                logger.warning(f"函数不存在: {function_name}")
                return []
            
            # 获取调用该函数的函数
            callers = self.graph_store.get_function_callers(function_name)
            
            # 获取该函数调用的函数
            callees = self.graph_store.get_function_callees(function_name)
            
            # 构建上下文项
            context_items = []
            
            # 添加函数本身的定义
            if function_node.get("code"):
                context_items.append(ContextItem(
                    content=function_node["code"],
                    source_type=self.source_type,
                    relevance_score=1.0,
                    metadata={
                        "function_name": function_name,
                        "file_path": function_node.get("file_path", ""),
                        "relation_type": "definition"
                    }
                ))
            
            # 添加调用者
            for caller in callers[:config.top_k // 2]:
                if caller.get("code"):
                    context_items.append(ContextItem(
                        content=caller["code"],
                        source_type=self.source_type,
                        relevance_score=0.8,
                        metadata={
                            "function_name": caller.get("name", ""),
                            "file_path": caller.get("file_path", ""),
                            "relation_type": "caller"
                        }
                    ))
            
            # 添加被调用者
            for callee in callees[:config.top_k // 2]:
                if callee.get("code"):
                    context_items.append(ContextItem(
                        content=callee["code"],
                        source_type=self.source_type,
                        relevance_score=0.7,
                        metadata={
                            "function_name": callee.get("name", ""),
                            "file_path": callee.get("file_path", ""),
                            "relation_type": "callee"
                        }
                    ))
            
            return context_items[:config.top_k]
            
        except Exception as e:
            logger.error(f"检索函数调用关系失败: {e}")
            return []
    
    def _retrieve_by_fuzzy_match(
        self, 
        query: str, 
        intent_analysis: IntentAnalysis, 
        config: RetrievalConfig
    ) -> List[ContextItem]:
        """基于模糊匹配检索调用关系
        
        当没有明确函数名时，尝试通过关键词匹配相关函数。
        
        Args:
            query: 原始查询
            intent_analysis: 意图分析结果
            config: 检索配置
            
        Returns:
            上下文项列表
        """
        context_items = []
        
        try:
            # 使用关键词搜索相关函数
            keywords = intent_analysis.keywords if intent_analysis.keywords else [query]
            
            for keyword in keywords:
                # 在Neo4j中搜索包含关键词的函数
                matching_functions = self._search_functions_by_keyword(keyword)
                
                for func_name in matching_functions[:3]:  # 限制每个关键词最多3个函数
                    # 获取函数信息
                    function_code = self._get_function_code(func_name)
                    if function_code:
                        context_items.append(ContextItem(
                            content=function_code,
                            source_type=self.source_type,
                            relevance_score=0.7,  # 模糊匹配给中等分数
                            metadata={
                                "function_name": func_name,
                                "relation_type": "keyword_match",
                                "matched_keyword": keyword
                            }
                        ))
                        
        except Exception as e:
            logger.warning(f"Fuzzy match retrieval failed: {e}")
        
        return context_items
    
    def _get_function_callers(self, function_name: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """获取函数的调用者"""
        try:
            # 构建Cypher查询
            query = """
            MATCH (caller:Function)-[:CALLS*1..{}]->(target:Function {{name: $function_name}})
            RETURN caller.name as caller_name, 
                   caller.file_path as caller_file,
                   caller.code as caller_code
            LIMIT 10
            """.format(max_depth)
            
            with self.graph_store.driver.session() as session:
                result = session.run(query, function_name=function_name)
                return [record.data() for record in result]
                
        except Exception as e:
            logger.error(f"Failed to get callers for {function_name}: {e}")
            return []
    
    def _get_function_callees(self, function_name: str, max_depth: int = 2) -> List[Dict[str, Any]]:
        """获取函数调用的其他函数"""
        try:
            query = """
            MATCH (target:Function {{name: $function_name}})-[:CALLS*1..{}]->(callee:Function)
            RETURN callee.name as callee_name,
                   callee.file_path as callee_file,
                   callee.code as callee_code
            LIMIT 10
            """.format(max_depth)
            
            with self.graph_store.driver.session() as session:
                result = session.run(query, function_name=function_name)
                return [record.data() for record in result]
                
        except Exception as e:
            logger.error(f"Failed to get callees for {function_name}: {e}")
            return []
    
    def _get_function_code(self, function_name: str) -> str:
        """获取函数的实现代码"""
        try:
            query = """
            MATCH (f:Function {name: $function_name})
            RETURN f.code as code, f.file_path as file_path
            LIMIT 1
            """
            
            with self.graph_store.driver.session() as session:
                result = session.run(query, function_name=function_name)
                record = result.single()
                if record:
                    return f"// Function: {function_name}\n// File: {record['file_path']}\n{record['code']}"
                    
        except Exception as e:
            logger.error(f"Failed to get code for {function_name}: {e}")
        
        return ""
    
    def _search_functions_by_keyword(self, keyword: str) -> List[str]:
        """通过关键词搜索函数"""
        try:
            query = """
            MATCH (f:Function)
            WHERE f.name CONTAINS $keyword OR f.code CONTAINS $keyword
            RETURN f.name as function_name
            LIMIT 10
            """
            
            with self.graph_store.driver.session() as session:
                result = session.run(query, keyword=keyword)
                return [record["function_name"] for record in result]
                
        except Exception as e:
            logger.error(f"Failed to search functions by keyword {keyword}: {e}")
            return []
    
    def _format_caller_info(self, function_name: str, callers: List[Dict[str, Any]]) -> str:
        """格式化调用者信息"""
        if not callers:
            return f"Function {function_name} has no callers found."
        
        info_lines = [f"Function {function_name} is called by:"]
        for caller in callers:
            caller_name = caller.get("caller_name", "unknown")
            caller_file = caller.get("caller_file", "unknown")
            info_lines.append(f"  - {caller_name} (in {caller_file})")
        
        return "\n".join(info_lines)
    
    def _format_callee_info(self, function_name: str, callees: List[Dict[str, Any]]) -> str:
        """格式化被调用者信息"""
        if not callees:
            return f"Function {function_name} calls no other functions."
        
        info_lines = [f"Function {function_name} calls:"]
        for callee in callees:
            callee_name = callee.get("callee_name", "unknown")
            callee_file = callee.get("callee_file", "unknown")
            info_lines.append(f"  - {callee_name} (in {callee_file})")
        
        return "\n".join(info_lines)
    
    def _looks_like_function(self, entity: str) -> bool:
        """判断实体是否像函数名"""
        return (
            entity and 
            entity.isidentifier() and 
            not entity.endswith('.c') and 
            not entity.endswith('.h')
        )
    
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
        """获取调用图统计信息"""
        try:
            with self.graph_store.driver.session() as session:
                # 获取函数总数
                func_count_result = session.run("MATCH (f:Function) RETURN count(f) as count")
                func_count = func_count_result.single()["count"]
                
                # 获取调用关系总数
                call_count_result = session.run("MATCH ()-[r:CALLS]->() RETURN count(r) as count")
                call_count = call_count_result.single()["count"]
                
                return {
                    "source_type": self.get_source_type(),
                    "available": True,
                    "function_count": func_count,
                    "call_relationship_count": call_count
                }
        except Exception as e:
            logger.error(f"Failed to get call graph statistics: {e}")
            return {
                "source_type": self.get_source_type(),
                "available": False,
                "error": str(e)
            } 