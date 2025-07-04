"""
LLM重排序器实现

基于大语言模型的智能重排序功能。
"""

import time
import re
import logging
import json
from typing import List, Dict, Any, Optional
from ..core.context_models import (
    ContextItem, 
    RerankResult
)
from ..core.retriever_interfaces import IReranker
from ..llm.chatbot import OpenRouterChatBot
from .prompt_templates import PromptTemplates
from ..config.config_manager import ConfigManager
from ..config.prompt_templates import TEMPLATES

logger = logging.getLogger(__name__)


class LLMReranker(IReranker):
    """基于LLM的重排序器
    
    使用大语言模型对多源检索结果进行智能重排序，
    提高最终上下文的相关性和质量。
    """
    
    def __init__(self):
        """Initializes the LLMReranker."""
        self.config = ConfigManager()
        self.chatbot = OpenRouterChatBot()
        self.prompt_template = TEMPLATES.get("rerank_default", "")
        if not self.prompt_template:
            logger.error("Rerank prompt template 'rerank_default' not found.")
            raise ValueError("Rerank prompt template not found.")
        logger.info("LLMReranker initialized.")
        self.max_retries = 3
        self.timeout_seconds = 30
        
    def rerank(self, query: str, items: List[ContextItem], top_k: int) -> List[ContextItem]:
        """
        Reranks the list of context items based on relevance to the query.
        """
        if not items or len(items) <= top_k:
            # No need to rerank if items are fewer than or equal to top_k
            items.sort(key=lambda x: x.score, reverse=True)
            return items[:top_k]
        
        # Prepare the context for the prompt
        formatted_context = "\n---\n".join(
            f"[{i}]\n{item.to_rerank_format()}" for i, item in enumerate(items)
        )
        
        prompt = self.prompt_template.format(
            query=query, 
            context_items=formatted_context
        )

        try:
            response_str = self.chatbot.ask(prompt)
            ranked_indices = self._parse_llm_response(response_str, len(items))

            # Reorder items based on the LLM's ranking
            reordered_items = [items[i] for i in ranked_indices if i < len(items)]
            
            # Add any missing items (due to faulty LLM output) to the end
            # This ensures we always return `top_k` items if possible.
            seen_indices = set(ranked_indices)
            missing_items = [item for i, item in enumerate(items) if i not in seen_indices]
            final_items = reordered_items + missing_items
            
            return final_items[:top_k]

        except Exception as e:
            logger.error(f"LLM Reranking failed: {e}", exc_info=True)
            # Fallback strategy: return original items sorted by initial score
            items.sort(key=lambda x: x.score, reverse=True)
            return items[:top_k]
    
    def _call_llm_with_retry(self, prompt: str) -> str:
        """带重试机制的LLM调用
        
        Args:
            prompt: 输入prompt
            
        Returns:
            LLM响应
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # 构建消息格式
                messages = [
                    {
                        "role": "system",
                        "content": "You are an expert code analyst helping to rank code contexts by relevance."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ]
                
                # 调用chatbot
                response = self.chatbot.chat_with_messages(messages)
                
                if response and response.strip():
                    return response.strip()
                else:
                    raise ValueError("Empty response from LLM")
                    
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(1 * (attempt + 1))  # 递增延迟
        
        raise Exception(f"All LLM call attempts failed. Last error: {last_error}")
    
    def _parse_llm_response(self, response: str, num_items: int) -> List[int]:
        """Safely parses the JSON list of indices from the LLM response."""
        try:
            # The LLM might return a markdown code block ` ```json [...] ``` `
            if "```" in response:
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            indices = json.loads(response.strip())
            
            if not isinstance(indices, list) or not all(isinstance(i, int) for i in indices):
                raise ValueError("LLM response is not a list of integers.")
            
            # Filter out-of-bounds indices and remove duplicates
            valid_indices = []
            seen = set()
            for i in indices:
                if 0 <= i < num_items and i not in seen:
                    valid_indices.append(i)
                    seen.add(i)
            
            return valid_indices
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Could not parse LLM rerank response: {e}. Response: '{response}'")
            # Fallback to default order if parsing fails
            return list(range(num_items))
    
    def is_available(self) -> bool:
        """检查重排序器是否可用"""
        try:
            # 测试chatbot连接
            test_messages = [
                {
                    "role": "user",
                    "content": "Hello, this is a connectivity test. Please respond with 'OK'."
                }
            ]
            
            response = self.chatbot.chat_with_messages(test_messages)
            return response and len(response.strip()) > 0
            
        except Exception as e:
            logger.warning(f"LLM reranker not available: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取重排序器统计信息"""
        return {
            "reranker_type": "llm",
            "prompt_template": self.prompt_template,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "available": self.is_available()
        }
    
    def set_prompt_template(self, template: str) -> None:
        """设置prompt模板
        
        Args:
            template: 模板类型（default, function_analysis, dependency_check, error_debugging）
        """
        valid_templates = ["default", "function_analysis", "dependency_check", "error_debugging"]
        if template in valid_templates:
            self.prompt_template = template
            logger.info(f"Prompt template changed to: {template}")
        else:
            logger.warning(f"Invalid template: {template}. Using default.")
            self.prompt_template = "default" 