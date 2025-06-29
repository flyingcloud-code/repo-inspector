"""
LLM重排序器实现

基于大语言模型的智能重排序功能。
"""

import time
import re
import logging
from typing import List, Dict, Any, Optional
from ..core.context_models import (
    ContextItem, 
    RerankResult
)
from ..core.retriever_interfaces import IReranker
from ..llm.chatbot import OpenRouterChatBot
from .prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)


class LLMReranker(IReranker):
    """基于LLM的重排序器
    
    使用大语言模型对多源检索结果进行智能重排序，
    提高最终上下文的相关性和质量。
    """
    
    def __init__(self, chatbot: OpenRouterChatBot, prompt_template: str | None = None):
        """初始化LLM重排序器
        
        Args:
            chatbot: OpenRouter聊天机器人实例
            prompt_template: 使用的prompt模板类型
        """
        self.chatbot = chatbot
        if prompt_template is None:
            # 从全局配置读取
            try:
                from ..config.config_manager import ConfigManager
                cfg_mgr = ConfigManager()
                pt = getattr(cfg_mgr.get_config().enhanced_query, "prompt_template", None)
                self.prompt_template = pt or "default"
            except Exception:
                self.prompt_template = "default"
        else:
            self.prompt_template = prompt_template
        self.max_retries = 3
        self.timeout_seconds = 30
        
    def rerank(
        self, 
        query: str, 
        context_items: List[ContextItem], 
        top_k: int = 5
    ) -> RerankResult:
        """对上下文项进行重新排序
        
        Args:
            query: 原始查询
            context_items: 待重排序的上下文项列表
            top_k: 返回的top-k结果数量
            
        Returns:
            重排序结果
        """
        start_time = time.time()
        original_count = len(context_items)
        
        # 如果项目数量不超过top_k，直接返回
        if len(context_items) <= top_k:
            rerank_time = time.time() - start_time
            return RerankResult(
                items=context_items,
                rerank_time=rerank_time,
                original_count=original_count,
                confidence=1.0  # 无需重排序，置信度最高
            )
        
        try:
            # 构建重排序prompt
            prompt = self._build_rerank_prompt(query, context_items)
            
            # 调用LLM进行重排序
            llm_response = self._call_llm_with_retry(prompt)
            
            # 解析重排序结果
            ranked_indices = self._parse_rerank_response(llm_response, len(context_items))
            
            # 根据排序结果重新组织上下文项
            reranked_items = self._apply_ranking(context_items, ranked_indices, top_k)
            
            rerank_time = time.time() - start_time
            confidence = self._calculate_confidence(llm_response, ranked_indices)
            
            logger.info(f"LLM reranking completed: {len(reranked_items)} items in {rerank_time:.3f}s")
            
            return RerankResult(
                items=reranked_items,
                rerank_time=rerank_time,
                original_count=original_count,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"LLM reranking failed: {e}")
            rerank_time = time.time() - start_time
            
            # 失败时返回原始排序的前top_k项
            fallback_items = context_items[:top_k]
            return RerankResult(
                items=fallback_items,
                rerank_time=rerank_time,
                original_count=original_count,
                confidence=0.0  # 失败时置信度为0
            )
    
    def _build_rerank_prompt(self, query: str, context_items: List[ContextItem]) -> str:
        """构建重排序prompt
        
        Args:
            query: 用户查询
            context_items: 上下文项列表
            
        Returns:
            格式化的prompt字符串
        """
        try:
            from ..config.prompt_templates_config import TEMPLATES
            if self.prompt_template in TEMPLATES:
                return TEMPLATES[self.prompt_template](query, context_items)
        except Exception as e:
            logger.warning(f"Prompt config load failed: {e}")

        # fallback to internal templates
        template_func = PromptTemplates.get_template_by_intent(self.prompt_template)
        return template_func(query, context_items)
    
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
    
    def _parse_rerank_response(self, response: str, total_items: int) -> List[int]:
        """解析LLM的重排序响应
        
        Args:
            response: LLM响应文本
            total_items: 总项目数量
            
        Returns:
            排序后的索引列表（从0开始）
        """
        try:
            # 查找数字序列
            # 支持多种格式：1,2,3,4,5 或 1 2 3 4 5 或 1. 2. 3. 4. 5.
            number_patterns = [
                r'(\d+(?:,\s*\d+)*)',  # 逗号分隔
                r'(\d+(?:\s+\d+)*)',   # 空格分隔
                r'(\d+\.?\s*)+',       # 点号分隔
            ]
            
            numbers = []
            for pattern in number_patterns:
                matches = re.findall(pattern, response)
                if matches:
                    # 提取所有数字
                    number_text = matches[0]
                    numbers = re.findall(r'\d+', number_text)
                    numbers = [int(n) for n in numbers]
                    break
            
            if not numbers:
                logger.warning("No valid ranking found in LLM response, using original order")
                return list(range(total_items))
            
            # 转换为0索引并验证
            indices = []
            for num in numbers:
                if 1 <= num <= total_items:
                    indices.append(num - 1)  # 转换为0索引
            
            # 添加缺失的索引
            missing_indices = [i for i in range(total_items) if i not in indices]
            indices.extend(missing_indices)
            
            return indices[:total_items]  # 确保不超过总数
            
        except Exception as e:
            logger.error(f"Failed to parse rerank response: {e}")
            logger.debug(f"Response was: {response}")
            return list(range(total_items))  # 返回原始顺序
    
    def _apply_ranking(
        self, 
        context_items: List[ContextItem], 
        ranked_indices: List[int], 
        top_k: int
    ) -> List[ContextItem]:
        """应用排序结果
        
        Args:
            context_items: 原始上下文项列表
            ranked_indices: 排序后的索引列表
            top_k: 返回的项目数量
            
        Returns:
            重排序后的上下文项列表
        """
        reranked_items = []
        
        for idx in ranked_indices[:top_k]:
            if 0 <= idx < len(context_items):
                reranked_items.append(context_items[idx])
        
        return reranked_items
    
    def _calculate_confidence(self, llm_response: str, ranked_indices: List[int]) -> float:
        """计算重排序的置信度
        
        Args:
            llm_response: LLM响应
            ranked_indices: 解析出的排序索引
            
        Returns:
            置信度分数（0.0-1.0）
        """
        try:
            # 基本置信度：如果能解析出完整的排序则为0.8
            base_confidence = 0.8 if ranked_indices else 0.0
            
            # 响应质量加分
            response_length = len(llm_response.strip())
            if response_length > 10:  # 有实质性响应
                base_confidence += 0.1
            
            # 排序完整性加分
            if len(set(ranked_indices)) == len(ranked_indices):  # 无重复
                base_confidence += 0.1
            
            return min(base_confidence, 1.0)
            
        except Exception:
            return 0.5  # 默认中等置信度
    
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