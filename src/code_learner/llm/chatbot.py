"""
智能聊天机器人实现

使用OpenRouter API进行代码问答和摘要生成
支持repo级别代码理解和交互
"""
import logging
import json
from typing import List, Dict, Any, Optional
from dataclasses import asdict
import requests

from ..core.interfaces import IChatBot
from ..core.data_models import ChatMessage, ChatResponse
from ..core.exceptions import APIConnectionError, ModelError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class OpenRouterChatBot(IChatBot):
    """OpenRouter聊天机器人实现
    
    支持代码问答和摘要生成，专门针对repo级别代码理解优化
    """
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1/chat/completions"):
        """初始化OpenRouter聊天机器人
        
        Args:
            api_key: OpenRouter API密钥
            base_url: API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name: str = "google/gemini-2.0-flash-001"  # 默认模型
        self.max_tokens: int = 8192
        self.temperature: float = 1.0
        self.top_p: float = 0.95
        
        # 请求配置
        self.timeout = 30
        self.max_retries = 3
        
        # 验证API密钥
        if not api_key:
            raise APIConnectionError("OpenRouter API密钥不能为空")
    
    def initialize(self, api_key: str, model: str) -> bool:
        """初始化OpenRouter API - 实现IChatBot接口"""
        self.api_key = api_key
        self.model_name = model
        return True
    
    def configure_model(self, model_name: str, max_tokens: int = 8192, 
                       temperature: float = 1.0, top_p: float = 0.95) -> None:
        """配置模型参数
        
        Args:
            model_name: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            top_p: top_p参数
        """
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        
        logger.info(f"🔧 模型配置更新: {model_name}")
        logger.info(f"📊 参数: max_tokens={max_tokens}, temperature={temperature}, top_p={top_p}")
    
    def ask_question(self, question: str, context: Optional[str] = None) -> ChatResponse:
        """提问代码相关问题
        
        Args:
            question: 用户问题
            context: 上下文信息（如相关代码片段）
            
        Returns:
            ChatResponse: 回答结果
        """
        try:
            logger.info(f"🤖 处理用户问题: {question[:100]}...")
            
            # 构建对话消息
            messages = self._build_qa_messages(question, context)
            
            # 调用OpenRouter API
            response = self._call_api(messages)
            
            # 解析响应
            chat_response = self._parse_response(response, "question_answer")
            
            logger.info(f"✅ 问题回答完成: {len(chat_response.content)} 字符")
            return chat_response
            
        except Exception as e:
            logger.error(f"❌ 问题回答失败: {e}")
            raise ModelError(f"Failed to answer question: {str(e)}")
    
    def generate_summary(self, code_content: str, file_path: Optional[str] = None) -> ChatResponse:
        """生成代码摘要 - 用户明确要求的功能
        
        Args:
            code_content: 代码内容
            file_path: 文件路径（可选）
            
        Returns:
            ChatResponse: 摘要结果
        """
        try:
            logger.info(f"📝 生成代码摘要: {file_path or 'unknown'}")
            logger.info(f"📊 代码长度: {len(code_content)} 字符")
            
            # 构建摘要消息
            messages = self._build_summary_messages(code_content, file_path)
            
            # 调用OpenRouter API
            response = self._call_api(messages)
            
            # 解析响应
            chat_response = self._parse_response(response, "code_summary")
            
            logger.info(f"✅ 代码摘要生成完成: {len(chat_response.content)} 字符")
            return chat_response
            
        except Exception as e:
            logger.error(f"❌ 代码摘要生成失败: {e}")
            raise ModelError(f"Failed to generate summary: {str(e)}")
    
    def chat_with_context(self, messages: List[ChatMessage]) -> ChatResponse:
        """基于上下文的多轮对话
        
        Args:
            messages: 对话消息列表
            
        Returns:
            ChatResponse: 对话响应
        """
        try:
            logger.info(f"💬 多轮对话: {len(messages)} 条消息")
            
            # 转换消息格式
            api_messages = []
            for msg in messages:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # 调用OpenRouter API
            response = self._call_api(api_messages)
            
            # 解析响应
            chat_response = self._parse_response(response, "chat_context")
            
            logger.info(f"✅ 多轮对话完成: {len(chat_response.content)} 字符")
            return chat_response
            
        except Exception as e:
            logger.error(f"❌ 多轮对话失败: {e}")
            raise ModelError(f"Failed to chat with context: {str(e)}")
    
    def _build_qa_messages(self, question: str, context: Optional[str] = None) -> List[Dict[str, str]]:
        """构建问答消息
        
        Args:
            question: 用户问题
            context: 上下文
            
        Returns:
            List[Dict]: API消息格式
        """
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的C语言代码分析专家。你的任务是：
1. 理解用户的代码相关问题
2. 基于提供的代码上下文给出准确、详细的回答
3. 解释代码的功能、逻辑和潜在问题
4. 提供实用的建议和最佳实践

请用中文回答，保持专业和准确。"""
            }
        ]
        
        # 添加上下文信息
        if context:
            messages.append({
                "role": "user",
                "content": f"相关代码上下文：\n```c\n{context}\n```"
            })
        
        # 添加用户问题
        messages.append({
            "role": "user",
            "content": question
        })
        
        return messages
    
    def _build_summary_messages(self, code_content: str, file_path: Optional[str] = None) -> List[Dict[str, str]]:
        """构建摘要消息
        
        Args:
            code_content: 代码内容
            file_path: 文件路径
            
        Returns:
            List[Dict]: API消息格式
        """
        file_info = f"文件: {file_path}" if file_path else "代码片段"
        
        messages = [
            {
                "role": "system",
                "content": """你是一个专业的C语言代码分析专家。你的任务是为C语言代码生成简洁、准确的摘要。

摘要应该包括：
1. 代码的主要功能和目的
2. 关键的函数和数据结构
3. 重要的算法和逻辑
4. 代码的复杂度和特点
5. 潜在的问题或改进建议

请用中文生成摘要，保持简洁但信息丰富。"""
            },
            {
                "role": "user", 
                "content": f"请为以下{file_info}生成详细摘要：\n\n```c\n{code_content}\n```"
            }
        ]
        
        return messages
    
    def _call_api(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用OpenRouter API
        
        Args:
            messages: 消息列表
            
        Returns:
            Dict: API响应
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # 可选的引用头
            "X-Title": "C Code Analysis Tool"  # 避免中文字符编码问题
        }
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p
        }
        
        # 执行API调用，带重试机制
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"🌐 调用OpenRouter API (尝试 {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                # 检查HTTP状态码
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # 速率限制，等待后重试
                    if attempt < self.max_retries - 1:
                        import time
                        wait_time = 2 ** attempt  # 指数退避
                        logger.warning(f"⚠️ API速率限制，等待 {wait_time} 秒后重试")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise APIConnectionError(f"API rate limit exceeded: {response.text}")
                else:
                    raise APIConnectionError(f"API call failed with status {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                if attempt < self.max_retries - 1:
                    logger.warning(f"⚠️ API超时，重试中...")
                    continue
                else:
                    raise APIConnectionError("API call timeout after retries")
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"⚠️ 网络错误，重试中: {e}")
                    continue
                else:
                    raise APIConnectionError(f"Network error: {str(e)}")
        
        raise APIConnectionError("API call failed after all retries")
    
    def _parse_response(self, response: Dict[str, Any], request_type: str) -> ChatResponse:
        """解析API响应
        
        Args:
            response: API响应
            request_type: 请求类型
            
        Returns:
            ChatResponse: 解析后的响应
        """
        try:
            # 提取响应内容
            if "choices" not in response or not response["choices"]:
                raise ModelError("API响应格式错误：缺少choices字段")
            
            choice = response["choices"][0]
            if "message" not in choice:
                raise ModelError("API响应格式错误：缺少message字段")
            
            message = choice["message"]
            content = message.get("content", "")
            
            # 提取使用统计
            usage = response.get("usage", {})
            
            # 创建ChatResponse对象
            chat_response = ChatResponse(
                content=content,
                model=response.get("model", self.model_name),
                usage=usage,
                metadata={
                    "request_type": request_type,
                    "finish_reason": choice.get("finish_reason", "unknown"),
                    "response_id": response.get("id", ""),
                    "created": response.get("created", 0)
                }
            )
            
            return chat_response
            
        except Exception as e:
            logger.error(f"❌ 响应解析失败: {e}")
            raise ModelError(f"Failed to parse API response: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息
        
        Returns:
            Dict: 模型配置信息
        """
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries
        } 