#!/usr/bin/env python3
"""
用户意图分析服务

使用LLM分析用户问题，提取相关的函数名、文件名、变量名等关键信息
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from ..core.interfaces import IChatBot
from ..utils.logger import get_logger

logger = get_logger(__name__)


class IntentAnalyzer:
    """用户意图分析器
    
    使用LLM分析用户问题，提取代码相关的实体和意图
    """
    
    def __init__(self, chatbot: IChatBot):
        """初始化意图分析器
        
        Args:
            chatbot: 聊天机器人实例
        """
        self.chatbot = chatbot
        logger.info("意图分析器初始化完成")
    
    def analyze_question(self, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """分析用户问题，提取相关信息
        
        Args:
            question: 用户问题
            context: 上下文信息
            
        Returns:
            Dict[str, Any]: 分析结果，包含函数名、文件名、关键词等
        """
        logger.info(f"分析用户问题: {question}")
        
        try:
            # 构建分析提示
            analysis_prompt = self._build_analysis_prompt(question, context)
            
            # 调用LLM进行分析
            response = self.chatbot.ask_question(analysis_prompt, [])
            
            # 解析LLM响应
            analysis_result = self._parse_llm_response(response.content)
            
            # 添加简单的正则表达式提取作为备用
            fallback_result = self._extract_with_regex(question)
            
            # 合并结果
            final_result = self._merge_results(analysis_result, fallback_result)
            
            logger.info(f"意图分析完成: {final_result}")
            return final_result
            
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            # 如果LLM分析失败，使用正则表达式作为fallback
            return self._extract_with_regex(question)
    
    def _build_analysis_prompt(self, question: str, context: Optional[Dict[str, Any]] = None) -> str:
        """构建分析提示
        
        Args:
            question: 用户问题
            context: 上下文信息
            
        Returns:
            str: 分析提示
        """
        prompt = f"""你是一个代码分析专家。请分析用户的问题，提取出相关的代码实体信息。

用户问题: "{question}"

请从问题中提取以下信息，并以JSON格式返回：

1. functions: 提到的函数名列表（如sbi_init, malloc等）
2. files: 提到的文件名列表（如main.c, header.h等）
3. variables: 提到的变量名列表
4. keywords: 关键技术词汇列表（如API, driver, interrupt等）
5. intent_type: 问题类型（function_analysis, file_analysis, general_question, call_relationship等）
6. search_terms: 用于向量搜索的关键词列表

注意事项：
- 只提取真正的代码相关实体，忽略"what", "how", "about"等疑问词
- 函数名通常包含下划线，如sbi_init, pmu_event_validate
- 文件名通常以.c, .h等结尾
- 如果问题涉及函数调用关系，intent_type设为"call_relationship"
- 如果问题询问特定函数功能，intent_type设为"function_analysis"

示例输出：
```json
{{
    "functions": ["sbi_init", "sbi_platform_init"],
    "files": ["init.c"],
    "variables": ["hartid"],
    "keywords": ["initialization", "platform", "boot"],
    "intent_type": "function_analysis",
    "search_terms": ["sbi_init", "initialization", "platform", "boot"]
}}
```

