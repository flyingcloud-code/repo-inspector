#!/usr/bin/env python3
"""
多源检索系统测试脚本
"""

import sys
import logging
from pathlib import Path

from src.code_learner.llm.service_factory import ServiceFactory
from src.code_learner.retrieval.vector_retriever import VectorContextRetriever
from src.code_learner.retrieval.call_graph_retriever import CallGraphContextRetriever
from src.code_learner.retrieval.dependency_retriever import DependencyContextRetriever
from src.code_learner.retrieval.multi_source_builder import MultiSourceContextBuilder
from src.code_learner.rerank.llm_reranker import LLMReranker
from src.code_learner.llm.intent_analyzer import IntentAnalyzer
from src.code_learner.core.context_models import IntentAnalysis, IntentType
from src.code_learner.storage.neo4j_store import Neo4jGraphStore

# 设置日志级别
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python test_multi_source_retrieval_cli.py <函数名> [项目ID]")
        return 1
    
    function_name = sys.argv[1]
    # 如果提供了项目ID，则使用它
    project_id = sys.argv[2] if len(sys.argv) > 2 else "auto_086e94dd"
    
    print(f"正在查询函数: {function_name} (项目ID: {project_id})")
    
    # 创建服务，使用指定的项目ID
    service_factory = ServiceFactory()
    graph_store = Neo4jGraphStore(project_id=project_id)
    graph_store.connect()  # 确保连接到Neo4j
    
    vector_store = service_factory.get_vector_store()
    chatbot = service_factory.get_chatbot()
    embedding_engine = service_factory.get_embedding_engine()
    
    # 创建检索器
    vector_retriever = VectorContextRetriever(vector_store)
    vector_retriever.configure_embedding_engine(embedding_engine)
    call_graph_retriever = CallGraphContextRetriever(graph_store)
    dependency_retriever = DependencyContextRetriever(graph_store)
    
    # 创建重排序器和意图分析器
    reranker = LLMReranker(chatbot)
    intent_analyzer = IntentAnalyzer(chatbot)
    
    # 创建多源构建器
    builder = MultiSourceContextBuilder(
        vector_retriever=vector_retriever,
        call_graph_retriever=call_graph_retriever,
        dependency_retriever=dependency_retriever,
        reranker=reranker,
        intent_analyzer=intent_analyzer
    )
    
    # 手动创建意图分析结果
    query = f"what is {function_name} function?"
    intent = IntentAnalysis(
        intent_type=IntentType.FUNCTION_QUERY,
        entities=[{"name": function_name, "type": "function"}],
        confidence=0.9
    )
    
    # 执行多源检索
    print("正在执行多源检索...")
    result = builder.build_context(query, intent)
    
    # 输出结果
    print(f"\n检索到 {len(result.items)} 个上下文项")
    print(f"重排序置信度: {result.confidence}")
    
    # 显示检索结果
    for i, item in enumerate(result.items):
        print(f"\n--- 结果 {i+1} ({item.source_type}) 相关度: {item.relevance_score:.2f} ---")
        
        # 显示元数据
        if item.metadata:
            if "file_path" in item.metadata:
                print(f"文件: {item.metadata['file_path']}")
            if "function_name" in item.metadata:
                print(f"函数: {item.metadata['function_name']}")
            if "start_line" in item.metadata and "end_line" in item.metadata:
                print(f"行: {item.metadata['start_line']}-{item.metadata['end_line']}")
        
        # 显示内容（限制长度）
        content_preview = item.content[:500] + "..." if len(item.content) > 500 else item.content
        print(f"\n{content_preview}\n")
    
    # 关闭连接
    graph_store.close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 