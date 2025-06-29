"""
代码问答服务

提供智能的代码理解和问答功能，结合图数据库和向量数据库
"""

import logging
import re
from typing import List, Dict, Any, Optional
from ..core.interfaces import IEmbeddingEngine, IVectorStore, IGraphStore, IChatBot
from ..llm.service_factory import ServiceFactory
from ..utils.logger import get_logger
from .intent_analyzer import IntentAnalyzer
from ..retrieval.vector_retriever import VectorContextRetriever
from ..retrieval.call_graph_retriever import CallGraphContextRetriever
from ..retrieval.dependency_retriever import DependencyContextRetriever
from ..retrieval.multi_source_builder import MultiSourceContextBuilder
from ..rerank.llm_reranker import LLMReranker
from ..core.context_models import IntentAnalysis, RetrievalConfig

logger = get_logger(__name__)


class CodeQAService:
    """代码问答服务
    
    结合Neo4j图数据库和Chroma向量数据库，提供智能的代码问答功能
    """
    
    def __init__(self, project_id: str = None):
        """初始化代码问答服务
        
        Args:
            project_id: 项目ID，用于项目隔离
        """
        self.project_id = project_id
        
        # 延迟初始化各个组件
        self.embedding_engine: Optional[IEmbeddingEngine] = None
        self.vector_store: Optional[IVectorStore] = None
        self.graph_store: Optional[IGraphStore] = None
        self.chatbot: Optional[IChatBot] = None
        self.intent_analyzer: Optional[IntentAnalyzer] = None
        
        logger.info(f"代码问答服务初始化，项目ID: {project_id}")
    
    def _ensure_services_initialized(self):
        """确保所有服务都已初始化"""
        if not self.embedding_engine:
            self.embedding_engine = ServiceFactory.get_embedding_engine()
        
        if not self.vector_store:
            factory = ServiceFactory()
            self.vector_store = factory.create_vector_store(project_id=self.project_id)
        
        if not self.graph_store:
            self.graph_store = ServiceFactory.get_graph_store(project_id=self.project_id)
        
        if not self.chatbot:
            self.chatbot = ServiceFactory.get_chatbot()
        
        if not self.intent_analyzer:
            self.intent_analyzer = IntentAnalyzer(self.chatbot)
    
    def ask_question(self, question: str, context: Optional[dict] = None) -> str:
        """询问代码相关问题
        
        Args:
            question: 用户问题
            context: 上下文信息，包含project_path, focus_function, focus_file
            
        Returns:
            str: 回答内容
        """
        try:
            logger.info(f"收到代码问题: {question}")
            
            # 确保所有服务已初始化
            self._ensure_services_initialized()
            
            # 使用意图分析器分析问题
            logger.info("使用意图分析器分析用户问题...")
            intent_analysis = self.intent_analyzer.analyze_question(question, context)
            logger.info(f"意图分析结果: {intent_analysis}")
            
            # 构建增强的代码上下文
            logger.info("构建代码上下文...")
            code_context = self._build_enhanced_code_context(question, context, intent_analysis)
            
            # 记录上下文来源
            context_sources = []
            if context and context.get("focus_function"):
                context_sources.append(f"指定函数: {context['focus_function']}")
            if context and context.get("focus_file"):
                context_sources.append(f"指定文件: {context['focus_file']}")
            
            # 从意图分析中获取的信息
            if intent_analysis.get("functions"):
                context_sources.append(f"检测到函数: {', '.join(intent_analysis['functions'])}")
            if intent_analysis.get("files"):
                context_sources.append(f"检测到文件: {', '.join(intent_analysis['files'])}")
            
            logger.info(f"上下文来源: {'; '.join(context_sources) if context_sources else '向量检索'}")
            
            # 调用LLM生成回答
            logger.info("调用LLM生成回答...")
            answer = self._generate_answer(question, code_context, intent_analysis)
            
            logger.info("问题回答完成")
            return answer
            
        except Exception as e:
            logger.error(f"问答过程中出错: {e}", exc_info=True)
            return f"抱歉，在处理您的问题时遇到了错误: {str(e)}"
    
    def _build_enhanced_code_context(self, question: str, context: Optional[dict], 
                                     intent_analysis: Dict[str, Any]) -> str:
        """构建增强的代码上下文
        
        Args:
            question: 用户问题
            context: 上下文信息
            intent_analysis: 意图分析结果
            
        Returns:
            str: 代码上下文
        """
        code_context = ""
        
        # 1. 处理明确指定的函数或文件
        if context and context.get("focus_function"):
            function_context = self._get_function_context(context["focus_function"])
            if function_context:
                code_context += f"## 指定函数信息\n{function_context}\n\n"
        
        if context and context.get("focus_file"):
            file_context = self._get_file_context(context["focus_file"])
            if file_context:
                code_context += f"## 指定文件信息\n{file_context}\n\n"
        
        # 2. 使用多源检索系统获取上下文
        try:
            logger.info("使用多源检索系统获取上下文...")
            
            # 确保所有服务已初始化
            self._ensure_services_initialized()
            
            # 创建检索器
            vector_retriever = VectorContextRetriever(
                vector_store=self.vector_store,
                embedding_engine=self.embedding_engine
            )
            
            call_graph_retriever = CallGraphContextRetriever(
                graph_store=self.graph_store
            )
            
            dependency_retriever = DependencyContextRetriever(
                graph_store=self.graph_store
            )
            
            # 创建重排序器
            reranker = LLMReranker(
                chatbot=self.chatbot
            )
            
            # 创建多源构建器
            builder = MultiSourceContextBuilder(
                vector_retriever=vector_retriever,
                call_graph_retriever=call_graph_retriever,
                dependency_retriever=dependency_retriever,
                reranker=reranker,
                intent_analyzer=self.intent_analyzer
            )
            
            # 转换意图分析格式
            intent = IntentAnalysis(
                entities=intent_analysis.get("functions", []) + intent_analysis.get("files", []),
                intent_type=intent_analysis.get("intent_type", "general_question"),
                keywords=intent_analysis.get("keywords", []) + intent_analysis.get("search_terms", []),
                confidence=0.8
            )
            
            # 获取多源上下文
            retrieval_config = RetrievalConfig(
                final_top_k=5,
                sources={
                    "vector": {"top_k": 5, "enable": True},
                    "call_graph": {"top_k": 5, "enable": True},
                    "dependency": {"top_k": 5, "enable": True}
                }
            )
            
            # 根据意图类型调整配置
            if intent.intent_type == "function_analysis":
                retrieval_config.sources["call_graph"]["top_k"] = 8
            elif intent.intent_type == "call_relationship":
                retrieval_config.sources["call_graph"]["top_k"] = 10
                retrieval_config.sources["vector"]["top_k"] = 3
            elif intent.intent_type == "file_analysis":
                retrieval_config.sources["dependency"]["top_k"] = 8
            
            # 执行多源检索
            context_items = builder.build_context(question, intent, retrieval_config)
            
            # 将结果格式化为字符串
            if context_items:
                code_context += "## 多源检索结果\n\n"
                
                for i, item in enumerate(context_items):
                    # 添加来源标识
                    source_tag = f"[{item.source_type}]" if item.source_type else ""
                    
                    # 添加元数据信息
                    meta_info = []
                    if item.metadata:
                        if "file_path" in item.metadata:
                            meta_info.append(f"文件: {item.metadata['file_path']}")
                        if "function_name" in item.metadata:
                            meta_info.append(f"函数: {item.metadata['function_name']}")
                        if "start_line" in item.metadata and "end_line" in item.metadata:
                            meta_info.append(f"行: {item.metadata['start_line']}-{item.metadata['end_line']}")
                    
                    meta_str = f" ({', '.join(meta_info)})" if meta_info else ""
                    
                    # 添加内容
                    code_context += f"### 片段 {i+1} {source_tag}{meta_str}\n```\n{item.content}\n```\n\n"
                
                logger.info(f"多源检索成功，获取到 {len(context_items)} 个上下文片段")
            else:
                logger.warning("多源检索未返回结果")
                
                # 回退到传统向量检索
                vector_context = self._get_enhanced_vector_context(question, intent_analysis)
                if vector_context:
                    code_context += vector_context
                
        except Exception as e:
            logger.error(f"多源检索失败: {e}", exc_info=True)
            
            # 回退到传统向量检索
            vector_context = self._get_enhanced_vector_context(question, intent_analysis)
            if vector_context:
                code_context += vector_context
            
            # 回退到Neo4j检索
            neo4j_context = self._get_neo4j_context_from_intent(intent_analysis)
            if neo4j_context:
                code_context += neo4j_context
        
        # 如果没有获取到任何上下文，添加一个提示
        if not code_context.strip():
            code_context = "未找到相关代码上下文。请尝试提供更具体的问题或指定函数/文件名。"
            logger.warning("未找到相关代码上下文")
        
        return code_context
    
    def _get_enhanced_vector_context(self, question: str, intent_analysis: Dict[str, Any], top_k: int = 5) -> str:
        """获取增强的向量上下文
        
        Args:
            question: 问题文本
            intent_analysis: 意图分析结果
            top_k: 返回结果数量
            
        Returns:
            str: 向量上下文
        """
        # 延迟加载嵌入引擎
        if not self.embedding_engine:
            self.embedding_engine = ServiceFactory.get_embedding_engine()
            if not self.embedding_engine.model:
                self.embedding_engine.load_model("jinaai/jina-embeddings-v2-base-code")
        
        # 检查向量存储是否已初始化
        if not self.vector_store or not self.vector_store.client:
            logger.warning("向量存储未初始化，跳过向量检索")
            return ""
        
        try:
            # 构建更智能的查询
            search_queries = self._build_search_queries(question, intent_analysis)
            
            all_results = []
            for query in search_queries:
                logger.info(f"向量检索查询: {query}")
                
                # 生成查询嵌入向量
                query_embedding = self.embedding_engine.encode_text(query)
                if query_embedding is None:
                    continue
                
                # 确保嵌入向量是list格式
                if hasattr(query_embedding, 'tolist'):
                    query_vector = query_embedding.tolist()
                else:
                    query_vector = list(query_embedding)
                
                # 执行向量查询
                results = self.vector_store.query_embeddings(
                    query_vector=query_vector,
                    n_results=top_k // len(search_queries) + 1,
                collection_name="code_embeddings"
            )
                
                all_results.extend(results)
            
            # 去重并按相似度排序
            unique_results = self._deduplicate_results(all_results)
            top_results = sorted(unique_results, key=lambda x: x.get('distance', 1.0))[:top_k]
            
            if not top_results:
                logger.warning("向量检索未找到相关结果")
                return ""
            
            # 构建上下文
            context_parts = []
            for i, result in enumerate(top_results):
                metadata = result.get('metadata', {})
                document = result.get('document', '')
                distance = result.get('distance', 1.0)
                
                context_part = f"### 代码片段 {i+1} (相似度: {1-distance:.3f})\n"
                
                # 添加元数据信息
                if metadata.get('function_name'):
                    context_part += f"**函数**: {metadata['function_name']}\n"
                if metadata.get('file_path'):
                    context_part += f"**文件**: {metadata['file_path']}\n"
                if metadata.get('chunk_type'):
                    context_part += f"**类型**: {metadata['chunk_type']}\n"
                
                context_part += f"**代码**:\n```c\n{document}\n```\n"
                context_parts.append(context_part)
            
            logger.info(f"向量检索找到 {len(top_results)} 个相关代码片段")
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return ""
    
    def _build_search_queries(self, question: str, intent_analysis: Dict[str, Any]) -> List[str]:
        """构建搜索查询列表
        
        Args:
            question: 原始问题
            intent_analysis: 意图分析结果
            
        Returns:
            List[str]: 搜索查询列表
        """
        queries = []
        
        # 1. 原始问题
        queries.append(question)
        
        # 2. 基于函数名的查询
        for func_name in intent_analysis.get("functions", []):
            queries.append(f"{func_name} function implementation")
            queries.append(f"{func_name} definition")
        
        # 3. 基于关键词的查询
        keywords = intent_analysis.get("keywords", [])
        if keywords:
            queries.append(" ".join(keywords))
        
        # 4. 基于搜索词的查询
        search_terms = intent_analysis.get("search_terms", [])
        if search_terms:
            queries.append(" ".join(search_terms))
        
        # 5. 基于意图类型的特定查询
        intent_type = intent_analysis.get("intent_type", "")
        if intent_type == "call_relationship":
            for func_name in intent_analysis.get("functions", []):
                queries.append(f"function calls {func_name}")
                queries.append(f"{func_name} caller")
        elif intent_type == "function_analysis":
            for func_name in intent_analysis.get("functions", []):
                queries.append(f"{func_name} function purpose")
                queries.append(f"what does {func_name} do")
        
        # 去重并限制数量
        unique_queries = list(dict.fromkeys(queries))  # 保持顺序的去重
        return unique_queries[:3]  # 限制查询数量避免过度检索
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重检索结果
        
        Args:
            results: 检索结果列表
            
        Returns:
            List[Dict[str, Any]]: 去重后的结果
        """
        seen_documents = set()
        unique_results = []
        
        for result in results:
            document = result.get('document', '')
            # 使用文档内容的前100个字符作为去重标识
            doc_key = document[:100] if document else ''
            
            if doc_key not in seen_documents:
                seen_documents.add(doc_key)
                unique_results.append(result)
        
        return unique_results
    
    def _get_neo4j_context_from_intent(self, intent_analysis: Dict[str, Any]) -> str:
        """从意图分析结果获取Neo4j上下文
        
        Args:
            intent_analysis: 意图分析结果
            
        Returns:
            str: Neo4j上下文
        """
        logger.info("开始从Neo4j获取上下文...")
        
        if not self.graph_store:
            logger.warning("Neo4j图存储未初始化，跳过Neo4j查询")
            return ""
        
        functions = intent_analysis.get("functions", [])
        logger.info(f"从意图分析中提取的函数列表: {functions}")
        
        if not functions:
            logger.info("没有检测到函数，跳过Neo4j查询")
            return ""
        
        context_parts = []
        
        # 获取意图分析识别的函数信息
        for func_name in functions:
            logger.info(f"正在从Neo4j查询函数: {func_name}")
            func_info = self._get_function_context(func_name)
            if func_info:
                logger.info(f"成功从Neo4j获取函数 {func_name} 的信息，长度: {len(func_info)} 字符")
                context_parts.append(f"### 函数: {func_name}\n{func_info}")
            else:
                logger.warning(f"未能从Neo4j获取函数 {func_name} 的信息")
        
        result = "\n\n".join(context_parts)
        logger.info(f"Neo4j上下文构建完成，总长度: {len(result)} 字符")
        return result
    
    def _get_call_relationship_context(self, function_names: List[str]) -> str:
        """获取函数调用关系上下文
        
        Args:
            function_names: 函数名列表
            
        Returns:
            str: 调用关系上下文
        """
        if not self.graph_store or not function_names:
            return ""
        
        context_parts = []
        
        for func_name in function_names:
            try:
                # 查询调用关系
                callers = self.graph_store.query_function_callers(func_name)
                callees = self.graph_store.query_function_calls(func_name)
                
                if callers or callees:
                    context_part = f"### {func_name} 调用关系\n"
                    
                    if callers:
                        caller_names = [caller.get('caller_name', 'unknown') for caller in callers]
                        context_part += f"**被以下函数调用**: {', '.join(caller_names)}\n"
                    
                    if callees:
                        callee_names = [callee.get('callee_name', 'unknown') for callee in callees]
                        context_part += f"**调用以下函数**: {', '.join(callee_names)}\n"
                    
                    context_parts.append(context_part)
                    
            except Exception as e:
                logger.warning(f"查询函数 {func_name} 的调用关系失败: {e}")
        
        return "\n\n".join(context_parts)
    
    def _get_function_context(self, function_name: str) -> str:
        """获取函数上下文信息
        
        Args:
            function_name: 函数名
            
        Returns:
            str: 函数上下文
        """
        logger.info(f"开始获取函数 {function_name} 的上下文...")
        
        if not self.graph_store:
            logger.warning("Neo4j图存储未初始化")
            return ""
        
        try:
            logger.info(f"调用Neo4j查询函数代码: {function_name}")
            # 从Neo4j获取函数代码
            function_code = self.graph_store.get_function_code(function_name)
            
            if function_code:
                logger.info(f"成功获取函数 {function_name} 的代码，长度: {len(function_code)} 字符")
                return f"```c\n{function_code}\n```"
            else:
                logger.warning(f"函数 '{function_name}' 未找到")
                return ""
                
        except Exception as e:
            logger.error(f"获取函数 {function_name} 上下文失败: {e}", exc_info=True)
            return ""
    
    def _get_file_context(self, file_path: str) -> str:
        """获取文件上下文信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件上下文
        """
        try:
            # 这里可以实现文件内容读取逻辑
            # 暂时返回空字符串
            return ""
        except Exception as e:
            logger.error(f"获取文件 {file_path} 上下文失败: {e}")
            return ""
    
    def _generate_answer(self, question: str, code_context: str, intent_analysis: Dict[str, Any]) -> str:
        """生成回答
        
        Args:
            question: 用户问题
            code_context: 代码上下文
            intent_analysis: 意图分析结果
            
        Returns:
            str: 生成的回答
        """
        try:
            # 构建专门的问答提示
            system_prompt = self._build_qa_system_prompt(intent_analysis)
            
            # 构建用户提示
            user_prompt = f"""请基于提供的代码上下文回答以下问题：

