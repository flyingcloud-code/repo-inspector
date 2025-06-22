"""核心接口定义

定义系统中各个组件的抽象接口，遵循SOLID原则中的接口隔离原则
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pathlib import Path

from .data_models import (
    Function, FileInfo, ParsedCode, EmbeddingData, 
    QueryResult, FunctionCallGraph, EmbeddingVector
)


class IParser(ABC):
    """代码解析器接口
    
    负责解析C语言源文件，提取函数定义、调用关系等结构信息
    """
    
    @abstractmethod
    def parse_file(self, file_path: Path) -> ParsedCode:
        """解析单个C文件
        
        Args:
            file_path: C源文件路径
            
        Returns:
            ParsedCode: 解析后的代码结构
            
        Raises:
            FileNotFoundError: 文件不存在
            ParseError: 解析失败
        """
        pass
    
    @abstractmethod
    def parse_directory(self, dir_path: Path, pattern: str = "*.c") -> List[ParsedCode]:
        """解析目录下的所有C文件
        
        Args:
            dir_path: 目录路径
            pattern: 文件匹配模式
            
        Returns:
            List[ParsedCode]: 解析结果列表
        """
        pass
    
    @abstractmethod
    def extract_functions(self, source_code: str, file_path: str) -> List[Function]:
        """从源代码中提取函数信息
        
        Args:
            source_code: C源代码字符串
            file_path: 文件路径（用于记录）
            
        Returns:
            List[Function]: 函数信息列表
        """
        pass


class IGraphStore(ABC):
    """图数据库存储接口
    
    负责将代码结构信息存储到Neo4j图数据库
    """
    
    @abstractmethod
    def connect(self, uri: str, user: str, password: str) -> bool:
        """连接到图数据库
        
        Args:
            uri: 数据库URI
            user: 用户名
            password: 密码
            
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def store_function(self, function: Function) -> bool:
        """存储函数信息
        
        Args:
            function: 函数对象
            
        Returns:
            bool: 存储是否成功
        """
        pass
    
    @abstractmethod
    def store_file(self, file_info: FileInfo) -> bool:
        """存储文件信息
        
        Args:
            file_info: 文件信息对象
            
        Returns:
            bool: 存储是否成功
        """
        pass
    
    @abstractmethod
    def create_call_relationship(self, caller: str, callee: str) -> bool:
        """创建函数调用关系
        
        Args:
            caller: 调用者函数名
            callee: 被调用者函数名
            
        Returns:
            bool: 创建是否成功
        """
        pass
    
    @abstractmethod
    def query_function_calls(self, function_name: str) -> List[str]:
        """查询函数的调用关系
        
        Args:
            function_name: 函数名
            
        Returns:
            List[str]: 被调用的函数列表
        """
        pass


class IVectorStore(ABC):
    """向量数据库存储接口
    
    负责存储和检索代码的向量嵌入
    """
    
    @abstractmethod
    def create_collection(self, name: str) -> bool:
        """创建向量集合
        
        Args:
            name: 集合名称
            
        Returns:
            bool: 创建是否成功
        """
        pass
    
    @abstractmethod
    def add_embeddings(self, embeddings: List[EmbeddingData]) -> bool:
        """添加向量嵌入
        
        Args:
            embeddings: 嵌入数据列表
            
        Returns:
            bool: 添加是否成功
        """
        pass
    
    @abstractmethod
    def search_similar(self, query_vector: EmbeddingVector, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索相似向量
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            
        Returns:
            List[Dict]: 相似结果列表
        """
        pass
    
    @abstractmethod
    def delete_collection(self, name: str) -> bool:
        """删除向量集合
        
        Args:
            name: 集合名称
            
        Returns:
            bool: 删除是否成功
        """
        pass


class IEmbeddingEngine(ABC):
    """嵌入生成引擎接口
    
    负责生成代码的向量嵌入
    """
    
    @abstractmethod
    def load_model(self, model_name: str) -> bool:
        """加载嵌入模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 加载是否成功
        """
        pass
    
    @abstractmethod
    def encode_text(self, text: str) -> EmbeddingVector:
        """编码文本为向量
        
        Args:
            text: 输入文本
            
        Returns:
            EmbeddingVector: 向量嵌入
        """
        pass
    
    @abstractmethod
    def encode_function(self, function: Function) -> EmbeddingData:
        """编码函数为向量嵌入
        
        Args:
            function: 函数对象
            
        Returns:
            EmbeddingData: 嵌入数据
        """
        pass
    
    @abstractmethod
    def encode_batch(self, texts: List[str]) -> List[EmbeddingVector]:
        """批量编码文本
        
        Args:
            texts: 文本列表
            
        Returns:
            List[EmbeddingVector]: 向量列表
        """
        pass


class IChatBot(ABC):
    """聊天机器人接口
    
    负责与LLM交互，回答用户问题
    """
    
    @abstractmethod
    def initialize(self, api_key: str, model: str) -> bool:
        """初始化聊天机器人
        
        Args:
            api_key: API密钥
            model: 模型名称
            
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def ask_question(self, question: str, context: List[str]) -> QueryResult:
        """询问问题
        
        Args:
            question: 用户问题
            context: 上下文信息
            
        Returns:
            QueryResult: 查询结果
        """
        pass
    
    @abstractmethod
    def generate_summary(self, code: str) -> str:
        """生成代码摘要
        
        Args:
            code: 源代码
            
        Returns:
            str: 代码摘要
        """
        pass 