请分析上述问题并返回JSON格式的结果："""

        if context and context.get('project_path'):
            prompt += f"\n\n上下文信息：项目路径为 {context['project_path']}"
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应
        
        Args:
            response: LLM响应内容
            
        Returns:
            Dict[str, Any]: 解析结果
        """
        try:
            # 尝试提取JSON部分
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析整个响应
                json_str = response.strip()
            
            # 解析JSON
            result = json.loads(json_str)
            
            # 确保所有必需字段存在
            default_result = {
                "functions": [],
                "files": [],
                "variables": [],
                "keywords": [],
                "intent_type": "general_question",
                "search_terms": []
            }
            
            for key, default_value in default_result.items():
                if key not in result:
                    result[key] = default_value
                elif not isinstance(result[key], list) and key != "intent_type":
                    result[key] = default_value
            
            return result
            
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"LLM响应解析失败: {e}, 响应内容: {response[:200]}...")
            return {
                "functions": [],
                "files": [],
                "variables": [],
                "keywords": [],
                "intent_type": "general_question",
                "search_terms": []
            }
    
    def _extract_with_regex(self, question: str) -> Dict[str, Any]:
        """使用正则表达式提取代码实体（备用方案）
        
        Args:
            question: 用户问题
            
        Returns:
            Dict[str, Any]: 提取结果
        """
        logger.info("使用正则表达式进行实体提取")
        
        # 函数名模式：通常包含下划线，以字母开头
        function_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
        potential_functions = re.findall(function_pattern, question)
        
        # 过滤函数名：包含下划线且不是常见英文单词
        common_words = {
            'what', 'about', 'this', 'that', 'function', 'does', 'call', 'who', 
            'how', 'where', 'when', 'why', 'which', 'the', 'and', 'or', 'but',
            'is', 'are', 'was', 'were', 'have', 'has', 'had', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'must', 'shall'
        }
        
        functions = []
        for word in potential_functions:
            if ('_' in word or word.startswith('sbi_') or word.endswith('_init') or 
                word.endswith('_get') or word.endswith('_set') or len(word) > 8) and \
               word.lower() not in common_words:
                functions.append(word)
        
        # 文件名模式
        file_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\.[ch]\b'
        files = re.findall(file_pattern, question)
        
        # 关键词提取
        keywords = []
        tech_keywords = [
            'api', 'apis', 'driver', 'interrupt', 'memory', 'allocation', 'boot',
            'initialization', 'platform', 'device', 'register', 'callback',
            'handler', 'manager', 'service', 'interface', 'protocol'
        ]
        
        question_lower = question.lower()
        for keyword in tech_keywords:
            if keyword in question_lower:
                keywords.append(keyword)
        
        # 确定意图类型
        intent_type = "general_question"
        if any(word in question_lower for word in ['call', 'calls', 'called', 'invoke']):
            intent_type = "call_relationship"
        elif functions:
            intent_type = "function_analysis"
        elif files:
            intent_type = "file_analysis"
        
        # 生成搜索词
        search_terms = functions + keywords
        if not search_terms:
            # 如果没有提取到特定术语，使用问题中的关键词
            words = re.findall(r'\b[a-zA-Z]{3,}\b', question)
            search_terms = [w for w in words if w.lower() not in common_words][:5]
        
        return {
            "functions": list(set(functions)),
            "files": list(set(files)),
            "variables": [],
            "keywords": list(set(keywords)),
            "intent_type": intent_type,
            "search_terms": list(set(search_terms))
        }
    
    def _merge_results(self, llm_result: Dict[str, Any], regex_result: Dict[str, Any]) -> Dict[str, Any]:
        """合并LLM分析结果和正则表达式结果
        
        Args:
            llm_result: LLM分析结果
            regex_result: 正则表达式结果
            
        Returns:
            Dict[str, Any]: 合并后的结果
        """
        merged = {}
        
        # 合并列表字段
        list_fields = ["functions", "files", "variables", "keywords", "search_terms"]
        for field in list_fields:
            llm_items = set(llm_result.get(field, []))
            regex_items = set(regex_result.get(field, []))
            merged[field] = list(llm_items | regex_items)
        
        # 选择更准确的意图类型
        merged["intent_type"] = llm_result.get("intent_type", regex_result.get("intent_type", "general_question"))
        
        return merged
    
    def extract_function_names(self, question: str) -> List[str]:
        """从问题中提取函数名（简化接口）
        
        Args:
            question: 用户问题
            
        Returns:
            List[str]: 函数名列表
        """
        analysis = self.analyze_question(question)
        return analysis.get("functions", [])
    
    def extract_search_terms(self, question: str) -> List[str]:
        """从问题中提取搜索词（简化接口）
        
        Args:
            question: 用户问题
            
        Returns:
            List[str]: 搜索词列表
        """
        analysis = self.analyze_question(question)
        return analysis.get("search_terms", []) 