{question}

请提供详细、准确的回答，包括：
1. 直接回答用户的问题
2. 相关的代码解释
3. 如果涉及函数调用关系，请说明调用链
4. 如果有潜在问题或改进建议，请指出

回答要求：
- 使用中文回答
- 保持技术准确性
- 提供具体的代码示例
- 结构清晰，易于理解
"""
            
                         # 调用LLM
            response = self.chatbot.ask_question(user_prompt, code_context)
            
            return response.content if response and response.content else "抱歉，无法生成回答。"
            
        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            return f"生成回答时出错: {str(e)}"
    
    def _build_qa_system_prompt(self, intent_analysis: Dict[str, Any]) -> str:
        """构建问答系统提示
        
        Args:
            intent_analysis: 意图分析结果
            
        Returns:
            str: 系统提示
        """
        intent_type = intent_analysis.get("intent_type", "general_question")
        
        base_prompt = """你是一个专业的C语言代码分析专家，专门帮助开发者理解OpenSBI等系统级代码。"""
        
        if intent_type == "function_analysis":
            return base_prompt + """
你的任务是分析函数的功能、参数、返回值和实现逻辑。
请详细解释函数的作用、工作原理，以及在系统中的重要性。
"""
        elif intent_type == "call_relationship":
            return base_prompt + """
你的任务是分析函数之间的调用关系。
请说明哪些函数调用了目标函数，目标函数又调用了哪些函数，以及整个调用链的作用。
"""
        elif intent_type == "file_analysis":
            return base_prompt + """
你的任务是分析文件的结构和功能。
请说明文件的作用、包含的主要函数和数据结构。
"""
        else:
            return base_prompt + """
请根据用户的问题和提供的代码上下文，给出准确、详细的回答。
"""
 