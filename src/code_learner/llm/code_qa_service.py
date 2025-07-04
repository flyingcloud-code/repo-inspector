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
from ..config.config_manager import ConfigManager
from ..config.prompt_templates import TEMPLATES
from ..core.context_models import ContextItem
from ..llm.chatbot import OpenRouterChatBot
from ..rerank.llm_reranker import LLMReranker

logger = get_logger(__name__)


class CodeQAService:
    """代码问答服务
    
    结合Neo4j图数据库和Chroma向量数据库，提供智能的代码问答功能
    """
    
    def __init__(self, project_id: str, verbose_rag: bool = False):
        """初始化代码问答服务
        
        Args:
            project_id: 项目ID，用于数据隔离
            verbose_rag: 是否启用详细的RAG检索日志
        """
        self.project_id = project_id
        self.verbose_rag = verbose_rag
        from ..retrieval.multi_source_builder import MultiSourceContextBuilder

        self.config = ConfigManager()
        self.chatbot = OpenRouterChatBot()
        self.intent_analyzer = IntentAnalyzer(self.chatbot)
        self.reranker = LLMReranker()
        self.context_builder = MultiSourceContextBuilder(project_id=project_id, reranker=self.reranker)
        self.logger = get_logger(__name__)
        self.logger.info(f"CodeQAService initialized for project {project_id}.")
    
    def ask_question(self, question: str) -> Dict[str, Any]:
        """询问代码相关问题
        
        Args:
            question: 用户问题
            
        Returns:
            Dict[str, Any]: 回答内容
        """
        try:
            self.logger.info(f"收到代码问题: {question}")
            
            # 确保所有服务已初始化
            self._ensure_services_initialized()
            
            # 使用意图分析器分析问题
            self.logger.info("使用意图分析器分析用户问题...")
            intent_analysis = self.intent_analyzer.analyze_question(question, None)
            self.logger.info(f"意图分析结果: {intent_analysis}")
            
            # 构建增强的代码上下文
            self.logger.info("构建代码上下文...")
            code_context = self._build_enhanced_code_context(question, None, intent_analysis)
            
            # 记录上下文来源
            context_sources = []
            if intent_analysis.get("functions"):
                context_sources.append(f"检测到函数: {', '.join(intent_analysis['functions'])}")
            if intent_analysis.get("files"):
                context_sources.append(f"检测到文件: {', '.join(intent_analysis['files'])}")
            
            self.logger.info(f"上下文来源: {'; '.join(context_sources) if context_sources else '向量检索'}")
            
            # 调用LLM生成回答
            self.logger.info("调用LLM生成回答...")
            answer = self._generate_answer(question, code_context, intent_analysis)
            
            self.logger.info("问题回答完成")
            return {"answer": answer}
            
        except Exception as e:
            self.logger.error(f"问答过程中出错: {e}", exc_info=True)
            return {"error": f"抱歉，在处理您的问题时遇到了错误: {str(e)}"}
    
    def _ensure_services_initialized(self):
        """确保所有服务都已初始化"""
        if not self.context_builder.reranker:
            self.context_builder.reranker = self.reranker
        
        if not self.chatbot:
            self.chatbot = self.chatbot
    
    def _build_enhanced_code_context(self, question: str, context: Optional[dict], 
                                 intent_analysis: Dict[str, Any]) -> str:
        """构建增强代码上下文
        
        使用多源检索系统获取更全面的代码上下文
        
        Args:
            question: 用户问题
            context: 可选的上下文信息
            intent_analysis: 意图分析结果
            
        Returns:
            str: 增强的代码上下文
        """
        self.logger.info("构建代码上下文...")
        
        # 如果没有提供上下文，创建一个空的
        if context is None:
            context = {}
        
        # 初始化上下文字符串
        code_context = ""
        
        try:
            # 使用多源检索系统
            self.logger.info("使用多源检索系统获取上下文...")
            
            # 获取多源上下文
            # 从配置管理器获取final_top_k
            final_top_k = self.config.get_config().enhanced_query.final_top_k
            self.logger.info(f"从配置获取final_top_k={final_top_k}")
            
            # 执行多源检索
            rerank_result = self.context_builder.build_context(
                query=question,
                intent=intent_analysis,
                verbose=self.verbose_rag
            )
            
            # 将结果格式化为字符串
            if rerank_result:
                code_context += "## 多源检索结果\n\n"
                self.logger.info(f"多源检索找到 {len(rerank_result)} 个相关代码片段")
                
                for i, item in enumerate(rerank_result):
                    # 添加分隔符
                    if i > 0:
                        code_context += "\n---\n\n"
                    
                    # 添加元数据信息
                    metadata = item.metadata or {}
                    file_path = metadata.get("file_path", "Unknown")
                    function_name = metadata.get("function_name", "")
                    relation_type = metadata.get("relation_type", "")
                    source_info = item.source  # 直接使用source字符串
                    
                    # 构建标题
                    title = f"### 代码片段 {i+1}"
                    if function_name:
                        title += f": 函数 `{function_name}`"
                    if relation_type:
                        title += f" ({relation_type})"
                    
                    code_context += f"{title}\n"
                    code_context += f"文件: {file_path}\n"
                    code_context += f"来源: {source_info}, 相关度: {item.score:.3f}\n\n"
                    
                    # 添加代码内容
                    if item.content.strip().startswith("```") or item.content.strip().endswith("```"):
                        # 已经有代码块标记
                        code_context += f"{item.content}\n"
                    else:
                        # 添加代码块标记
                        code_context += f"```c\n{item.content}\n```\n"
            else:
                self.logger.warning("多源检索未返回结果或返回空列表")
                
                # 尝试直接使用向量检索作为备选
                self.logger.info("回退到向量检索...")
                code_context += self._get_enhanced_vector_context(question, intent_analysis, top_k=final_top_k)
                
        except Exception as e:
            self.logger.error(f"构建增强代码上下文失败: {e}", exc_info=True)
            
            # 出错时也尝试使用向量检索作为备选
            self.logger.info("发生错误，回退到向量检索...")
            code_context += self._get_enhanced_vector_context(question, intent_analysis)
        
        return code_context
    
    def _get_enhanced_vector_context(self, question: str, intent_analysis: Dict[str, Any], top_k: int = 5) -> str:
        """使用向量检索获取增强上下文
        
        当多源检索失败时的备选方案
        
        Args:
            question: 用户问题
            intent_analysis: 意图分析结果
            top_k: 返回结果数量
            
        Returns:
            str: 向量检索上下文
        """
        self.logger.info(f"向量检索查询: {question}")
        
        try:
            # 确保向量检索器可用
            if not self.context_builder.vector_retriever or not self.context_builder.vector_retriever.is_available():
                self.logger.warning("向量检索器未初始化或不可用")
                return ""

            # 使用向量检索器进行检索
            results = self.context_builder.vector_retriever.retrieve(question, intent_analysis)
            
            # 限制结果数量
            unique_results = results[:top_k]
            
            self.logger.info(f"向量检索找到 {len(unique_results)} 个相关代码片段")
            
            # 格式化结果
            if not unique_results:
                return ""
            
            context = "## 向量检索结果 (备用方案)\n\n"
            
            for i, item in enumerate(unique_results):
                # 添加分隔符
                if i > 0:
                    context += "\n---\n\n"
                
                # 提取元数据
                metadata = item.metadata or {}
                file_path = metadata.get("file_path", "未知文件")
                function_name = metadata.get("function_name", "")
                
                # 构建标题
                title = f"### 代码片段 {i+1}"
                if function_name:
                    title += f": 函数 `{function_name}`"
                
                context += f"{title}\n"
                context += f"文件: {file_path}\n"
                context += f"来源: {item.source}, 相关度: {item.score:.3f}\n\n"
                
                # 添加代码内容
                if item.content.strip().startswith("```") or item.content.strip().endswith("```"):
                    context += f"{item.content}\n"
                else:
                    context += f"```c\n{item.content}\n```\n"
            
            return context
            
        except Exception as e:
            self.logger.error(f"向量检索失败: {e}", exc_info=True)
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
        
        # 确保函数名相关查询优先返回
        function_queries = [q for q in unique_queries if any(func in q for func in intent_analysis.get("functions", []))]
        other_queries = [q for q in unique_queries if q not in function_queries]
        
        # 组合并限制返回5个查询
        prioritized_queries = function_queries + other_queries
        return prioritized_queries[:5]  # 增加到5个查询以提高召回率
    
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
        self.logger.info("开始从Neo4j获取上下文...")
        
        if not self.context_builder.graph_store:
            self.logger.warning("Neo4j图存储未初始化，跳过Neo4j查询")
            return ""
        
        functions = intent_analysis.get("functions", [])
        self.logger.info(f"从意图分析中提取的函数列表: {functions}")
        
        if not functions:
            self.logger.info("没有检测到函数，跳过Neo4j查询")
            return ""
        
        context_parts = []
        
        # 获取意图分析识别的函数信息
        for func_name in functions:
            self.logger.info(f"正在从Neo4j查询函数: {func_name}")
            func_info = self._get_function_context(func_name)
            if func_info:
                self.logger.info(f"成功从Neo4j获取函数 {func_name} 的信息，长度: {len(func_info)} 字符")
                context_parts.append(f"### 函数: {func_name}\n{func_info}")
            else:
                self.logger.warning(f"未能从Neo4j获取函数 {func_name} 的信息")
        
        result = "\n\n".join(context_parts)
        self.logger.info(f"Neo4j上下文构建完成，总长度: {len(result)} 字符")
        return result
    
    def _get_call_relationship_context(self, function_names: List[str]) -> str:
        """获取函数调用关系上下文
        
        Args:
            function_names: 函数名列表
            
        Returns:
            str: 调用关系上下文
        """
        if not self.context_builder.graph_store or not function_names:
            return ""
        
        context_parts = []
        
        for func_name in function_names:
            try:
                # 查询调用关系
                callers = self.context_builder.graph_store.query_function_callers(func_name)
                callees = self.context_builder.graph_store.query_function_calls(func_name)
                
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
                self.logger.warning(f"查询函数 {func_name} 的调用关系失败: {e}")
        
        return "\n\n".join(context_parts)
    
    def _get_function_context(self, function_name: str) -> str:
        """获取函数上下文信息
        
        Args:
            function_name: 函数名
            
        Returns:
            str: 函数上下文
        """
        self.logger.info(f"开始获取函数 {function_name} 的上下文...")
        
        if not self.context_builder.graph_store:
            self.logger.warning("Neo4j图存储未初始化")
            return ""
        
        try:
            self.logger.info(f"调用Neo4j查询函数代码: {function_name}")
            # 从Neo4j获取函数代码
            function_code = self.context_builder.graph_store.get_function_code(function_name)
            
            if function_code:
                self.logger.info(f"成功获取函数 {function_name} 的代码，长度: {len(function_code)} 字符")
                return f"```c\n{function_code}\n```"
            else:
                self.logger.warning(f"函数 '{function_name}' 未找到")
                return ""
                
        except Exception as e:
            self.logger.error(f"获取函数 {function_name} 上下文失败: {e}", exc_info=True)
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
            self.logger.error(f"获取文件 {file_path} 上下文失败: {e}")
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
            self.logger.error(f"生成回答失败: {e}")
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
 