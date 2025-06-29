"""
重排序Prompt模板库

定义用于LLM重排序的各种prompt模板。
"""

from typing import Dict, List
from ..core.context_models import ContextItem


class PromptTemplates:
    """重排序Prompt模板集合"""
    
    @staticmethod
    def default_rerank_prompt(query: str, context_items: List[ContextItem]) -> str:
        """默认的重排序prompt
        
        Args:
            query: 用户查询
            context_items: 待重排序的上下文项
            
        Returns:
            格式化的prompt字符串
        """
        prompt_parts = [
            "You are an expert code analyst. Given a user query and a list of code contexts from different sources, ",
            "please rank them by relevance to the query. Consider the following factors:",
            "1. Direct relevance to the query topic",
            "2. Code quality and completeness", 
            "3. Contextual information value",
            "4. Source reliability (CALL_GRAPH > VECTOR > DEPENDENCY for function analysis)",
            "",
            f"User Query: {query}",
            "",
            "Code Contexts to rank:",
        ]
        
        # 添加每个上下文项
        for i, item in enumerate(context_items):
            source_tag = f"[{item.source_type.value.upper()}]"
            preview = item.content[:300] + "..." if len(item.content) > 300 else item.content
            prompt_parts.append(f"{i+1}. {source_tag} (Score: {item.relevance_score:.2f})")
            prompt_parts.append(f"   {preview}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Please provide the ranking as a comma-separated list of numbers (e.g., 3,1,5,2,4).",
            "Only return the numbers, no explanation needed.",
            "Ranking:"
        ])
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def function_analysis_prompt(query: str, context_items: List[ContextItem]) -> str:
        """函数分析专用的重排序prompt"""
        prompt_parts = [
            "You are analyzing C code functions. Rank the following contexts by their relevance to the query.",
            "Prioritize:",
            "1. Function implementation code (highest priority)",
            "2. Function call relationships and usage patterns", 
            "3. Related function dependencies",
            "4. Documentation and comments",
            "",
            f"Query: {query}",
            "",
            "Contexts:"
        ]
        
        for i, item in enumerate(context_items):
            relation_type = item.metadata.get("relation_type", "unknown")
            function_name = item.metadata.get("function_name", "")
            source_info = f"[{item.source_type.value.upper()}:{relation_type}]"
            
            if function_name:
                source_info += f" Function: {function_name}"
            
            preview = item.content[:200] + "..." if len(item.content) > 200 else item.content
            prompt_parts.append(f"{i+1}. {source_info}")
            prompt_parts.append(f"   {preview}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Rank by relevance (comma-separated numbers):",
        ])
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def dependency_analysis_prompt(query: str, context_items: List[ContextItem]) -> str:
        """依赖分析专用的重排序prompt"""
        prompt_parts = [
            "You are analyzing code dependencies and relationships. Rank contexts by dependency relevance.",
            "Focus on:",
            "1. Direct dependency relationships",
            "2. Include/import statements",
            "3. Module interactions",
            "4. Build and compilation dependencies",
            "",
            f"Query: {query}",
            "",
            "Dependency Contexts:"
        ]
        
        for i, item in enumerate(context_items):
            source_info = f"[{item.source_type.value.upper()}]"
            file_path = item.metadata.get("file_path", "")
            
            if file_path:
                source_info += f" File: {file_path}"
            
            preview = item.content[:250] + "..." if len(item.content) > 250 else item.content
            prompt_parts.append(f"{i+1}. {source_info}")
            prompt_parts.append(f"   {preview}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Rank by dependency relevance:",
        ])
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def debugging_prompt(query: str, context_items: List[ContextItem]) -> str:
        """调试问题专用的重排序prompt"""
        prompt_parts = [
            "You are helping debug C code issues. Rank contexts by their potential to help solve the problem.",
            "Prioritize:",
            "1. Error-prone code patterns",
            "2. Function implementations that might contain bugs",
            "3. Related function calls and dependencies",
            "4. Similar code patterns that work correctly",
            "",
            f"Debug Query: {query}",
            "",
            "Code Contexts for debugging:"
        ]
        
        for i, item in enumerate(context_items):
            source_info = f"[{item.source_type.value.upper()}]"
            function_name = item.metadata.get("function_name", "")
            
            if function_name:
                source_info += f" Function: {function_name}"
            
            preview = item.content[:300] + "..." if len(item.content) > 300 else item.content
            prompt_parts.append(f"{i+1}. {source_info} (Confidence: {item.relevance_score:.2f})")
            prompt_parts.append(f"   {preview}")
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Rank by debugging relevance:",
        ])
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def get_template_by_intent(intent_type: str) -> callable:
        """根据意图类型获取对应的prompt模板
        
        Args:
            intent_type: 意图类型
            
        Returns:
            对应的prompt模板函数
        """
        template_map = {
            "function_analysis": PromptTemplates.function_analysis_prompt,
            "dependency_check": PromptTemplates.dependency_analysis_prompt,
            "error_debugging": PromptTemplates.debugging_prompt,
            "default": PromptTemplates.default_rerank_prompt
        }
        
        return template_map.get(intent_type, PromptTemplates.default_rerank_prompt)
    
    @staticmethod
    def build_context_summary(context_items: List[ContextItem]) -> str:
        """构建上下文摘要信息
        
        用于在prompt中提供上下文的统计信息。
        
        Args:
            context_items: 上下文项列表
            
        Returns:
            上下文摘要字符串
        """
        if not context_items:
            return "No contexts available."
        
        # 统计各种源类型的数量
        source_counts = {}
        total_length = 0
        
        for item in context_items:
            source_type = item.source_type.value
            source_counts[source_type] = source_counts.get(source_type, 0) + 1
            total_length += len(item.content)
        
        summary_parts = [
            f"Total contexts: {len(context_items)}",
            f"Total content length: {total_length} characters",
            "Source distribution:"
        ]
        
        for source_type, count in source_counts.items():
            summary_parts.append(f"  - {source_type.upper()}: {count}")
        
        return "\n".join(summary_parts) 